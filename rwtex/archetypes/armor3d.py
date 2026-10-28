"""Perspective-correct plate armor and helmets on 3D form proxies (see rwtex/form.py).

Plates are authored as patches in surface coordinates - ``(theta, v)`` on the torso,
``(theta, phi)`` on the head - then projected per view and flat-shaded per facet from real
normals with vanilla's quantised tones.  That reproduces what makes marine / recon /
cataphract armor read so well: a FEW crisp planes (white front, grey sides, bright tops,
dark undersides), horizontals that bow with the body, a foreshortened neck ring, and parts
that correctly hide when they face away.

Theta: 0 = front, +pi/2 = the pawn's right side (screen-left in the south view), pi = back.
"""
from __future__ import annotations

import math
from typing import Callable, Optional, Sequence

import numpy as np

from .. import geom as G
from ..color import mix
from ..form import HeadForm, TorsoForm, clip_poly, tone_for
from ..materials import get as getmat
from ..parts import common as C
from ..render import Bevel, Dome, Facets, Fill, Glow, Line, Part
from .apparel import Ctx, DESIGNS, HELMET_DESIGNS, _undersuit, plate_shading

PI = math.pi


def _tones(c: Ctx, role: str):
    m = getmat(c.m(role))
    return (m.light, m.base, m.shade, m.deep)


def splate(c: Ctx, name: str, poly, z: float, role: str = 'shell', r=1.06, cols: Sequence[float] = (),
           rows: Sequence[float] = (), mask='auto', wrap: float = 0.0, bias: int = 0, lines: bool = False,
           cap: bool = True) -> Optional[Part]:
    """Surface plate: projected outline + one flat tone per facet cell (cols x rows).
    ``cap=False`` for rigid plates that should not follow the rounded shoulder dome."""
    form: TorsoForm = c.form
    ring = form.ring(c.dir, poly, r, wrap, cap)
    if len(ring) < 3:
        return None
    tones = _tones(c, role)
    p = c.part(name, ring, role, z, shading=[], mask=mask, tone=tones[1])
    P = np.asarray(poly, float)
    t0, t1 = P[:, 0].min(), P[:, 0].max()
    v0, v1 = P[:, 1].min(), P[:, 1].max()
    tb = [t0] + [x for x in sorted(cols) if t0 < x < t1] + [t1]
    vb = [v0] + [x for x in sorted(rows) if v0 < x < v1] + [v1]
    for i in range(len(tb) - 1):
        col = clip_poly(P, tb[i], tb[i + 1])
        if len(col) < 3:
            continue
        for j in range(len(vb) - 1):
            cell = clip_poly(col[:, ::-1], vb[j], vb[j + 1])
            if len(cell) < 3:
                continue
            cell = cell[:, ::-1]
            n = form.normal(c.dir, (tb[i] + tb[i + 1]) / 2, (vb[j] + vb[j + 1]) / 2)
            idx = min(3, tone_for(n, c.dir) + bias)
            if idx == 1 and not lines:
                continue
            cr = form.ring(c.dir, cell, r, wrap, cap)
            if len(cr) >= 3:
                p.fill(cr, tones[idx])
    return p


def sline(c: Ctx, p: Part, pts_tv, r=1.06, width: float = 1.0, tone='deep', cap: bool = True, **kw) -> None:
    """Engraved line drawn ON the surface (follows the perspective)."""
    form: TorsoForm = c.form
    pts = []
    for a, b in zip(pts_tv[:-1], pts_tv[1:]):
        for t in np.linspace(0, 1, 8, endpoint=False):
            th = a[0] + (b[0] - a[0]) * t
            v = a[1] + (b[1] - a[1]) * t
            if form.normal(c.dir, th, v)[2] > -0.05:
                pts.append(form.P(c.dir, th, v, r, cap))
    th, v = pts_tv[-1]
    if form.normal(c.dir, th, v)[2] > -0.05:
        pts.append(form.P(c.dir, th, v, r, cap))
    if len(pts) >= 2:
        p.details.append(Line(G.poly(pts), width * c.k, tone, **kw))


