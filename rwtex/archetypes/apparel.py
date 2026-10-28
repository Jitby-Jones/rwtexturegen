"""Worn apparel: body armor and helmets for every body type and direction.

Design once in *body space* - ``u`` across the body (-1 left/back .. +1 right/front) and
``v`` down the body (0 shoulders .. 1 bottom) - and the frame maps it onto each vanilla
body silhouette (Male/Female/Thin/Hulk/Fat x south/east/north) measured from the art
source.  Helmets use the same idea on the head silhouette.

Output naming follows RimWorld: ``Name_<BodyType>_<dir>.png`` (+ ``Name_<BodyType>_<dir>m.png``
masks, Graphic_Multi convention) for body apparel, ``Name_<dir>.png`` for headgear and
``Name.png`` / ``Name_m.png`` for the ground texture.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .. import geom as G
from ..materials import get as getmat
from ..parts import common as C
from ..render import Bevel, Dome, Facets, Fill, Glow, Line, Part, Rim, Scene, Split
from ..styles import Style, get as get_style
from . import register

BODY_TYPES = ['Male', 'Female', 'Thin', 'Hulk', 'Fat']
ROLES = ('shell', 'undersuit', 'strap', 'accent', 'trim', 'energy', 'joint', 'lens')
DEFAULT_ROLE_MATS = {'shell': 'armor_white', 'undersuit': 'undersuit', 'strap': 'undersuit', 'accent': 'graphite',
                     'trim': 'steel_bright', 'energy': 'led_cyan', 'joint': 'steel_bright', 'lens': 'lens_teal'}
DIRS = ['south', 'east', 'north']
_T = None


def templates() -> dict:
    global _T
    if _T is None:
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'templates.json')) as f:
            _T = json.load(f)
    return _T


class Frame:
    """Maps body-space (u, v) onto a measured silhouette."""

    def __init__(self, rows: Sequence[Sequence[float]], k: float = 1.0, scale: float = 1.0,
                 center: Tuple[float, float] = (64.0, 64.0), dir: str = 'south', clamp: bool = True,
                 top_zone: float = 0.35):
        a = np.asarray(rows, dtype=float)
        cx0, cy0 = center
        self.y = ((a[:, 0] + 0.5 - cy0) * scale + cy0) * k
        self.xl = ((a[:, 1] - cx0) * scale + cx0) * k
        self.xr = ((a[:, 2] - cx0) * scale + cx0) * k
        self.k = k * scale
        self.dir = dir
        self.top = float(self.y.min() - 0.5 * k * scale)
        self.bot = float(self.y.max() + 0.5 * k * scale)
        self.H = self.bot - self.top
        w = self.xr - self.xl
        n = len(w)
        self.i_sh = int(np.argmax(w[:max(2, int(n * top_zone))]))
        lo = int(n * 0.6)
        self.i_hip = lo + int(np.argmax(w[lo:]))
        self.clamp = clamp
        mid = int(n * 0.5)
        self.hw_ref = float(w[mid] / 2)

    def edges(self, y: float) -> Tuple[float, float]:
        return float(np.interp(y, self.y, self.xl)), float(np.interp(y, self.y, self.xr))

    def frame(self, v: float) -> Tuple[float, float, float]:
        y = self.top + v * self.H
        yy = y
        if self.clamp:
            yy = min(max(y, self.y[self.i_sh]), self.y[self.i_hip])
        xl, xr = self.edges(yy)
        return (xl + xr) / 2, (xr - xl) / 2, y

    def P(self, u: float, v: float) -> Tuple[float, float]:
        cx, hw, y = self.frame(v)
        return cx + u * hw, y

    def uv(self, pts, c: float = 0.0, corners: str = 'chamfer', mirror: bool = False, step: float = 1.5) -> np.ndarray:
        """Body-space polygon -> canvas ring.  ``c`` is a corner size in canvas px."""
        p = np.asarray(pts, dtype=float).copy()
        if mirror:
            p[:, 0] *= -1
            p = p[::-1]
        S = np.array([max(self.hw_ref, 1.0), self.H])
        q = p * S
        if c > 0:
            q = G.chamfer(q, c * self.k) if corners == 'chamfer' else G.rounded(q, c * self.k)
        q = G.resample(q, step * self.k)
        uvp = q / S
        return np.array([self.P(u, v) for u, v in uvp])

    def silhouette(self, expand: float = 0.0) -> np.ndarray:
        e = expand * self.k
        left = np.stack([self.xl - e, self.y], axis=1)
        right = np.stack([self.xr + e, self.y], axis=1)[::-1]
        top = np.array([[(self.xl[0] + self.xr[0]) / 2, self.top - e]])
        bot = np.array([[(self.xl[-1] + self.xr[-1]) / 2, self.bot + e]])
        ring = np.vstack([top, left, bot, right])
        return G.simplify_ring(ring, 0.15)

    def ellipse(self, u: float, v: float, ru: float, rv: float) -> np.ndarray:
        cx, hw, y = self.frame(v)
        return G.ellipse(cx + u * hw, y, abs(ru) * self.hw_ref, abs(rv) * self.H)


def body_frame(bt: str, dir: str, k: float = 1.0, scale: float = 1.0, center=(64.0, 64.0)) -> Frame:
    return Frame(templates()['bodies'][f'{bt}_{dir}'], k, scale, center, dir)


def head_frame(dir: str, k: float = 1.0, scale: float = 1.0, center=(64.0, 64.0)) -> Frame:
    return Frame(templates()['heads'][f'Average_{dir}'], k, scale, center, dir, clamp=True, top_zone=0.75)


# ----------------------------------------------------------------------------- painting rules

APPAREL_LIGHT = -90.0          # vanilla apparel reads as lit from straight above (symmetric facets)
APPAREL_INNER = 2.0            # inner line weight at 128px (vanilla plate seams are heavy)


def plate_shading(k: float, width: float = 2.6) -> list:
    """Chamfered-plate facets: lit top facets, grey side facets, darker bottom facets."""
    return [Facets(width * k, ('light', 'base', 'shade', 'deep'), (0.5, 0.15, -0.7))]


def apparel_scene(size: int, name: str, outline: float, k: float, ground: bool = False) -> Scene:
    return Scene(size, name=name, outline=outline, inner=APPAREL_INNER * k * (1.1 if ground else 1.0),
                 light_angle=APPAREL_LIGHT, occlusion=(1.5 * k, 0.32, 1.1 * k))


# ----------------------------------------------------------------------------- context

@dataclass
class Ctx:
    scene: Scene
    f: Frame
    dir: str
    bt: str
    st: Style
    mats: Dict[str, str]
    p: dict
    k: float
    ground: bool = False
    seed: int = 0
    form: object = None   # rwtex.form.TorsoForm / HeadForm (3D proxy for perspective-correct plates)

    def m(self, role: str) -> str:
        return self.mats.get(role) or self.st.materials.get(role) or DEFAULT_ROLE_MATS.get(role) or role

    def tone(self, ref):
        """Map 'role.tone' references (e.g. 'energy.base') to 'material.tone'."""
        if isinstance(ref, str) and '.' in ref and not ref.startswith('#'):
            role, t = ref.rsplit('.', 1)
            if role in ROLES:
                return f'{self.m(role)}.{t}'
        return ref

    def part(self, name: str, ring, role: str, z: float, shading='auto', mask='auto', **kw) -> Part:
        mname = self.m(role)
        mat = getmat(mname)
        if mask == 'auto':
            mask = 'r' if role in self.p.get('mask_roles', ('shell',)) else None
        if shading == 'auto' and role in ('shell', 'trim') and 'tone' not in kw:
            return self.plate(name, ring, z, role=role, mask=mask, **kw)
        if shading == 'auto':
            shading = plate_shading(self.k)
        p = Part(name, ring, mat, z=z, shading=shading, mask=mask, **kw)
        self.scene.add(p)
        return p

    def pair(self, name: str, pts, role: str, z: float, c: float = 2.0, corners: str = 'chamfer', **kw) -> List[Part]:
        """A left/right symmetric pair (south/north) - mirrored across u=0."""
        out = [self.part(name + '_r', self.f.uv(pts, c, corners), role, z, **kw)]
        out.append(self.part(name + '_l', self.f.uv(pts, c, corners, mirror=True), role, z, **kw))
        return out

    # painting helpers -------------------------------------------------------------------------
    def view_tone(self, role: str = 'shell', facing: str = 'auto'):
        """Base value by view: front-facing plates stay bright, side planes and the whole back
        view drop toward the shade tone (vanilla north views read light grey)."""
        from ..color import mix
        mat = getmat(self.m(role))
        if facing == 'auto':
            facing = {'south': 'front', 'east': 'side', 'north': 'back'}[self.dir]
        t = {'front': 0.0, 'side': 0.35, 'back': 0.55}[facing]
        return mix(mat.base, mat.shade, t)

    def plate(self, name: str, ring, z: float, role: str = 'shell', facing: str = 'auto', dome: bool = True,
              bevel: float = 2.6, mask='auto', **kw) -> Part:
        """Armor plate with the painted look: view-dependent base value, a soft airbrushed
        highlight (dome gradient) and chamfer facets derived from that base."""
        from ..color import mix
        mat = getmat(self.m(role))
        base = self.view_tone(role, facing)
        sh: list = []
        if dome:
            sh.append(Dome((mix(base, mat.light, 0.8), base, mix(base, mat.shade, 0.55)), (-0.2, -0.6), 1.35, 1.0))
        sh.append(Facets(bevel * self.k, (mix(base, mat.light, 0.9), base, mix(base, mat.shade, 0.9), mix(base, mat.deep, 0.75)),
                         (0.5, 0.15, -0.7)))
        return self.part(name, ring, role, z, shading=sh, mask=mask, tone=base, **kw)

    def pair_plates(self, name: str, pts, z: float, c: float = 2.0, corners: str = 'chamfer', **kw) -> List[Part]:
        """Symmetric pair of painted plates (south/north)."""
        return [self.plate(name + '_r', self.f.uv(pts, c, corners), z, **kw),
                self.plate(name + '_l', self.f.uv(pts, c, corners, mirror=True), z, **kw)]

    def panel(self, part: Part, inset: float = 2.6, width: float = 1.1, tone='deep', ring_index: int = 0) -> Part:
        """Inner panel line following the plate outline (vanilla seam inside a plate)."""
        r = part.rings[ring_index]
        rr = G.offset(G.simplify_ring(r, 0.4), -inset * self.k)
        part.details.append(Line(rr, width * self.k, tone, closed=True))
        return part

    def joint(self, name: str, u: float, v: float, r: float, z: float, lens: bool = False) -> Part:
        """Exposed bionic joint cap: light metal disc, black ring, teal lens + glint
        (vanilla bionic-eye overlay palette)."""
        f, k = self.f, self.k
        ry = r * f.hw_ref / f.H
        jp = self.part(name, f.ellipse(u, v, r, ry), 'joint', z,
                       shading=[Dome(('light', 'base', 'shade'), (-0.3, -0.45), 1.15), Facets(1.2 * k, ('light', 'base', 'shade', 'deep'), (0.5, 0.15, -0.7))],
                       mask=None)
        jp.detail(Fill([f.ellipse(u, v, r * 0.5, ry * 0.5)], 'deep', mask=None),
                  Fill([f.ellipse(u, v, r * 0.26, ry * 0.26)], 'energy.base' if lens else 'shade', mask=None))
        return jp

    @property
    def front(self) -> bool:
        return self.dir == 'south'

    @property
    def side(self) -> bool:
        return self.dir == 'east'

    @property
    def back(self) -> bool:
        return self.dir == 'north'


# ----------------------------------------------------------------------------- apparel set

@dataclass
class ApparelSet:
    name: str
    kind: str  # 'body' | 'head'
    scenes: Dict[str, Scene] = field(default_factory=dict)  # key: 'Male_south' / 'south' / 'ground'
    meta: dict = field(default_factory=dict)

    def files(self) -> List[Tuple[str, Scene]]:
        out = []
        for key, sc in self.scenes.items():
            fn = self.name if key == 'ground' else f'{self.name}_{key}'
            out.append((fn, sc))
        return out


ARMOR_STYLE = {
    'neolithic': dict(design='tribal', mats=dict(shell='bone', undersuit='hide', strap='sinew', accent='feather_red', trim='bone')),
    'medieval': dict(design='plate', mats=dict(shell='blade_white', undersuit='leather', strap='leather', accent='brass', trim='brass')),
    'industrial': dict(design='flak', mats=dict(shell='olive_drab', undersuit='cloth_khaki', strap='polymer', accent='polymer', trim='polymer'),
                       mask_roles=()),
    'spacer': dict(design='marine', mats=dict(shell='armor_white', undersuit='undersuit', strap='undersuit', accent='visor_dark', trim='steel_bright', energy='led_cyan')),
    'ultratech': dict(design='cataphract', mats=dict(shell='armor_white', undersuit='undersuit', strap='graphite', accent='graphite', trim='steel_bright', energy='cyan_glow')),
    'archotech': dict(design='monolith', mats=dict(shell='archo_olive', undersuit='archo_frame', strap='archo_frame', accent='archo_sage', trim='archo_sage', energy='archo_yellow'),
                      mask_roles=()),
    'imperial': dict(design='cataphract', trim_gold=True, mats=dict(shell='armor_white', undersuit='undersuit', strap='imperial_purple', accent='graphite', trim='imperial_gold', energy='mono_cyan')),
    'mechanoid': dict(design='marine', mats=dict(shell='mech_pale', undersuit='undersuit', strap='undersuit', accent='mech_taupe', trim='mech_taupe', energy='mech_red'), mask_roles=()),
    'anomaly': dict(design='marine', spikes=True, mats=dict(shell='bioferrite', undersuit='void_black', strap='flesh', accent='flesh', trim='void_black', energy='glow_red'), mask_roles=()),
    'dms': dict(design='exo', mats=dict(shell='dms_gunmetal', undersuit='muscle_fiber', strap='dms_olive', accent='hazard_yellow', trim='dms_steel', energy='glow_orange'),
                mask_roles=()),
    'bionic': dict(design='bionic', mats=dict(shell='armor_white', undersuit='muscle_fiber', strap='graphite', accent='graphite', trim='steel_bright',
                                              energy='led_cyan', joint='steel_bright', lens='lens_teal')),
    'vanilla_expanded': dict(design='marine', mats=dict(shell='armor_white', undersuit='undersuit', strap='undersuit', accent='visor_dark', trim='steel_bright', energy='led_cyan')),
}


# ----------------------------------------------------------------------------- body designs

def _collar(c: Ctx, z: float = 30):
    """Neck opening with a light rim (covered by the head when worn, visible on ground)."""
    f = c.f
    if c.side or c.back:
        return
    v = 0.035
    rim = f.ellipse(0, v, 0.46 if c.ground else 0.42, 0.085)
    hole = f.ellipse(0, v + 0.004, 0.33 if c.ground else 0.3, 0.06)
    c.part('collar', rim, 'trim', z, shading=[Bevel(0.8 * c.k, 0.9 * c.k)], mask=None)
    c.part('neck', hole, 'undersuit', z + 0.1, shading=[Bevel(0, 1.2 * c.k, shade_tone='deep')], mask=None, outline=None)


def _undersuit(c: Ctx, fibers: bool = False):
    f = c.f
    p = c.part('undersuit', f.silhouette(0.6), 'undersuit', 0, shading=plate_shading(c.k, 2.2), mask=None)
    if fibers:
        _muscle_fibers(c, p)
    return p


def _muscle_fibers(c: Ctx, p: Part):
    """Artificial-muscle striation lines (DMS bionic suit / bionic exo)."""
    f = c.f
    k = c.k
    if c.front:
        for side in (-1, 1):
            for i in range(3):  # abdominal rows
                v = 0.52 + i * 0.09
                p.line([f.P(side * 0.12, v), f.P(side * 0.5, v + 0.015)], 0.9 * k, 'light')
            p.line([f.P(side * 0.75, 0.3), f.P(side * 0.6, 0.55), f.P(side * 0.55, 0.8)], 0.9 * k, 'light')
        p.line([f.P(0, 0.42), f.P(0, 0.9)], 0.9 * k, 'deep')
    elif c.back:
        for i in range(6):
            v = 0.2 + i * 0.11
            p.fill(G.rounded(G.rect(*f.P(-0.13, v), *f.P(0.13, v + 0.06)), 1.0 * k), 'light')
        for side in (-1, 1):
            p.line([f.P(side * 0.25, 0.25), f.P(side * 0.7, 0.45), f.P(side * 0.6, 0.8)], 0.9 * k, 'light')
    else:
        for i in range(4):
            v = 0.35 + i * 0.12
            p.line([f.P(-0.2, v), f.P(0.55, v + 0.03)], 0.9 * k, 'light')


def design_marine(c: Ctx):
    """Vanilla marine grammar: dominant shoulder mantle around the neck hole, V-neck chest
    plate, dark belt with a node, splayed tassets; light-grey values on side/back views."""
    f, k, p = c.f, c.k, c.p
    _undersuit(c, fibers=p.get('fibers', False))
    if c.front:
        for t in c.pair_plates('tasset', [(0.16, 0.8), (0.95, 0.77), (1.04, 1.03), (0.28, 1.03)], 3, 1.8):
            c.panel(t, 2.4)
        c.plate('codpiece', f.uv([(-0.18, 0.8), (0.18, 0.8), (0.15, 0.99), (-0.15, 0.99)], 1.4), 3.2, bevel=1.6)
        c.part('belt', f.uv([(-0.88, 0.7), (0.88, 0.7), (0.86, 0.79), (-0.86, 0.79)], 1.0), 'strap', 4, mask=None)
        c.part('belt_node', f.ellipse(0, 0.745, 0.13, 0.04), 'accent', 4.5, mask=None, shading=[Facets(1.0 * k)])
        ch = c.plate('chest', f.uv([(-0.8, 0.22), (-0.2, 0.28), (0.0, 0.4), (0.2, 0.28), (0.8, 0.22), (0.74, 0.52), (0.0, 0.62), (-0.74, 0.52)], 2.2), 6)
        c.panel(ch, 2.6)
        m = c.plate('mantle', f.uv([(-0.95, -0.05), (0.95, -0.05), (1.3, 0.07), (1.34, 0.3), (0.6, 0.36), (0.26, 0.25), (-0.26, 0.25),
                                    (-0.6, 0.36), (-1.34, 0.3), (-1.3, 0.07)], 2.8), 8)
        c.panel(m, 3.2)
        _collar(c)
    elif c.side:
        c.plate('backplate', f.uv([(-1.08, 0.06), (-0.3, 0.02), (-0.26, 0.62), (-1.02, 0.66)], 2.0), 4, facing='back')
        th = c.plate('thigh', f.uv([(-0.15, 0.79), (0.96, 0.76), (1.03, 1.03), (-0.08, 1.03)], 2.0), 4, facing='side')
        c.panel(th, 2.4)
        c.part('belt', f.uv([(-1.0, 0.68), (1.04, 0.68), (1.02, 0.77), (-0.98, 0.77)], 0.8), 'strap', 5, mask=None)
        ch = c.plate('chest', f.uv([(-0.05, 0.08), (1.1, 0.14), (1.14, 0.42), (1.0, 0.6), (0.0, 0.62)], 2.2), 6, facing='front')
        c.panel(ch, 2.6)
        pd = c.plate('pauldron', f.uv([(-0.66, -0.12), (0.52, -0.12), (0.8, 0.06), (0.82, 0.3), (0.52, 0.47), (-0.42, 0.47), (-0.74, 0.3), (-0.78, 0.04)], 3.0), 9, facing='side')
        c.panel(pd, 3.0)
    else:
        for t in c.pair_plates('tasset', [(0.16, 0.8), (0.95, 0.77), (1.04, 1.03), (0.28, 1.03)], 3, 1.8):
            c.panel(t, 2.4)
        c.part('belt', f.uv([(-0.88, 0.7), (0.88, 0.7), (0.86, 0.79), (-0.86, 0.79)], 1.0), 'strap', 4, mask=None)
        for t in c.pair_plates('backside', [(0.12, 0.34), (0.86, 0.3), (0.82, 0.66), (0.14, 0.68)], 5, 2.0):
            c.panel(t, 2.4)
        pk = c.part('pack', f.uv([(-0.34, 0.34), (0.34, 0.34), (0.3, 0.64), (-0.3, 0.64)], 2.0), 'accent', 6, mask=None,
                    shading=[Facets(1.6 * k)])
        pk.detail(*C.vent_slots(*f.P(-0.22, 0.42), *f.P(0.22, 0.5), 4, k))
        m = c.plate('mantle', f.uv([(-0.95, -0.05), (0.95, -0.05), (1.3, 0.07), (1.34, 0.3), (0.95, 0.36), (-0.95, 0.36), (-1.34, 0.3), (-1.3, 0.07)], 2.8), 8)
        for side in (-1, 1):
            m.line([f.P(side * 0.4, -0.03), f.P(side * 0.48, 0.34)], 1.1 * k, 'deep')


def design_cataphract(c: Ctx):
    """Heavy ultratech grammar: high pauldrons, back fins, smooth shells, glowing seams."""
    f, k, p = c.f, c.k, c.p
    _undersuit(c, fibers=p.get('fibers', False))
    fin = p.get('fins', True)
    if c.side:
        if fin:
            c.part('fin', f.uv([(-0.95, -0.25), (-0.62, -0.32), (-0.55, 0.3), (-0.95, 0.3)], 2.0, 'round'), 'shell', 2)
        c.part('backplate', f.uv([(-1.15, 0.05), (-0.3, 0.0), (-0.25, 0.62), (-1.1, 0.68)], 3.0, 'round'), 'shell', 5)
        c.part('chest', f.uv([(-0.05, 0.05), (1.15, 0.1), (1.12, 0.6), (0.0, 0.64)], 3.0, 'round'), 'shell', 6)
        c.part('pauldron', f.uv([(-0.75, -0.12), (0.7, -0.08), (0.78, 0.33), (0.0, 0.46), (-0.8, 0.32)], 5.0, 'round'), 'shell', 9)
        c.part('thigh', f.uv([(-0.25, 0.72), (1.0, 0.7), (0.95, 1.03), (-0.2, 1.03)], 2.5, 'round'), 'shell', 4)
    elif c.front:
        if fin:
            c.pair('fin', [(0.32, -0.32), (0.62, -0.32), (0.66, 0.1), (0.3, 0.1)], 'shell', 1, 2.5, 'round')
        c.part('chest', f.uv([(-0.84, 0.18), (0.84, 0.18), (0.76, 0.58), (0.0, 0.64), (-0.76, 0.58)], 3.0, 'round'), 'shell', 5)
        c.pair('pauldron', [(0.22, -0.1), (1.32, -0.06), (1.36, 0.32), (1.0, 0.4), (0.5, 0.3), (0.22, 0.16)], 'shell', 8, 3.5, 'round')
        c.pair('thigh', [(0.1, 0.7), (1.0, 0.7), (0.95, 1.03), (0.16, 1.03)], 'shell', 4, 2.5, 'round')
        c.part('belt', f.uv([(-0.78, 0.62), (0.78, 0.62), (0.75, 0.7), (-0.75, 0.7)], 1.0), 'strap', 3.5, mask=None)
        _collar(c)
    else:
        if fin:
            c.pair('fin', [(0.3, -0.34), (0.62, -0.34), (0.66, 0.2), (0.3, 0.2)], 'shell', 9, 2.5, 'round')
        c.part('back', f.uv([(-0.9, 0.1), (0.9, 0.1), (0.84, 0.64), (-0.84, 0.64)], 3.5, 'round'), 'shell', 5)
        c.pair('pauldron', [(0.22, -0.1), (1.32, -0.06), (1.36, 0.32), (1.0, 0.4), (0.5, 0.3), (0.22, 0.16)], 'shell', 8, 3.5, 'round')
        c.pair('thigh', [(0.1, 0.72), (1.0, 0.72), (0.95, 1.03), (0.16, 1.03)], 'shell', 4, 2.5, 'round')
        _collar(c)


def design_plate(c: Ctx):
    """Medieval plate: overlapping lames with rivets and leather straps (stuff-tinted)."""
    f, k = c.f, c.k
    _undersuit(c)
    if c.side:
        c.part('cuirass', f.uv([(-1.05, 0.05), (1.08, 0.08), (1.02, 0.6), (-1.0, 0.62)], 2.0, 'round'), 'shell', 5)
        c.part('pauldron', f.uv([(-0.55, -0.02), (0.55, -0.02), (0.6, 0.28), (-0.6, 0.28)], 4.0, 'round'), 'shell', 9)
        for i in range(3):
            c.part(f'tasset{i}', f.uv([(-0.4, 0.62 + i * 0.12), (0.95, 0.62 + i * 0.12), (0.92, 0.74 + i * 0.12), (-0.38, 0.74 + i * 0.12)], 1.0), 'shell', 4 + i * 0.1)
    else:
        c.part('cuirass', f.uv([(-0.9, 0.08), (0.9, 0.08), (0.82, 0.62), (-0.82, 0.62)], 3.0, 'round'), 'shell', 5)
        c.pair('pauldron', [(0.45, -0.04), (1.22, 0.0), (1.2, 0.3), (0.5, 0.26)], 'shell', 8, 3.5, 'round')
        for i in range(3):
            c.part(f'tasset{i}', f.uv([(-0.8, 0.62 + i * 0.12), (0.8, 0.62 + i * 0.12), (0.78, 0.75 + i * 0.12), (-0.78, 0.75 + i * 0.12)], 1.0), 'shell', 4 + i * 0.1)
        if c.front:
            cu = c.scene.get('cuirass')
            cu.line([f.P(0, 0.12), f.P(0, 0.6)], 1.0 * k, 'shade')
            cu.detail(*C.rivets([f.P(u, 0.14) for u in (-0.7, 0.7)] + [f.P(u, 0.56) for u in (-0.65, 0.65)], 1.1 * k))
        _collar(c)
    for p in [p for p in c.scene.parts if p.name.startswith('tasset')]:
        p.detail(*C.rivets([((p.bbox()[0] + p.bbox()[2]) / 2, (p.bbox()[1] + p.bbox()[3]) / 2)], 1.0 * k))


def design_tribal(c: Ctx):
    """Neolithic: hide wrap, bone plates, sinew lashing."""
    f, k = c.f, c.k
    _undersuit(c)
    if c.side:
        c.part('wrap', G.wobble(f.uv([(-1.0, 0.2), (1.05, 0.25), (1.0, 0.85), (-0.95, 0.8)], 3.0, 'round'), 0.7 * k, 5 * k, c.seed), 'undersuit', 3,
               shading=[Bevel(1 * k, 1.4 * k)])
        c.part('bone', f.uv([(-0.4, 0.0), (0.5, 0.02), (0.45, 0.22), (-0.35, 0.2)], 3.0, 'round'), 'shell', 8)
    else:
        w = c.part('wrap', G.wobble(f.uv([(-0.95, 0.25), (0.95, 0.3), (0.9, 0.85), (-0.92, 0.8)], 3.0, 'round'), 0.7 * k, 5 * k, c.seed),
                   'undersuit', 3, shading=[Bevel(1 * k, 1.4 * k)])
        w.detail(*C.diag_bands(f.P(-0.8, 0.5)[0], f.P(0.8, 0.5)[0], f.P(0, 0.52)[1], 1.6 * k, 5, 1.2 * k, 0.6 * k, 'sinew.base'))
        c.pair('bone', [(0.35, 0.0), (1.05, 0.06), (0.95, 0.24), (0.4, 0.18)], 'shell', 8, 3.0, 'round')
        if c.front:
            beads = [f.P(u, 0.2 + 0.08 * (1 - (u / 0.4) ** 2)) for u in np.linspace(-0.4, 0.4, 7)]
            c.part('beads', [G.circle(x, y, 1.6 * k) for x, y in beads], 'accent', 9, shading=[Bevel(0.6 * k, 0.6 * k)], mask=None)


def design_flak(c: Ctx):
    """Industrial flak vest: olive vest, pouches, stitching."""
    f, k = c.f, c.k
    _undersuit(c)
    if c.side:
        c.part('vest', f.uv([(-1.05, 0.08), (1.08, 0.12), (1.02, 0.7), (-1.0, 0.72)], 2.5, 'round'), 'shell', 5)
        c.part('pouch', f.uv([(0.45, 0.42), (1.05, 0.42), (1.02, 0.62), (0.45, 0.62)], 1.2), 'shell', 6)
    else:
        v = c.part('vest', f.uv([(-0.95, 0.06), (-0.3, 0.06), (-0.22, 0.2), (0.22, 0.2), (0.3, 0.06), (0.95, 0.06), (0.9, 0.72), (-0.9, 0.72)], 2.5, 'round'), 'shell', 5)
        v.line([f.P(-0.85, 0.14), f.P(-0.85, 0.68)], 0.8 * k, 'deep')
        v.line([f.P(0.85, 0.14), f.P(0.85, 0.68)], 0.8 * k, 'deep')
        if c.front:
            for u in (-0.5, 0.0, 0.5):
                c.part(f'pouch{u}', f.uv([(u - 0.2, 0.44), (u + 0.2, 0.44), (u + 0.19, 0.66), (u - 0.19, 0.66)], 1.2), 'shell', 6)
        _collar(c)


def design_monolith(c: Ctx):
    """Archotech: stepped sage-olive blocks, yellow traces, floating plates."""
    f, k = c.f, c.k
    _undersuit(c)
    if c.side:
        c.part('block', f.uv([(-0.9, 0.05), (0.95, 0.05), (0.95, 0.35), (1.08, 0.35), (1.08, 0.66), (-0.85, 0.66)], 0.4), 'shell', 5,
               shading=[Bevel(1 * k, 1 * k)])
        c.part('float', f.uv([(-0.5, -0.18), (0.4, -0.18), (0.4, -0.05), (-0.5, -0.05)], 0.3), 'trim', 9, shading=[Bevel(0.8 * k, 0.8 * k)])
    else:
        b = c.part('block', f.uv([(-0.9, 0.05), (-0.4, 0.05), (-0.4, 0.15), (0.4, 0.15), (0.4, 0.05), (0.9, 0.05), (0.9, 0.4), (0.78, 0.4),
                                  (0.78, 0.66), (-0.78, 0.66), (-0.78, 0.4), (-0.9, 0.4)], 0.4), 'shell', 5, shading=[Bevel(1 * k, 1 * k)])
        x0, y0 = f.P(-0.65, 0.22)
        x1, y1 = f.P(0.65, 0.58)
        b.detail(*C.circuit(x0, x1, y0, y1, k, seed=c.seed, n=2))
        c.pair('float', [(0.95, -0.12), (1.25, -0.12), (1.25, 0.12), (0.95, 0.12)], 'trim', 9, 0.3)
        c.pair('leg', [(0.15, 0.72), (0.9, 0.72), (0.9, 1.0), (0.15, 1.0)], 'shell', 4, 0.4)
        _collar(c)
    for p in c.scene.parts:
        if p.name.startswith('block'):
            p.glow = Glow(getmat('archo_yellow').glow, 2.0 * k, 0.25, 'halo')


def design_exo(c: Ctx):
    """DMS exo / bionic suit: muscle-fibre body, gunmetal frame bars, olive straps, hazard tag."""
    f, k = c.f, c.k
    _undersuit(c, fibers=True)
    if c.side:
        c.part('spine_frame', f.uv([(-1.1, 0.0), (-0.75, 0.0), (-0.75, 0.75), (-1.1, 0.75)], 2.0), 'shell', 6)
        c.part('shoulder', f.uv([(-0.5, -0.02), (0.6, 0.0), (0.6, 0.22), (-0.5, 0.22)], 3.0), 'shell', 9)
        c.part('strap', f.uv([(-0.7, 0.4), (1.02, 0.4), (1.02, 0.5), (-0.7, 0.5)], 0.8), 'strap', 7, mask=None)
    else:
        c.pair('shoulder', [(0.3, -0.02), (1.15, 0.0), (1.15, 0.22), (0.35, 0.22)], 'shell', 9, 3.0)
        c.pair('frame', [(0.55, 0.22), (0.72, 0.22), (0.72, 0.92), (0.55, 0.92)], 'shell', 6, 1.0)
        c.part('strap', f.uv([(-0.85, 0.42), (0.85, 0.42), (0.85, 0.52), (-0.85, 0.52)], 0.8), 'strap', 7, mask=None)
        if c.front:
            tag = c.part('tag', f.uv([(0.2, 0.25), (0.48, 0.25), (0.48, 0.36), (0.2, 0.36)], 0.6), 'accent', 8, mask=None)
            tag.detail(*C.vent_slots(*f.P(0.24, 0.28), *f.P(0.44, 0.33), 3, k, tone='deep'))
        else:
            c.part('pack', f.uv([(-0.4, 0.12), (0.4, 0.12), (0.4, 0.5), (-0.4, 0.5)], 2.5), 'shell', 8).detail(
                *C.vent_slots(*f.P(-0.28, 0.2), *f.P(0.28, 0.3), 4, k))
        _collar(c)


def design_bionic(c: Ctx):
    """Bionic assault suit: marine mantle + recon segmented abdomen + cataphract-height
    pauldrons over an artificial-muscle undersuit (DMS bionic suit), with exposed bionic
    joints (vanilla bionic-eye palette), a segmented bionic spine and a chest power core."""
    f, k, p = c.f, c.k, c.p
    glow = p.get('glow', True)
    _undersuit(c, fibers=True)
    if c.front:
        for t in c.pair_plates('tasset', [(0.2, 0.81), (0.96, 0.78), (1.04, 1.03), (0.3, 1.03)], 3, 1.8):
            c.panel(t, 2.4)
        c.plate('codpiece', f.uv([(-0.16, 0.81), (0.16, 0.81), (0.13, 0.98), (-0.13, 0.98)], 1.4), 3.2, bevel=1.6)
        c.part('belt', f.uv([(-0.88, 0.71), (0.88, 0.71), (0.86, 0.79), (-0.86, 0.79)], 1.0), 'strap', 4, mask=None, shading=[Facets(1.2 * k)])
        node = c.part('belt_node', f.ellipse(0, 0.75, 0.12, 0.035), 'joint', 4.5, mask=None, shading=[Facets(1.0 * k)])
        node.detail(Fill([f.ellipse(0, 0.75, 0.06, 0.018)], 'energy.base', mask=None))
        for i in range(2):
            v0 = 0.575 + i * 0.07
            c.plate(f'abs{i}', f.uv([(-0.38, v0), (0.38, v0), (0.34, v0 + 0.055), (-0.34, v0 + 0.055)], 1.0), 5, dome=False, bevel=1.4)
        ch = c.plate('chest', f.uv([(-0.78, 0.22), (-0.22, 0.28), (0.0, 0.4), (0.22, 0.28), (0.78, 0.22), (0.72, 0.5), (0.0, 0.58), (-0.72, 0.5)], 2.2), 6)
        c.panel(ch, 2.6)
        if glow:
            for side in (-1, 1):
                ch.line([f.P(side * 0.62, 0.3), f.P(side * 0.58, 0.47)], 1.0 * k, 'energy.base', mask=None)
        core = c.part('core', f.ellipse(0, 0.345, 0.15, 0.045), 'joint', 7, mask=None,
                      shading=[Dome(('light', 'base', 'shade'), (-0.3, -0.4), 1.1), Facets(1.0 * k)])
        core.detail(Fill([f.ellipse(0, 0.345, 0.09, 0.027)], 'energy.base', mask=None),
                    Fill([f.ellipse(-0.025, 0.338, 0.035, 0.011)], 'energy.light', mask=None))
        m = c.plate('mantle', f.uv([(-0.95, -0.06), (0.95, -0.06), (1.34, 0.05), (1.4, 0.3), (0.62, 0.36), (0.28, 0.26), (-0.28, 0.26),
                                    (-0.62, 0.36), (-1.4, 0.3), (-1.34, 0.05)], 2.8), 8)
        c.panel(m, 3.2)
        for side in (-1, 1):
            c.joint(f'shoulder_joint_{"r" if side > 0 else "l"}', side * 1.08, 0.19, 0.16, 9)
            c.joint(f'hip_joint_{"r" if side > 0 else "l"}', side * 0.66, 0.75, 0.15, 6)
        _collar(c)
    elif c.side:
        sp = c.part('spine', f.uv([(-1.22, -0.04), (-0.86, -0.06), (-0.82, 0.86), (-1.12, 0.88)], 2.0), 'accent', 2, mask=None,
                    shading=[Facets(1.4 * k)])
        for i, v in enumerate(np.arange(0.02, 0.82, 0.095)):
            sp.detail(Fill([G.chamfer(G.rect(*f.P(-1.15, v), *f.P(-0.9, v + 0.06)), 0.8 * k)], 'trim.base',
                           shading=[Facets(0.8 * k, ('trim.light', 'trim.base', 'trim.shade', 'trim.deep'), (0.5, 0.15, -0.7))]))
            if glow and i % 2 == 1:
                sp.detail(Fill([G.circle(*f.P(-1.02, v + 0.03), 0.9 * k)], 'energy.base', mask=None))
        c.plate('backplate', f.uv([(-0.92, 0.06), (-0.3, 0.02), (-0.26, 0.6), (-0.88, 0.64)], 2.0), 4, facing='back')
        th = c.plate('thigh', f.uv([(-0.12, 0.8), (0.96, 0.77), (1.03, 1.03), (-0.05, 1.03)], 2.0), 4, facing='side')
        c.panel(th, 2.4)
        c.part('belt', f.uv([(-0.84, 0.69), (1.04, 0.69), (1.02, 0.77), (-0.82, 0.77)], 0.8), 'strap', 5, mask=None, shading=[Facets(1.0 * k)])
        for i in range(2):
            v0 = 0.56 + i * 0.065
            c.plate(f'abs{i}', f.uv([(0.36, v0), (1.03, v0), (0.99, v0 + 0.05), (0.39, v0 + 0.05)], 1.0), 5.5, facing='front', dome=False, bevel=1.4)
        ch = c.plate('chest', f.uv([(-0.05, 0.08), (1.1, 0.14), (1.15, 0.4), (1.0, 0.52), (0.0, 0.55)], 2.2), 6, facing='front')
        c.panel(ch, 2.6)
        if glow:
            ch.line([f.P(0.35, 0.44), f.P(0.95, 0.42)], 1.0 * k, 'energy.base', mask=None)
        c.joint('hip_joint', 0.3, 0.75, 0.2, 6.5)
        pd = c.plate('pauldron', f.uv([(-0.66, -0.16), (0.5, -0.16), (0.8, 0.04), (0.82, 0.3), (0.52, 0.48), (-0.42, 0.48), (-0.74, 0.3), (-0.78, 0.02)], 3.0), 9, facing='side')
        c.panel(pd, 3.0)
        c.joint('shoulder_joint', 0.02, 0.17, 0.2, 10)
    else:
        for t in c.pair_plates('tasset', [(0.2, 0.81), (0.96, 0.78), (1.04, 1.03), (0.3, 1.03)], 3, 1.8):
            c.panel(t, 2.4)
        c.part('belt', f.uv([(-0.88, 0.71), (0.88, 0.71), (0.86, 0.79), (-0.86, 0.79)], 1.0), 'strap', 4, mask=None, shading=[Facets(1.2 * k)])
        for t in c.pair_plates('backside', [(0.22, 0.34), (0.86, 0.3), (0.82, 0.66), (0.24, 0.68)], 5, 2.0):
            c.panel(t, 2.4)
        m = c.plate('mantle', f.uv([(-0.95, -0.06), (0.95, -0.06), (1.34, 0.05), (1.4, 0.3), (0.95, 0.36), (-0.95, 0.36), (-1.4, 0.3), (-1.34, 0.05)], 2.8), 8)
        for side in (-1, 1):
            m.line([f.P(side * 0.42, -0.04), f.P(side * 0.5, 0.34)], 1.1 * k, 'deep')
        sp = c.part('spine', f.uv([(-0.19, 0.0), (0.19, 0.0), (0.17, 0.88), (-0.17, 0.88)], 2.0), 'accent', 9, mask=None,
                    shading=[Facets(1.4 * k)])
        for i, v in enumerate(np.arange(0.04, 0.84, 0.095)):
            sp.detail(Fill([G.chamfer(G.rect(*f.P(-0.15, v), *f.P(0.15, v + 0.058)), 0.8 * k)], 'trim.base',
                           shading=[Facets(0.8 * k, ('trim.light', 'trim.base', 'trim.shade', 'trim.deep'), (0.5, 0.15, -0.7))]))
            if glow and i % 2 == 0:
                sp.detail(Fill([G.circle(*f.P(0, v + 0.029), 0.9 * k)], 'energy.base', mask=None))
        for side in (-1, 1):
            c.joint(f'shoulder_joint_{"r" if side > 0 else "l"}', side * 1.08, 0.19, 0.16, 10)
            c.joint(f'hip_joint_{"r" if side > 0 else "l"}', side * 0.66, 0.75, 0.15, 6)


def _resolve_roles(c: Ctx) -> None:
    """Rewrite role-based tone references in details/shading to concrete materials."""
    from ..render import Bevel as _B, Split as _S, Gradient as _Gr, Rim as _R
    for p in c.scene.parts:
        for d in p.details:
            d.tone = c.tone(d.tone)
            if isinstance(d, Fill):
                d.outline_tone = c.tone(d.outline_tone)
                for op in d.shading:
                    _fix_op(c, op)
        for op in p.shading:
            _fix_op(c, op)
        if isinstance(p.tone, str):
            p.tone = c.tone(p.tone)


def _fix_op(c: Ctx, op) -> None:
    for attr in ('light_tone', 'shade_tone', 'tone'):
        if hasattr(op, attr):
            setattr(op, attr, c.tone(getattr(op, attr)))
    if hasattr(op, 'tones'):
        op.tones = tuple(c.tone(t) for t in op.tones)


DESIGNS: Dict[str, Callable[[Ctx], None]] = {
    'marine': design_marine, 'cataphract': design_cataphract, 'plate': design_plate, 'tribal': design_tribal,
    'flak': design_flak, 'monolith': design_monolith, 'exo': design_exo, 'bionic': design_bionic,
}


def _post(c: Ctx):
    """Style-level decorations applied after the design."""
    k = c.k
    if c.p.get('trim_gold'):
        for p in list(c.scene.parts):
            if p.name.startswith('pauldron') and not c.side:
                x0, y0, x1, y1 = p.bbox()
                p.detail(Fill([G.rect(x0, y1 - 2.6 * k, x1, y1)], 'imperial_gold.base', mask=None,
                              shading=[Bevel(0.6 * k, 0.6 * k, light_tone='imperial_gold.light', shade_tone='imperial_gold.shade')]))
        if not c.side:
            fan = []
            f = c.f
            for i, u in enumerate(np.linspace(-0.55, 0.55, 5)):
                cx, cy = f.P(u, -0.1 - 0.06 * (1 - abs(u)))
                fan.append(G.rotate(G.capsule(cx, cy - 4 * k, cx, cy + 4 * k, 1.8 * k), u * 30, cx, cy + 4 * k))
            c.part('laurel', fan, 'imperial_gold', -1, shading=[Bevel(0.6 * k, 0.6 * k)], mask=None)
    if c.p.get('spikes'):
        for p in list(c.scene.parts):
            if p.name.startswith(('yoke', 'pauldron')):
                x0, y0, x1, y1 = p.bbox()
                c.part(p.name + '_spike', G.poly([(x0 + 2 * k, y0 + 2 * k), ((x0 + x1) / 2, y0 - 5 * k), (x1 - 2 * k, y0 + 2 * k)]), 'trim', p.z - 0.5,
                       mask=None)


def _forms():
    from ..form import HeadForm, TorsoForm
    return HeadForm, TorsoForm


@register('armor')
def armor(style='spacer', size: int = 128, seed: int = 0, name: str = 'Armor', *, design: Optional[str] = None,
          mats: Optional[dict] = None, body_types: Sequence[str] = BODY_TYPES, dirs: Sequence[str] = DIRS,
          ground: bool = True, ground_scale: float = 1.3, ground_body: str = 'Male', outline: Optional[float] = None,
          mask_roles: Optional[Sequence[str]] = None, design_fn: Optional[Callable[[Ctx], None]] = None, **params) -> ApparelSet:
    st = get_style(style)
    d = dict(ARMOR_STYLE.get(st.key, ARMOR_STYLE['spacer']))
    dm = dict(d.pop('mats'))
    dm.update(mats or {})
    p = dict(d)
    p.update(params)
    if mask_roles is not None:
        p['mask_roles'] = tuple(mask_roles)
    fn = design_fn or DESIGNS[design or p.get('design', 'marine')]
    HeadForm, TorsoForm = _forms()
    k = size / 128.0
    ol = outline if outline is not None else 3.4 * k
    out = ApparelSet(name, 'body', meta=dict(archetype='armor', style=st.key, design=design or p.get('design')))
    for bt in body_types:
        for dr in dirs:
            sc = apparel_scene(size, f'{name}_{bt}_{dr}', ol, k)
            c = Ctx(sc, body_frame(bt, dr, k), dr, bt, st, dm, p, k, seed=seed)
            c.form = TorsoForm(bt, k)
            fn(c)
            _post(c)
            _resolve_roles(c)
            sc.meta.update(dict(kind='apparel_body', body=bt, dir=dr))
            out.scenes[f'{bt}_{dr}'] = sc
    if ground:
        sc = apparel_scene(size, name, ol * 1.1, k, ground=True)
        fr = body_frame(ground_body, 'south', k, scale=ground_scale, center=(64.0, 70.0))
        c = Ctx(sc, fr, 'south', ground_body, st, dm, p, k * ground_scale, ground=True, seed=seed)
        c.form = TorsoForm(ground_body, k, scale=ground_scale, center=(64.0, 70.0))
        fn(c)
        _post(c)
        _resolve_roles(c)
        sc.meta.update(dict(kind='apparel_ground'))
        out.scenes['ground'] = sc
    return out


# ----------------------------------------------------------------------------- helmets

HELMET_STYLE = {
    'neolithic': dict(design='mask', mats=dict(shell='wood', accent='feather_red', lens='void_black', trim='sinew')),
    'medieval': dict(design='helm', mats=dict(shell='blade_white', accent='iron_dark', lens='void_black', trim='brass')),
    'industrial': dict(design='ballistic', mats=dict(shell='olive_drab', accent='polymer', lens='lens_teal', trim='polymer'), mask_roles=()),
    'spacer': dict(design='marine', mats=dict(shell='armor_white', accent='visor_dark', lens='spacer_grey', trim='steel_bright', energy='led_cyan')),
    'ultratech': dict(design='cataphract', mats=dict(shell='armor_white', accent='graphite', lens='visor_dark', trim='steel_bright', energy='cyan_glow')),
    'archotech': dict(design='monolith', mats=dict(shell='archo_olive', accent='archo_frame', lens='archo_yellow', trim='archo_sage', energy='archo_yellow'), mask_roles=()),
    'imperial': dict(design='cataphract', crest=True, mats=dict(shell='armor_white', accent='graphite', lens='visor_dark', trim='imperial_gold', energy='mono_cyan')),
    'dms': dict(design='gasmask', mats=dict(shell='dms_olive', accent='dms_gunmetal', lens='visor_dark', trim='dms_steel', energy='glow_orange'), mask_roles=()),
    'mechanoid': dict(design='marine', mats=dict(shell='mech_pale', accent='undersuit', lens='mech_red', trim='mech_taupe', energy='mech_red'), mask_roles=()),
    'anomaly': dict(design='helm', mats=dict(shell='bioferrite', accent='void_black', lens='glow_red', trim='void_black', energy='glow_red'), mask_roles=()),
    'bionic': dict(design='bionic', mats=dict(shell='armor_white', accent='graphite', lens='lens_teal', trim='steel_bright', energy='led_cyan', joint='steel_bright')),
    'vanilla_expanded': dict(design='marine', mats=dict(shell='armor_white', accent='visor_dark', lens='visor_dark', trim='steel_bright', energy='led_cyan')),
}


def _shell(c: Ctx, expand: float = -1.2, z: float = 5) -> Part:
    """Helmet shell that follows the round head silhouette (never a box)."""
    return c.plate('shell', c.f.silhouette(expand), z, bevel=2.4)


def _ridge(c: Ctx, v1: float = 0.34, z: float = 6) -> Part:
    f, k = c.f, c.k
    r = c.plate('ridge', f.uv([(-0.15, -0.08), (0.15, -0.08), (0.12, v1), (-0.12, v1)], 1.2), z, dome=False, bevel=1.4)
    r.detail(Fill([G.rounded(G.rect(*f.P(-0.08, 0.02), *f.P(0.08, 0.1)), 0.8 * k)], 'deep'))
    return r


def helm_marine(c: Ctx):
    """Vanilla marine-helmet grammar: round shell, centre ridge, angular dark visor, chin guard."""
    f, k = c.f, c.k
    sh = _shell(c)
    if c.front:
        _ridge(c)
        c.part('visor', f.uv([(-0.8, 0.42), (-0.22, 0.44), (0.0, 0.53), (0.22, 0.44), (0.8, 0.42), (0.72, 0.63), (0.24, 0.67), (0.0, 0.61),
                              (-0.24, 0.67), (-0.72, 0.63)], 1.0), 'accent', 7, mask=None,
               shading=[Facets(1.4 * k, ('accent.light', 'accent.base', 'accent.shade', 'accent.deep'), (0.5, 0.15, -0.7))])
        sh.line([f.P(-0.5, 0.36), f.P(0.0, 0.4), f.P(0.5, 0.36)], 1.0 * k, 'deep')
        sh.line([f.P(0.0, 0.7), f.P(0.0, 0.92)], 1.0 * k, 'deep')
        for u in (-0.36, 0.36):
            sh.fill(G.rounded(G.rect(*f.P(u - 0.1, 0.78), *f.P(u + 0.1, 0.84)), 0.6 * k), 'deep')
    elif c.side:
        c.part('visor', f.uv([(0.35, 0.42), (1.06, 0.44), (1.04, 0.62), (0.5, 0.64)], 1.2), 'accent', 7, mask=None,
               shading=[Facets(1.2 * k, ('accent.light', 'accent.base', 'accent.shade', 'accent.deep'), (0.5, 0.15, -0.7))])
        sh.line([f.P(0.55, -0.02), f.P(0.1, 0.25), f.P(-0.35, 0.62), f.P(-0.45, 0.95)], 1.1 * k, 'deep')
        cap = c.plate('earcap', f.ellipse(-0.08, 0.56, 0.2, 0.08), 7, facing='side', dome=False, bevel=1.4)
        cap.detail(Fill([f.ellipse(-0.08, 0.56, 0.09, 0.036)], 'deep'))
    else:
        _ridge(c, v1=0.6)
        sh.line([f.P(-0.8, 0.66), f.P(0.8, 0.66)], 1.0 * k, 'deep')


def helm_cataphract(c: Ctx):
    """Ultratech heavy helm: round shell, raised brow, single visor slit, jaw guard (+ imperial crest)."""
    f, k = c.f, c.k
    sh = _shell(c, expand=-0.6)
    if c.p.get('crest'):
        if c.side:
            c.part('crest', f.uv([(-0.15, -0.44), (0.12, -0.44), (0.02, -0.02), (-0.95, 0.42), (-1.05, 0.3)], 2.0, 'round'), 'trim', 4.5, mask=None)
        else:
            c.part('crest', f.uv([(-0.13, -0.42), (0.13, -0.42), (0.12, 0.3), (-0.12, 0.3)], 1.5, 'round'), 'trim', 6.5, mask=None)
    if c.front:
        brow = c.plate('brow', f.uv([(-0.9, 0.3), (0.9, 0.3), (0.84, 0.42), (-0.84, 0.42)], 1.4), 6, dome=False, bevel=1.4)
        c.part('slit', f.uv([(-0.78, 0.44), (0.78, 0.44), (0.74, 0.52), (-0.74, 0.52)], 0.8), 'accent', 6.5, mask=None, shading=[])
        jaw = c.plate('jaw', f.uv([(-0.62, 0.58), (0.62, 0.58), (0.46, 0.98), (-0.46, 0.98)], 2.4), 7, bevel=2.0)
        jaw.line([f.P(0.0, 0.62), f.P(0.0, 0.94)], 1.0 * k, 'deep')
    elif c.side:
        c.plate('brow', f.uv([(0.1, 0.3), (1.08, 0.32), (1.06, 0.42), (0.1, 0.42)], 1.4), 6, facing='front', dome=False, bevel=1.4)
        c.part('slit', f.uv([(0.45, 0.44), (1.1, 0.46), (1.08, 0.53), (0.45, 0.52)], 0.8), 'accent', 6.5, mask=None, shading=[])
        c.plate('jaw', f.uv([(0.12, 0.58), (1.04, 0.6), (0.94, 0.98), (0.12, 0.95)], 2.4), 7, facing='front', bevel=2.0)
        sh.line([f.P(0.4, -0.02), f.P(-0.2, 0.3), f.P(-0.55, 0.62)], 1.1 * k, 'deep')
    else:
        sh.line([f.P(-0.8, 0.62), f.P(0.8, 0.62)], 1.0 * k, 'deep')
        sh.line([f.P(0.0, -0.02), f.P(0.0, 0.6)], 1.0 * k, 'deep')


def helm_bionic(c: Ctx):
    """Bionic helm: round shell, smooth faceplate with a dark sensor band, one bionic eye
    (vanilla bionic-eye palette: light plate, black ring, teal lens), neural port at the back."""
    f, k, p = c.f, c.k, c.p
    glow = p.get('glow', True)
    sh = _shell(c)

    def eye(u, v, r, z):
        ry = r * f.hw_ref / f.H
        e = c.part('eye_plate', f.ellipse(u, v, r * 1.25, ry * 1.25), 'joint', z,
                   shading=[Dome(('light', 'base', 'shade'), (-0.3, -0.45), 1.15), Facets(1.0 * k)], mask=None)
        e.detail(Fill([f.ellipse(u, v, r * 0.85, ry * 0.85)], 'black', mask=None),
                 Fill([f.ellipse(u, v, r * 0.58, ry * 0.58)], 'lens.base', mask=None),
                 Fill([f.ellipse(u - r * 0.2, v - ry * 0.22, r * 0.18, ry * 0.18)], 'energy.light', mask=None))
        return e

    if c.front:
        _ridge(c, v1=0.3)
        face = c.plate('face', f.uv([(-0.8, 0.36), (0.8, 0.36), (0.8, 0.64), (0.42, 0.98), (-0.42, 0.98), (-0.8, 0.64)], 3.0), 6.5, bevel=2.0)
        c.panel(face, 2.2)
        band = c.part('band', f.uv([(-0.86, 0.42), (0.86, 0.42), (0.82, 0.54), (-0.82, 0.54)], 1.2), 'accent', 7, mask=None,
                      shading=[Facets(1.0 * k, ('accent.light', 'accent.base', 'accent.shade', 'accent.deep'), (0.5, 0.15, -0.7))])
        if glow:
            band.line([f.P(-0.74, 0.48), f.P(0.12, 0.48)], 1.0 * k, 'energy.base', mask=None)
        eye(0.44, 0.48, 0.2, 8)
        for i, u in enumerate((-0.2, 0.0, 0.2)):
            face.fill(G.rounded(G.rect(*f.P(u - 0.06, 0.76), *f.P(u + 0.06, 0.88)), 0.6 * k), 'deep')
    elif c.side:
        face = c.plate('face', f.uv([(0.18, 0.36), (1.08, 0.38), (1.08, 0.66), (0.86, 0.98), (0.2, 0.96)], 3.0), 6.5, facing='front', bevel=2.0)
        c.panel(face, 2.2)
        band = c.part('band', f.uv([(0.1, 0.42), (1.12, 0.44), (1.1, 0.55), (0.1, 0.54)], 1.0), 'accent', 7, mask=None,
                      shading=[Facets(1.0 * k, ('accent.light', 'accent.base', 'accent.shade', 'accent.deep'), (0.5, 0.15, -0.7))])
        eye(0.82, 0.49, 0.19, 8)
        c.joint('earport', -0.32, 0.56, 0.2, 7.5)
        sh.line([f.P(0.5, -0.02), f.P(-0.1, 0.22), f.P(-0.62, 0.42)], 1.1 * k, 'deep')
    else:
        _ridge(c, v1=0.56)
        port = c.part('port', f.uv([(-0.3, 0.58), (0.3, 0.58), (0.26, 1.02), (-0.26, 1.02)], 2.0), 'accent', 7, mask=None,
                      shading=[Facets(1.4 * k)])
        for i, v in enumerate((0.64, 0.76, 0.88)):
            port.detail(Fill([G.chamfer(G.rect(*f.P(-0.2, v), *f.P(0.2, v + 0.07)), 0.7 * k)], 'trim.base'))
            if glow and i == 1:
                port.detail(Fill([G.circle(*f.P(0, v + 0.035), 0.9 * k)], 'energy.base', mask=None))


def helm_simple(c: Ctx, kind: str):
    f, k = c.f, c.k
    if kind == 'helm':  # medieval barrel helm: flat-topped but follows the head width
        sh = c.plate('shell', G.chamfer(G.poly([f.P(-1.0, -0.06), f.P(1.0, -0.06), f.P(1.04, 0.98), f.P(-1.04, 0.98)]), 3.0 * k)
                     if not c.side else G.chamfer(G.poly([f.P(-1.04, -0.06), f.P(0.86, -0.06), f.P(1.08, 0.3), f.P(1.06, 0.98), f.P(-1.04, 0.98)]), 3.0 * k), 5)
        if not c.back:
            u0, u1 = (0.2, 1.1) if c.side else (-0.84, 0.84)
            c.part('slit', f.uv([(u0, 0.42), (u1, 0.42), (u1, 0.5), (u0, 0.5)], 0.6), 'lens', 6, mask=None, shading=[])
            sh.line([f.P(0.0 if not c.side else 0.9, 0.06), f.P(0.0 if not c.side else 0.95, 0.4)], 1.0 * k, 'deep')
            sh.detail(*C.rivets([f.P(u, 0.8) for u in ((0.3, 0.7) if c.side else (-0.6, 0.0, 0.6))], 1.1 * k))
        else:
            sh.line([f.P(-0.9, 0.62), f.P(0.9, 0.62)], 1.0 * k, 'deep')
    elif kind == 'ballistic':
        r = f.uv([(-1.12, 0.05), (1.12, 0.05), (1.18, 0.55), (-1.18, 0.55)], 9.0, 'round')
        c.plate('shell', r, 5)
        if not c.back:
            g0, g1 = ((0.2, 1.1) if c.side else (-0.7, 0.7))
            c.part('goggles', f.uv([(g0, 0.36), (g1, 0.36), (g1, 0.48), (g0, 0.48)], 2.0, 'round'), 'lens', 6, mask=None)
    elif kind == 'mask':  # tribal war mask: carved face plate over the face + feather
        if c.back:
            c.part('strap', f.uv([(-1.0, 0.42), (1.0, 0.42), (1.0, 0.5), (-1.0, 0.5)], 1.0), 'trim', 5, mask=None)
        else:
            u0, u1 = (0.05, 1.1) if c.side else (-0.92, 0.92)
            r = G.wobble(f.uv([(u0, 0.22), (u1, 0.22), (u1 - 0.08, 0.7), ((u0 + u1) / 2, 1.0), (u0 + 0.08, 0.7)], 4.0, 'round'), 0.6 * k, 5 * k, c.seed)
            s_ = c.plate('shell', r, 5, mask=None)
            for u in ((0.62,) if c.side else (-0.4, 0.4)):
                s_.fill(f.ellipse(u, 0.46, 0.17, 0.055), 'lens.base')
            s_.line([f.P((u0 + u1) / 2 - 0.3, 0.75), f.P((u0 + u1) / 2 + 0.3, 0.75)], 1.2 * k, 'accent.base')
            s_.detail(*C.diag_bands(f.P(u0 + 0.1, 0.3)[0], f.P(u1 - 0.1, 0.3)[0], f.P(0, 0.3)[1], 1.2 * k, 3, 1.2 * k, 0.4 * k, 'accent.base'))
        c.part('feather', f.uv([(0.3, -0.38), (0.52, -0.38), (0.48, 0.2), (0.32, 0.2)], 2.0, 'round'), 'accent', 4, mask=None)
    elif kind == 'gasmask':
        c.plate('shell', f.uv([(-1.08, 0.0), (1.08, 0.0), (1.12, 0.6), (-1.12, 0.6)], 8.0, 'round'), 5)
        if not c.back:
            c.part('mask', f.uv([(-0.75, 0.38), (0.75, 0.38), (0.6, 1.0), (-0.6, 1.0)] if not c.side else [(0.0, 0.38), (1.12, 0.38), (1.0, 1.0), (0.1, 1.0)], 3.0, 'round'),
                   'accent', 6, mask=None)
            for u in ((-0.35, 0.35) if not c.side else (0.7,)):
                c.part(f'lens{u}', f.ellipse(u, 0.52, 0.18, 0.06), 'lens', 7, mask=None, shading=[Bevel(0.6 * k, 0.6 * k)])
            c.part('filter', f.ellipse(0.0 if not c.side else 0.9, 0.86, 0.22, 0.08), 'trim', 7.5, mask=None)
    elif kind == 'monolith':  # archotech: head-shaped shell with a stepped crown + glowing eye slit
        sh = c.plate('shell', c.f.silhouette(-1.0), 5, bevel=1.6)
        c.plate('crown', f.uv([(-0.7, -0.14), (0.7, -0.14), (0.7, 0.02), (0.92, 0.02), (0.92, 0.28), (-0.92, 0.28), (-0.92, 0.02), (-0.7, 0.02)], 0.4)
                if not c.side else f.uv([(-0.9, -0.14), (0.6, -0.14), (0.6, 0.02), (0.9, 0.02), (0.9, 0.28), (-0.9, 0.28)], 0.4), 6, dome=False, bevel=1.2)
        if not c.back:
            u0, u1 = (0.3, 1.04) if c.side else (-0.7, 0.7)
            c.part('eye', f.uv([(u0, 0.44), (u1, 0.44), (u1, 0.52), (u0, 0.52)], 0.3), 'lens', 7, mask=None, shading=[])
        x0, y0 = f.P(-0.6, 0.6)
        x1, y1 = f.P(0.6, 0.92)
        sh.detail(*C.circuit(x0, x1, y0, y1, k, seed=c.seed, n=1))
        c.part('float', f.uv([(-0.35, -0.42), (0.35, -0.42), (0.35, -0.3), (-0.35, -0.3)], 0.3), 'trim', 7, mask=None, shading=[Bevel(0.8 * k, 0.8 * k)])


HELMET_DESIGNS = {'marine': helm_marine, 'cataphract': helm_cataphract, 'bionic': helm_bionic,
                  'helm': lambda c: helm_simple(c, 'helm'), 'ballistic': lambda c: helm_simple(c, 'ballistic'),
                  'mask': lambda c: helm_simple(c, 'mask'), 'gasmask': lambda c: helm_simple(c, 'gasmask'),
                  'monolith': lambda c: helm_simple(c, 'monolith')}


@register('helmet')
def helmet(style='spacer', size: int = 128, seed: int = 0, name: str = 'Helmet', *, design: Optional[str] = None,
           mats: Optional[dict] = None, dirs: Sequence[str] = DIRS, ground: bool = True, ground_scale: float = 1.3,
           outline: Optional[float] = None, mask_roles: Optional[Sequence[str]] = None,
           design_fn: Optional[Callable[[Ctx], None]] = None, **params) -> ApparelSet:
    st = get_style(style)
    d = dict(HELMET_STYLE.get(st.key, HELMET_STYLE['spacer']))
    dm = dict(d.pop('mats'))
    dm.update(mats or {})
    p = dict(d)
    p.update(params)
    if mask_roles is not None:
        p['mask_roles'] = tuple(mask_roles)
    fn = design_fn or HELMET_DESIGNS[design or p.get('design', 'marine')]
    HeadForm, TorsoForm = _forms()
    k = size / 128.0
    ol = outline if outline is not None else 3.4 * k
    out = ApparelSet(name, 'head', meta=dict(archetype='helmet', style=st.key, design=design or p.get('design')))
    for dr in dirs:
        sc = apparel_scene(size, f'{name}_{dr}', ol, k)
        c = Ctx(sc, head_frame(dr, k), dr, 'Average', st, dm, p, k, seed=seed)
        c.form = HeadForm(dr, k)
        fn(c)
        _resolve_roles(c)
        sc.meta.update(dict(kind='apparel_head', dir=dr))
        out.scenes[dr] = sc
    if ground:
        sc = apparel_scene(size, name, ol * 1.1, k, ground=True)
        c = Ctx(sc, head_frame('south', k, scale=ground_scale, center=(64.0, 66.0)), 'south', 'Average', st, dm, p, k * ground_scale, ground=True, seed=seed)
        c.form = HeadForm('south', k, scale=ground_scale, center=(64.0, 66.0))
        fn(c)
        _resolve_roles(c)
        sc.meta.update(dict(kind='apparel_ground'))
        out.scenes['ground'] = sc
    return out
