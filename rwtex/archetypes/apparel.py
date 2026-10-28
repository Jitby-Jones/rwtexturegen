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
APPAREL_INNER = 1.4            # inner line weight at 128px (vanilla seams: black-dark-black ~4 px)


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
    fit: str = 'marine'   # which measured vanilla fit the 3D-form designs follow (rwtex/data/armor_fit.json)

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


# marine / recon / cataphract / bionic are registered by armor3d (perspective-correct 3D-form designs)
DESIGNS: Dict[str, Callable[[Ctx], None]] = {
    'plate': design_plate, 'tribal': design_tribal, 'flak': design_flak, 'monolith': design_monolith, 'exo': design_exo,
}


def _post(c: Ctx):
    """Style-level decorations applied after the design (imperial gold trim, anomaly spikes)."""
    k = c.k
    if c.p.get('trim_gold'):
        for p in list(c.scene.parts):
            if p.name in ('chest', 'backplate', 'pauldron') or p.name.startswith('pauldron'):
                x0, y0, x1, y1 = p.bbox()
                p.detail(Fill([G.rect(x0, y1 - 2.6 * k, x1, y1 + 1.0)], 'imperial_gold.base', mask=None,
                              shading=[Bevel(0.6 * k, 0.6 * k, light_tone='imperial_gold.light', shade_tone='imperial_gold.shade')]))
        if not c.side:
            fan = []
            f = c.f
            for i, u in enumerate(np.linspace(-0.55, 0.55, 5)):
                cx, cy = f.P(u, -0.1 - 0.06 * (1 - abs(u)))
                fan.append(G.rotate(G.capsule(cx, cy - 4 * k, cx, cy + 4 * k, 1.8 * k), u * 30, cx, cy + 4 * k))
            c.part('laurel', fan, 'imperial_gold', -1, shading=[Bevel(0.6 * k, 0.6 * k)], mask=None)
    if c.p.get('spikes'):
        form = c.form
        if form is not None and hasattr(form, 'P') and not hasattr(form, 'rx'):   # torso form
            thetas = {'south': (1.4, -1.4), 'north': (3.14159 - 1.4, 3.14159 + 1.4), 'east': (2.3, 1.3)}[c.dir]
            cx = (form.d if c.dir == 'east' else form.a)(0.28)[0]
            for i, th in enumerate(thetas):
                x, y = form.P(c.dir, th, 0.28, 1.06)
                out = -1 if x < cx else 1
                c.part(f'spike{i}', G.poly([(x - out * 1.0 * k, y - 3.5 * k), (x + out * 8.5 * k, y - 9.5 * k), (x + out * 1.5 * k, y + 3.5 * k)]),
                       'trim', 9, mask=None)
        else:
            for p in list(c.scene.parts):
                if p.name.startswith(('yoke', 'pauldron')):
                    x0, y0, x1, y1 = p.bbox()
                    c.part(p.name + '_spike', G.poly([(x0 + 2 * k, y0 + 2 * k), ((x0 + x1) / 2, y0 - 5 * k), (x1 - 2 * k, y0 + 2 * k)]),
                           'trim', p.z - 0.5, mask=None)


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


# marine / recon / cataphract / bionic helmets are registered by armor3d
HELMET_DESIGNS = {'helm': lambda c: helm_simple(c, 'helm'), 'ballistic': lambda c: helm_simple(c, 'ballistic'),
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