def sjoint(c: Ctx, name: str, theta: float, v: float, R: float, z: float, r: float = 1.2, glow: bool = True) -> Optional[Part]:
    """Exposed bionic joint cap on the surface (foreshortened by its facing)."""
    form: TorsoForm = c.form
    n = form.normal(c.dir, theta, v)
    if n[2] < 0.05:
        return None
    x, y = form.P(c.dir, theta, v, r)
    rx = R * c.k * max(0.45, n[2])
    ry = R * c.k * 0.85
    jp = c.part(name, G.ellipse(x, y, rx, ry), 'joint', z,
                shading=[Dome(('light', 'base', 'shade'), (-0.3, -0.45), 1.15), Facets(1.0 * c.k, ('light', 'base', 'shade', 'deep'), (0.5, 0.15, -0.7))],
                mask=None)
    jp.detail(Fill([G.ellipse(x, y, rx * 0.52, ry * 0.52)], 'deep', mask=None),
              Fill([G.ellipse(x, y, rx * 0.26, ry * 0.26)], 'energy.base' if glow else 'shade', mask=None))
    return jp


def collar(c: Ctx, z: float = 30) -> None:
    """Foreshortened neck ring (only the front view shows it; the head covers most of it)."""
    if c.dir != 'south':
        return
    form: TorsoForm = c.form
    cs, a = form.a(0.0)
    y = form.y(-0.075)
    k = c.k
    c.part('collar', G.ellipse(cs, y, a * 0.48, a * 0.2), 'trim', z, mask=None,
           shading=[Facets(1.0 * k, ('light', 'base', 'shade', 'deep'), (0.5, 0.15, -0.7))])
    c.part('neck', G.ellipse(cs, y + 0.4 * k, a * 0.34, a * 0.12), 'undersuit', z + 0.1, mask=None, outline=None,
           shading=[Bevel(0, 1.2 * k, shade_tone='deep')])


def fibers(c: Ctx, p: Part, r: float = 1.0) -> None:
    """Artificial-muscle striations following the body surface."""
    if c.dir == 'south':
        for th in (-0.95, -0.6, -0.25, 0.25, 0.6, 0.95):
            sline(c, p, [(th, 0.3), (th * 0.85, 0.78)], r, 0.8, 'light')
        for v in (0.6, 0.67):
            sline(c, p, [(-0.55, v), (0.55, v)], r, 0.8, 'light')
    elif c.dir == 'north':
        for th in (PI - 0.9, PI - 0.5, PI + 0.5, PI + 0.9):
            sline(c, p, [(th, 0.25), (th, 0.8)], r, 0.8, 'light')
    else:
        for th in (0.3, 0.8, 1.3, 1.8, 2.3, 2.8):
            sline(c, p, [(th, 0.3), (th, 0.82)], r, 0.8, 'light')


def _mirror(poly):
    return [(-t, v) for t, v in poly][::-1]


def _back(poly):
    """Mirror a front patch to the back (theta -> pi - theta)."""
    return [(PI - t, v) for t, v in poly][::-1]


def _splay(r0: float, v0: float, k: float):
    return lambda v: r0 + k * max(0.0, v - v0)


# ----------------------------------------------------------------------------- shared pieces

MANTLE_F = [(-2.25, -0.17), (2.25, -0.17), (2.25, 0.24), (1.05, 0.25), (0.5, 0.27), (0.22, 0.2), (-0.22, 0.2), (-0.5, 0.27), (-1.05, 0.25), (-2.25, 0.24)]
MANTLE_B = [(PI - 2.25, -0.17), (PI + 2.25, -0.17), (PI + 2.25, 0.26), (PI - 2.25, 0.26)]
CHEST = [(-1.0, 0.3), (-0.34, 0.28), (0.0, 0.36), (0.34, 0.28), (1.0, 0.3), (0.95, 0.53), (0.0, 0.58), (-0.95, 0.53)]
TASSET = [(0.22, 0.78), (1.25, 0.76), (1.4, 1.03), (0.34, 1.03)]
COD = [(-0.17, 0.79), (0.17, 0.79), (0.14, 1.0), (-0.14, 1.0)]
BELT_F = [(-1.9, 0.655), (1.9, 0.655), (1.9, 0.725), (-1.9, 0.725)]
BELT_B = [(PI - 1.9, 0.655), (PI + 1.9, 0.655), (PI + 1.9, 0.725), (PI - 1.9, 0.725)]
MCOLS = (-1.95, -1.25, -0.55, 0.55, 1.25, 1.95)
BCOLS = tuple(PI + x for x in (-1.95, -1.25, -0.55, 0.55, 1.25, 1.95))


def _lower(c: Ctx, tasset_r=1.05, splay=0.6) -> None:
    for side in (1, -1):
        poly = TASSET if side > 0 else _mirror(TASSET)
        splate(c, f'tasset_{side}', poly, 3, r=_splay(tasset_r, 0.76, splay), cols=(side * 0.75,), wrap=0.35)
        bpoly = _back(poly)
        splate(c, f'tasset_back_{side}', bpoly, 2.5, r=_splay(tasset_r, 0.76, splay), cols=(PI - side * 0.75,), wrap=0.35)
    splate(c, 'codpiece', COD, 3.2, r=1.07)
    splate(c, 'belt', BELT_F, 4, 'strap', r=1.05, cols=(-1.1, -0.4, 0.4, 1.1), mask=None)
    splate(c, 'belt_back', BELT_B, 3.9, 'strap', r=1.05, cols=tuple(PI + x for x in (-1.1, -0.4, 0.4, 1.1)), mask=None)


def _hull(pts: np.ndarray) -> np.ndarray:
    pts = sorted(map(tuple, np.asarray(pts, float)))
    if len(pts) <= 2:
        return np.asarray(pts)

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p_ in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p_) <= 0:
            lower.pop()
        lower.append(p_)
    for p_ in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p_) <= 0:
            upper.pop()
        upper.append(p_)
    return np.asarray(lower[:-1] + upper[:-1])


def slab(c: Ctx, name: str, face, z: float, depth=(0.0, -3.0), role: str = 'shell', mask='auto',
         face_normal=(0.0, 0.0, 1.0), chamfer: float = 1.2) -> Part:
    """Extruded plate seen from the 3/4 camera: the main face plus the thickness faces that
    point toward ``depth`` (screen px; up = top face visible, sideways = outer face visible).
    Every face is lit by its 3D normal with the per-view pawn light, so a pad reads as
    white front / bright top / grey outer side exactly like vanilla marine pads."""
    from ..form import LIGHTS, tone_for
    k = c.k
    face = G.chamfer(np.asarray(face, float), chamfer * k) if chamfer else np.asarray(face, float)
    dv = np.array(depth, float) * k
    back = face + dv
    tones = _tones(c, role)
    hull = _hull(np.vstack([face, back]))
    fn = np.array(face_normal, float)
    fn = fn / np.linalg.norm(fn)
    p = c.part(name, hull, role, z, shading=[], mask=mask, tone=tones[min(3, tone_for(fn, c.dir))])
    n = len(face)
    sa = 0.5 * float(np.dot(face[:, 0], np.roll(face[:, 1], -1)) - np.dot(face[:, 1], np.roll(face[:, 0], -1)))
    for i in range(n):
        a, b = face[i], face[(i + 1) % n]
        e = b - a
        L = float(np.hypot(*e)) or 1.0
        nrm = np.array([e[1], -e[0]]) / L * (1 if sa > 0 else -1)   # outward (screen, y down)
        if float(np.dot(nrm, dv)) <= 0.05:
            continue
        n3 = np.array([nrm[0], -nrm[1], 0.12])
        idx = tone_for(n3 / np.linalg.norm(n3), c.dir)
        quad = np.array([a, b, b + dv, a + dv])
        p.fill(quad, tones[idx])
    p.fill(face, tones[min(3, tone_for(fn, c.dir))])
    return p


def _pads(c: Ctx, z: float = 9, w: float = 0.46, out: float = 0.3, h: float = 0.4, ridge: bool = True) -> None:
    """Shoulder pads as extruded slabs anchored to the torso form (marine/cataphract silhouette)."""
    form: TorsoForm = c.form
    k = c.k
    if c.dir in ('south', 'north'):
        cs, a = form.a(0.08)
        y0 = form.y(-0.02)
        H = form.H
        for side in (1, -1):
            xe = cs + side * a
            face = [(xe - side * a * w, y0 + 2.0 * k), (xe + side * a * (out - 0.12), y0), (xe + side * a * (out + 0.14), y0 + H * h * 0.84),
                    (xe + side * a * (out - 0.04), y0 + H * h), (xe - side * a * w * 0.62, y0 + H * h * 0.92)]
            lim = c.scene.w - 6.0 * c.scene.w / 128
            face = [(min(max(x, 6.0 * c.scene.w / 128 + 2.4 * k), lim - 2.4 * k), y) for x, y in face]
            pd = slab(c, f'pad_{side}', face, z, depth=(side * 2.4, -3.0))
            if ridge:
                pd.line([(xe - side * a * w * 0.7, y0 + H * h * 0.42), (xe + side * a * (out + 0.02), y0 + H * h * 0.45)], 1.0 * k, 'deep')
    else:
        ce, d = form.d(0.3)
        cy = form.y(0.3)
        H = form.H
        hw, hh = d * 0.66, H * 0.2
        face = [(ce - hw, cy - hh), (ce + hw * 0.8, cy - hh), (ce + hw, cy - hh * 0.4), (ce + hw, cy + hh * 0.55),
                (ce + hw * 0.6, cy + hh), (ce - hw * 0.8, cy + hh), (ce - hw, cy + hh * 0.5)]
        pd = slab(c, 'pad', face, z, depth=(2.6, -3.0), chamfer=1.6)
        if ridge:
            pd.line([(ce - hw * 0.8, cy + hh * 0.05), (ce + hw * 0.95, cy + hh * 0.05)], 1.0 * k, 'deep')


def _mantle(c: Ctx, r: float = 1.2) -> None:
    splate(c, 'mantle_back', MANTLE_B, 7.5, r=r, cols=BCOLS, rows=(0.03,), wrap=0.6)
    m = splate(c, 'mantle', MANTLE_F, 8, r=r, cols=MCOLS, rows=(0.03,), wrap=0.6)
    if m is not None:
        sline(c, m, [(-0.62, -0.02), (-0.52, 0.24)], r, 1.1)
        sline(c, m, [(0.62, -0.02), (0.52, 0.24)], r, 1.1)


# ----------------------------------------------------------------------------- body designs

def d3_marine(c: Ctx) -> None:
    """Marine power armor grammar (spacer)."""
    _undersuit(c, fibers=c.p.get('fibers', False))
    pk = splate(c, 'pack', [(PI - 0.45, 0.28), (PI + 0.45, 0.28), (PI + 0.4, 0.64), (PI - 0.4, 0.64)], 6, 'accent', r=1.17,
                cols=(PI - 0.15, PI + 0.15), mask=None)
    splate(c, 'backplate', [(PI - 1.3, 0.3), (PI + 1.3, 0.3), (PI + 1.2, 0.66), (PI - 1.2, 0.66)], 4, r=1.08,
           cols=(PI - 1.0, PI - 0.45, PI + 0.45, PI + 1.0))
    _lower(c)
    ch = splate(c, 'chest', CHEST, 6, r=1.09, cols=(-0.45, 0.45))
    _mantle(c, 1.16)
    _pads(c)
    if c.dir == 'south':
        node = c.part('belt_node', G.ellipse(*c.form.P('south', 0, 0.69, 1.07), 3.2 * c.k, 2.0 * c.k), 'accent', 4.5, mask=None,
                      shading=[Facets(0.8 * c.k)])
    collar(c)


def d3_recon(c: Ctx) -> None:
    """Recon armor grammar: slimmer shells, chevron chest over a dark undersuit, light shoulders."""
    _undersuit(c, fibers=False)
    splate(c, 'backplate', [(PI - 1.1, 0.06), (PI + 1.1, 0.06), (PI + 1.0, 0.6), (PI - 1.0, 0.6)], 4, r=1.06, cols=(PI - 0.4, PI + 0.4))
    for side in (1, -1):
        poly = [(0.25, 0.8), (1.2, 0.78), (1.3, 1.02), (0.35, 1.02)]
        poly = poly if side > 0 else _mirror(poly)
        splate(c, f'thigh_{side}', poly, 3, r=_splay(1.04, 0.78, 0.3), cols=(side * 0.7,), wrap=0.25)
        splate(c, f'thigh_back_{side}', _back(poly), 2.5, r=_splay(1.04, 0.78, 0.3), wrap=0.25)
    chev = [(-1.05, 0.2), (0.0, 0.42), (1.05, 0.2), (1.0, 0.36), (0.0, 0.58), (-1.0, 0.36)]
    splate(c, 'chevron', chev, 6, r=1.07, cols=(-0.45, 0.45))
    for side in (1, -1):
        sh = [(0.55, -0.15), (1.95, -0.1), (2.05, 0.24), (0.7, 0.2)]
        splate(c, f'shoulder_{side}', sh if side > 0 else _mirror(sh), 8, r=1.14, cols=(side * 1.25,), rows=(0.03,), wrap=0.5)
    collar(c)


def d3_cataphract(c: Ctx) -> None:
    """Cataphract grammar: massive layered pauldrons, tall back fins, heavy smooth shells."""
    _undersuit(c, fibers=c.p.get('fibers', False))
    if c.p.get('fins', True):
        for side in (1, -1):
            fin = [(PI - side * 0.55, -0.45), (PI - side * 0.25, -0.45), (PI - side * 0.22, 0.25), (PI - side * 0.6, 0.25)]
            splate(c, f'fin_{side}', fin, 1 if c.dir != 'north' else 9, r=1.12, wrap=0.2)
    splate(c, 'backplate', [(PI - 1.3, 0.28), (PI + 1.3, 0.28), (PI + 1.2, 0.68), (PI - 1.2, 0.68)], 4, r=1.1,
           cols=(PI - 1.0, PI - 0.4, PI + 0.4, PI + 1.0))
    _lower(c, 1.07, 0.7)
    splate(c, 'chest', [(-1.2, 0.2), (-0.4, 0.18), (0.0, 0.28), (0.4, 0.18), (1.2, 0.2), (1.12, 0.56), (0.0, 0.64), (-1.12, 0.56)], 6, r=1.11,
           cols=(-0.42, 0.42))
    _mantle(c, 1.18)
    for side in (1, -1):
        pd = [(0.55, -0.24), (2.2, -0.2), (2.3, 0.3), (1.6, 0.42), (0.7, 0.34)]
        pdp = pd if side > 0 else _mirror(pd)
        splate(c, f'pauldron_{side}', pdp, 9, r=1.34, cols=(side * 1.05, side * 1.6), rows=(0.03,), wrap=0.75)
    collar(c)


def d3_bionic(c: Ctx) -> None:
    """Bionic assault suit: marine mantle + recon segmented abdomen + cataphract-height
    pauldron line over an artificial-muscle undersuit; exposed bionic joints, a segmented
    bionic spine and a chest power core (DMS bionic-suit + vanilla bionic palettes)."""
    glow = c.p.get('glow', True)
    us = _undersuit(c, fibers=False)
    fibers(c, us)
    # spine: a protruding column - surface patch from behind, extruded slab from the side
    if c.dir == 'east':
        form: TorsoForm = c.form
        k = c.k
        ce, dd = form.d(0.35)
        xb = ce - dd * 1.02
        y0, y1 = form.y(-0.06), form.y(0.88)
        sp = slab(c, 'spine', [(xb - 1.2 * k, y0), (xb + 2.6 * k, y0), (xb + 2.6 * k, y1), (xb - 1.2 * k, y1)], 2,
                  depth=(-2.2, -1.5), role='accent', mask=None, face_normal=(-0.3, 0.0, 1.0), chamfer=1.0)
        for i, v in enumerate(np.arange(-0.03, 0.84, 0.1)):
            yy = form.y(v)
            sp.fill(G.chamfer(G.rect(xb - 3.0 * k, yy, xb + 1.6 * k, yy + 3.2 * k), 0.6 * k), 'trim.base', clip=False)
            if glow and i % 2 == 1:
                sp.fill(G.circle(xb - 0.8 * k, yy + 1.6 * k, 0.9 * k), 'energy.base', mask=None, clip=False)
        sp = None
    else:
        sp = splate(c, 'spine', [(PI - 0.24, -0.12), (PI + 0.24, -0.12), (PI + 0.22, 0.9), (PI - 0.22, 0.9)], 9, 'accent', r=1.22,
                    cols=(PI - 0.08, PI + 0.08), mask=None, wrap=0.0)
    if sp is not None:
        for i, v in enumerate(np.arange(-0.06, 0.84, 0.1)):
            seg = splate(c, f'vertebra{i}', [(PI - 0.17, v), (PI + 0.17, v), (PI + 0.17, v + 0.065), (PI - 0.17, v + 0.065)], 9.2,
                         'trim', r=1.26, cols=(PI - 0.06, PI + 0.06), mask=None, wrap=0.3)
            if glow and seg is not None and i % 2 == 1:
                x, y = c.form.P(c.dir, PI, v + 0.033, 1.27)
                seg.detail(Fill([G.ellipse(x, y, 1.0 * c.k, 0.9 * c.k)], 'energy.base', mask=None))
    for side in (1, -1):
        bp = [(PI - side * 0.32, 0.3), (PI - side * 1.25, 0.3), (PI - side * 1.15, 0.66), (PI - side * 0.32, 0.66)]
        splate(c, f'backplate_{side}', bp, 4, r=1.08, cols=(PI - side * 0.8,))
    _lower(c)
    for i in range(2):
        v0 = 0.575 + i * 0.075
        ab = [(-0.75, v0), (0.75, v0), (0.72, v0 + 0.055), (-0.72, v0 + 0.055)]
        splate(c, f'abs{i}', ab, 5, r=1.06, cols=(-0.35, 0.35))
    ch = splate(c, 'chest', CHEST, 6, r=1.09, cols=(-0.45, 0.45))
    if ch is not None and glow:
        sline(c, ch, [(-0.78, 0.3), (-0.72, 0.48)], 1.09, 1.0, 'energy.base', mask=None)
        sline(c, ch, [(0.78, 0.3), (0.72, 0.48)], 1.09, 1.0, 'energy.base', mask=None)
    _mantle(c, 1.16)
    _pads(c, w=0.42, out=0.26, h=0.36)
    if c.dir == 'south':
        x, y = c.form.P('south', 0, 0.255, 1.12)
        core = c.part('core', G.ellipse(x, y, 3.4 * c.k, 2.4 * c.k), 'joint', 8.5, mask=None,
                      shading=[Dome(('light', 'base', 'shade'), (-0.3, -0.4), 1.1), Facets(0.9 * c.k)])
        core.detail(Fill([G.ellipse(x, y, 2.0 * c.k, 1.4 * c.k)], 'energy.base', mask=None),
                    Fill([G.ellipse(x - 0.6 * c.k, y - 0.4 * c.k, 0.8 * c.k, 0.5 * c.k)], 'energy.light', mask=None))
        x, y = c.form.P('south', 0, 0.69, 1.07)
        node = c.part('belt_node', G.ellipse(x, y, 2.8 * c.k, 1.8 * c.k), 'joint', 4.5, mask=None, shading=[Facets(0.8 * c.k)])
        node.detail(Fill([G.ellipse(x, y, 1.3 * c.k, 0.8 * c.k)], 'energy.base', mask=None))
    for side in (1, -1):
        sjoint(c, f'shoulder_joint_{side}', side * 1.45, 0.42, 2.8, 9.5, r=1.22, glow=glow)
        sjoint(c, f'hip_joint_{side}', side * 1.3, 0.74, 2.8, 5, r=1.08, glow=glow)
    collar(c)


# ----------------------------------------------------------------------------- helmets

def hpanel(c: Ctx, name: str, poly, z: float, role: str = 'shell', r: float = 1.05, cols=(), rows=(), mask='auto', base_ring=None,
           bias: int = 0) -> Optional[Part]:
    hf: HeadForm = c.form
    ring = base_ring if base_ring is not None else hf.ring(poly, r)
    if len(ring) < 3:
        return None
    tones = _tones(c, role)
    p = c.part(name, ring, role, z, shading=[], mask=mask, tone=tones[1])
    P = np.asarray(poly, float)
    t0, t1 = P[:, 0].min(), P[:, 0].max()
    f0, f1 = P[:, 1].min(), P[:, 1].max()
    tb = [t0] + [x for x in sorted(cols) if t0 < x < t1] + [t1]
    fb = [f0] + [x for x in sorted(rows) if f0 < x < f1] + [f1]
    for i in range(len(tb) - 1):
        col = clip_poly(P, tb[i], tb[i + 1])
        if len(col) < 3:
            continue
        for j in range(len(fb) - 1):
            cell = clip_poly(col[:, ::-1], fb[j], fb[j + 1])
            if len(cell) < 3:
                continue
            cell = cell[:, ::-1]
            n = hf.normal((tb[i] + tb[i + 1]) / 2, (fb[j] + fb[j + 1]) / 2)
            if n[2] < -0.05:
                continue
            idx = min(3, tone_for(n, c.dir) + bias)
            if idx == 1:
                continue
            cr = hf.ring(cell, r)
            if len(cr) >= 3:
                p.fill(cr, tones[idx])
    return p


def _hshell(c: Ctx, cols=(-1.3, -0.48, 0.48, 1.3), rows=(0.62,), expand: float = -1.2) -> Part:
    shell = [(-PI, -1.3), (PI, -1.3), (PI, 1.57), (-PI, 1.57)]
    return hpanel(c, 'shell', shell, 5, r=1.12, cols=(-2.2,) + tuple(cols) + (2.2,), rows=rows, base_ring=c.f.silhouette(expand))


def h3_marine(c: Ctx) -> None:
    hf: HeadForm = c.form
    _hshell(c)
    hpanel(c, 'ridge', [(-0.17, 0.25), (0.17, 0.25), (0.15, 1.45), (-0.15, 1.45)], 6, r=1.13, rows=(0.9,))
    visor = [(-1.08, -0.02), (-0.36, 0.03), (0.0, -0.06), (0.36, 0.03), (1.08, -0.02), (0.98, -0.32), (0.32, -0.38), (0.0, -0.3),
             (-0.32, -0.38), (-0.98, -0.32)]
    vp = hpanel(c, 'visor', visor, 7, 'lens', r=1.1, cols=(-0.45, 0.45), mask=None)
    if vp is not None:
        for t0, t1 in ((-0.85, -0.2), (0.2, 0.85)):
            eye = [(t0, -0.08), (t1, -0.04), (t1 - 0.05, -0.22), (t0 + 0.05, -0.24)]
            r_ = hf.ring(eye, 1.11)
            if len(r_) >= 3:
                vp.fill(r_, 'accent.base')
    hpanel(c, 'chin', [(-0.32, -0.55), (0.32, -0.55), (0.25, -0.95), (-0.25, -0.95)], 6.5, r=1.1, cols=(-0.12, 0.12))


def h3_recon(c: Ctx) -> None:
    hf: HeadForm = c.form
    _hshell(c, cols=(-1.0, 1.0))
    visor = [(-1.0, 0.1), (1.0, 0.1), (0.9, -0.28), (0.0, -0.42), (-0.9, -0.28)]
    hpanel(c, 'visor', visor, 7, 'accent', r=1.1, cols=(-0.4, 0.4), mask=None)
    for side in (1, -1):
        th = side * 1.45
        n = hf.normal(th, 0.2)
        if n[2] > -0.2:
            x, y = hf.P(th, 0.35, 1.12)
            c.part(f'antenna_{side}', G.rounded(G.rect(x - 1.4 * c.k, y - 12 * c.k, x + 1.4 * c.k, y + 4 * c.k), 1.0 * c.k), 'accent', 8, mask=None,
                   shading=[Facets(0.8 * c.k)])


def h3_cataphract(c: Ctx) -> None:
    _hshell(c, cols=(-1.15, -0.4, 0.4, 1.15), rows=(0.55,), expand=-0.6)
    if c.p.get('crest'):
        hpanel(c, 'crest', [(-0.14, 0.4), (0.14, 0.4), (0.14, 1.57), (-0.14, 1.57)], 7.5, 'trim', r=1.3, mask=None)
    hpanel(c, 'brow', [(-1.15, 0.2), (1.15, 0.2), (1.12, 0.05), (-1.12, 0.05)], 6, r=1.13, cols=(-0.45, 0.45))
    hpanel(c, 'slit', [(-1.0, 0.03), (1.0, 0.03), (0.98, -0.08), (-0.98, -0.08)], 6.5, 'accent', r=1.13, mask=None)
    hpanel(c, 'jaw', [(-0.85, -0.18), (0.85, -0.18), (0.55, -0.95), (-0.55, -0.95)], 7, r=1.12, cols=(-0.3, 0.3))


def h3_bionic(c: Ctx) -> None:
    hf: HeadForm = c.form
    glow = c.p.get('glow', True)
    _hshell(c)
    hpanel(c, 'ridge', [(-0.16, 0.3), (0.16, 0.3), (0.14, 1.45), (-0.14, 1.45)], 6, r=1.13, rows=(0.9,))
    face = [(-1.05, 0.14), (1.05, 0.14), (1.0, -0.38), (0.55, -0.95), (-0.55, -0.95), (-1.0, -0.38)]
    fp = hpanel(c, 'face', face, 6.5, r=1.1, cols=(-0.5, 0.5), rows=(-0.45,))
    band = hpanel(c, 'band', [(-1.12, 0.06), (1.12, 0.06), (1.1, -0.1), (-1.1, -0.1)], 7, 'accent', r=1.12, cols=(-0.5, 0.5), mask=None)
    if band is not None and glow:
        pts = [hf.P(t, -0.02, 1.13) for t in np.linspace(-1.0, 0.1, 10) if hf.normal(t, -0.02)[2] > 0]
        if len(pts) > 1:
            band.details.append(Line(G.poly(pts), 1.0 * c.k, 'energy.base', mask=None))
    # bionic eye on the pawn's left (screen right in south view): vanilla bionic-eye palette
    th, ph = -0.42, -0.02
    if hf.normal(th, ph)[2] > 0.1:
        x, y = hf.P(th, ph, 1.15)
        nz = hf.normal(th, ph)[2]
        rx, ry = 4.6 * c.k * max(0.5, nz), 4.4 * c.k
        e = c.part('eye', G.ellipse(x, y, rx, ry), 'joint', 8, mask=None,
                   shading=[Dome(('light', 'base', 'shade'), (-0.3, -0.45), 1.15), Facets(0.9 * c.k)])
        e.detail(Fill([G.ellipse(x, y, rx * 0.7, ry * 0.7)], 'black', mask=None),
                 Fill([G.ellipse(x, y, rx * 0.48, ry * 0.48)], 'lens.base', mask=None),
                 Fill([G.ellipse(x - rx * 0.18, y - ry * 0.2, rx * 0.15, ry * 0.15)], 'energy.light', mask=None))
    if fp is not None:
        for t in (-0.2, 0.0, 0.2):
            if hf.normal(t, -0.7)[2] > 0.1:
                x, y = hf.P(t, -0.7, 1.11)
                fp.fill(G.rounded(G.rect(x - 0.9 * c.k, y - 2.2 * c.k, x + 0.9 * c.k, y + 2.2 * c.k), 0.6 * c.k), 'deep')
    for side in (1, -1):
        th = side * 1.5
        if hf.normal(th, -0.15)[2] > 0.15:
            x, y = hf.P(th, -0.15, 1.12)
            jp = c.part(f'earport_{side}', G.ellipse(x, y, 3.4 * c.k, 3.6 * c.k), 'joint', 7.5, mask=None,
                        shading=[Dome(('light', 'base', 'shade'), (-0.3, -0.45), 1.15), Facets(0.9 * c.k)])
            jp.detail(Fill([G.ellipse(x, y, 1.7 * c.k, 1.8 * c.k)], 'deep', mask=None))
    if c.dir == 'north':
        port = hpanel(c, 'port', [(PI - 0.35, -0.25), (PI + 0.35, -0.25), (PI + 0.3, -1.1), (PI - 0.3, -1.1)], 7, 'accent', r=1.12,
                      cols=(PI - 0.12, PI + 0.12), mask=None)
        if port is not None:
            for i, ph_ in enumerate((-0.4, -0.62, -0.84)):
                x, y = hf.P(PI, ph_, 1.14)
                port.fill(G.chamfer(G.rect(x - 3.2 * c.k, y - 1.3 * c.k, x + 3.2 * c.k, y + 1.3 * c.k), 0.6 * c.k), 'trim.base')
                if glow and i == 1:
                    port.fill(G.circle(x, y, 0.9 * c.k), 'energy.base', mask=None)


DESIGNS.update({'marine': d3_marine, 'recon': d3_recon, 'cataphract': d3_cataphract, 'bionic': d3_bionic})
HELMET_DESIGNS.update({'marine': h3_marine, 'recon': h3_recon, 'cataphract': h3_cataphract, 'bionic': h3_bionic})
FORM_DESIGNS = {'marine', 'recon', 'cataphract', 'bionic'}
