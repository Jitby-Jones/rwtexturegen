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
from typing import Callable, Optional, Sequence, Tuple

import numpy as np

from .. import geom as G
from ..form import HeadForm, TorsoForm, clip_poly
from ..materials import get as getmat
from ..render import Dome, Facets, Fill, Line, Part
from .apparel import Ctx, DESIGNS, HELMET_DESIGNS

PI = math.pi


def _tones(c: Ctx, role: str):
    m = getmat(c.m(role))
    return (m.light, m.base, m.shade, m.deep)


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


# ----------------------------------------------------------------------------- vanilla plate kit
#
# Calibrated on vanilla PowerArmor / ReconArmor in every body type and view (the footprint
# tables are in docs/STYLE_GUIDE.md section 6):
#   * the shell HUGS the body: its coloured edge stays within about -4..+4 px of the naked
#     silhouette and the 3.4 px black outline does the rest; the waist pinches under the chest;
#   * every large face is ONE flat value - white where it faces the pawn's front, #ccc on the
#     camera-facing side in the east view and over the whole back, #999 for low back plates;
#   * chamfers are narrow grey strips, plates are separated by black-dark-black seams and the
#     exposed undersuit (belt, tasset gaps) is near-black;
#   * shell and belt sit LOWER at the front than at the back - that is what tilts the belt
#     into a diagonal in the east view.

_FIT: Optional[dict] = None


def fit(c: Ctx, key: str, v0: float = -1.0, v1: float = 2.0):
    """Measured vanilla marine-armor silhouette offsets for this body type: (v, px) pairs.
    ``key``: south | north | east_back | east_front (rwtex/data/armor_fit.json)."""
    global _FIT
    if _FIT is None:
        import json
        import os
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'armor_fit.json'), encoding='utf-8') as f:
            _FIT = json.load(f)
    row = _FIT['bodies'].get(c.bt, _FIT['bodies']['Male'])[key]
    return [(v, o) for v, o in zip(_FIT['v'], row) if o is not None and v0 <= v <= v1]


def fit_top(c: Ctx, view: Optional[str] = None) -> float:
    fit(c, 'south')
    return float(_FIT['bodies'].get(c.bt, _FIT['bodies']['Male'])[(view or ('south' if c.dir == 'east' else c.dir)) + '_top'])


def layout(c: Ctx) -> dict:
    """Measured vanilla plate boundaries for this body type (chest/shell bottoms, belt and
    tasset bands at the front and the back) as surface v.  They were measured on screen at the
    body's centre line, where the projection drops the camera-facing surface by half the
    TILT bow, so that drop is taken back out here."""
    from ..form import TILT
    fit(c, 'south')
    form: TorsoForm = c.form
    raw = _FIT['layout'].get(c.bt, _FIT['layout']['Male'])
    return {key: v - 0.5 * TILT * form.d(v)[1] / form.H for key, v in raw.items()}


def offr(c: Ctx, table, back_table=None) -> Callable:
    """Radius function that puts a plate's coloured edge ``px`` beyond the body silhouette in
    the current view; ``table`` holds (v, px at 128) pairs, linearly interpolated.  In the east
    view ``back_table`` (if given) applies to the back half, ``table`` to the front half."""
    form: TorsoForm = c.form
    k = c.k

    def interp(tb):
        vs = np.array([t[0] for t in tb], float)
        px = np.array([t[1] for t in tb], float) * k
        return lambda v: float(np.interp(v, vs, px))
    ext = form.d if c.dir == 'east' else form.a
    f_front = interp(table)
    if back_table is None or c.dir != 'east':
        def r(v: float) -> float:
            return max(0.2, 1.0 + f_front(v) / max(ext(v)[1], 1.0))
        return r
    f_back = interp(back_table)

    def r2(v: float, th: float) -> float:
        w = 0.5 - 0.5 * float(np.clip(math.cos(th) / 0.35, -1.0, 1.0))
        o = f_front(v) * (1 - w) + f_back(v) * w
        return max(0.2, 1.0 + o / max(ext(v)[1], 1.0))
    r2.by_theta = True
    return r2


def vtone(view: str, th: float, v: float) -> int:
    """Vanilla value rule (pawn-relative light): 1 = base white facing the pawn's front,
    2 = #ccc on the camera-facing side in the east view and everywhere in the north view."""
    if view == 'south':
        return 1
    if view == 'north':
        return 2
    return 1 if math.cos(th) > 0.8 else 2


FACET_TOL = 0.9   # px at 128: projected curves are straightened into facets (vanilla's crisp, geometric outlines)


def vplate(c: Ctx, name: str, poly, z: float, role: str = 'shell', r=1.0, cols: Sequence[float] = (),
           rows: Sequence[float] = (), tone: Optional[Callable] = None, bias: int = 0, gap: float = 0.0,
           within: Optional[Part] = None, mask='auto', wrap: float = 0.0, cap: bool = True,
           facet: float = FACET_TOL) -> Optional[Part]:
    """Plate on the torso form: projected outline, one flat value per (cols x rows) cell from
    ``tone(view, theta, v)`` (default :func:`vtone`) + ``bias``, and an optional ``gap`` (px) of
    exposed dark undersuit around it - the vanilla black-dark-black seam - clipped to ``within``.
    ``facet`` straightens the projected curves into a few straight segments (px tolerance)."""
    form: TorsoForm = c.form
    ring = form.ring(c.dir, poly, r, wrap, cap)
    if len(ring) < 3:
        return None
    if facet > 0:
        ring = G.simplify_ring(ring, facet * c.k)
    tf = tone or vtone
    tones = _tones(c, role)
    P = np.asarray(poly, float)
    t0, t1 = P[:, 0].min(), P[:, 0].max()
    v0, v1 = P[:, 1].min(), P[:, 1].max()
    tb = [t0] + [x for x in sorted(cols) if t0 < x < t1] + [t1]
    vb = [v0] + [x for x in sorted(rows) if v0 < x < v1] + [v1]
    cells = []
    for i in range(len(tb) - 1):
        col = clip_poly(P, tb[i], tb[i + 1])
        if len(col) < 3:
            continue
        for j in range(len(vb) - 1):
            cell = clip_poly(col[:, ::-1], vb[j], vb[j + 1])
            if len(cell) < 3:
                continue
            cr = form.ring(c.dir, cell[:, ::-1], r, wrap, cap)
            if len(cr) < 3:
                continue
            if facet > 0:
                cr = G.simplify_ring(cr, facet * c.k)
            idx = int(np.clip(tf(c.dir, (tb[i] + tb[i + 1]) / 2, (vb[j] + vb[j + 1]) / 2) + bias, 0, 3))
            cells.append((idx, cr, abs(G.signed_area(cr))))
    if cells:
        areas: dict = {}
        for idx, _, a in cells:
            areas[idx] = areas.get(idx, 0.0) + a
        base = max(areas, key=areas.get)
    else:
        base = int(np.clip(tf(c.dir, (t0 + t1) / 2, (v0 + v1) / 2) + bias, 0, 3))
    if gap > 0:
        c.part(name + '_gap', G.offset(ring, gap * c.k), 'undersuit', z - 0.01, shading=[], mask=None, tone='base',
               silhouette=False, clip=within.rings if within is not None else None)
    p = c.part(name, ring, role, z, shading=[], mask=mask, tone=tones[base])
    for idx, cr, _ in cells:
        if idx != base:
            p.fill(cr, tones[idx])
    return p


def edge(front: float, back: float) -> Callable[[float], float]:
    """A horizontal edge that sits at ``front`` on the pawn's front and ``back`` at its back."""
    return lambda th: back + (front - back) * (0.5 + 0.5 * math.cos(th))


def band(th0: float, th1: float, top, bot, n: int = 36):
    """(theta, v) polygon between two edges (floats or theta -> v callables)."""
    f = top if callable(top) else (lambda th, _v=top: _v)
    g = bot if callable(bot) else (lambda th, _v=bot: _v)
    ts = np.linspace(th0, th1, n)
    return [(t, f(t)) for t in ts] + [(t, g(t)) for t in ts[::-1]]


def around(c: Ctx) -> Tuple[float, float]:
    """Theta range of a full wrap-around band whose visible half is contiguous in this view."""
    return {'south': (-PI, PI), 'east': (-PI / 2, 3 * PI / 2), 'north': (0.0, 2 * PI)}[c.dir]


def mirror(poly):
    return [(-t, v) for t, v in poly][::-1]


def back(poly):
    """Mirror a front patch to the back (theta -> pi - theta)."""
    return [(PI - t, v) for t, v in poly][::-1]


def base_suit(c: Ctx, fibers_: bool = False, from_v: float = 0.36) -> Part:
    """Near-black undersuit: what shows in the belt and tasset gaps.  It starts below the
    shoulders (``from_v``) so the shell alone shapes the top of the silhouette - vanilla leaves
    the body bare where the shell is cut back (east view, under the head)."""
    c.scene.occlusion = None
    form: TorsoForm = c.form
    ring = c.f.silhouette(0.4)
    y_cut = form.y(from_v)
    cut = clip_poly(ring[:, ::-1], y_cut, 1e6)[:, ::-1] if from_v > 0 else ring
    p = c.part('undersuit', cut if len(cut) >= 3 else ring, 'undersuit', 0, shading=[], mask=None, tone='base')
    if fibers_:
        fibers(c, p)
    return p


def neck_ring(c: Ctx, z: float = 8.0, style: str = 'round') -> float:
    """Vanilla neck opening (front view): a big dark foreshortened hole inside a light collar
    lip that is thickest at the front (``round``, marine), the same with a raised gorget ring
    (``gorget``, cataphract) or a deep V opening (``v``, recon - see :func:`neck_v`).  Returns
    the screen y just below the lip, where the chest plate starts."""
    form: TorsoForm = c.form
    k = c.k
    a_sh = max(form.a(v)[1] for v in (0.25, 0.3, 0.35))
    rx = max(0.33 * a_sh + 4.0 * k, 9.0 * k)
    ry = 0.115 * form.H
    cs, cy = form.a(0.18)[0], form.y(0.18)
    grow = 2.4 * k if style == 'gorget' else 0.0
    lip_ry = ry + 1.5 * k + grow
    lip_cy = cy + 2.0 * k + grow * 0.5
    lip_bot = lip_cy + lip_ry
    if c.dir != 'south':
        return lip_bot
    c.part('collar_gap', G.ellipse(cs, lip_cy, rx + 3.4 * k + grow, lip_ry + 1.4 * k), 'undersuit', z - 0.02, shading=[], mask=None,
           tone='base', silhouette=False)
    col = c.part('collar', G.ellipse(cs, lip_cy, rx + 2.0 * k + grow, lip_ry), 'shell', z, shading=[], tone=_tones(c, 'shell')[2])
    if style == 'gorget':
        col.fill(G.ellipse(cs, lip_cy - 0.6 * k, rx + 2.0 * k + grow * 0.45, lip_ry - grow * 0.55), _tones(c, 'shell')[1])
    c.part('neck', G.ellipse(cs, cy, rx, ry), 'undersuit', z + 0.1, shading=[], mask=None, tone='base')
    return lip_bot


def neck_v(c: Ctx, v_top: float, v_pt: float, z: float = 8.0) -> None:
    """Recon collar: a deep V of dark undersuit edged by a light lip; the shell becomes a yoke."""
    lip = [(-0.86, v_top), (0.86, v_top), (0.0, v_pt + 0.06)]
    vplate(c, 'collar', lip, z, tone=lambda *_: 2, gap=1.6)
    vplate(c, 'neck', [(-0.7, v_top - 0.01), (0.7, v_top - 0.01), (0.0, v_pt)], z + 0.1, 'undersuit', tone=lambda *_: 1, mask=None)


def node(c: Ctx, name: str, theta: float, v: float, R: float, z: float, r: float = 1.0, role: str = 'undersuit',
         glow: bool = False) -> Optional[Part]:
    """Round fitting (belt node, power core) foreshortened by its facing."""
    form: TorsoForm = c.form
    n = form.normal(c.dir, theta, v)
    if n[2] < 0.2:
        return None
    x, y = form.P(c.dir, theta, v, r)
    rx, ry = R * c.k * max(0.5, n[2]), R * c.k
    tn = _tones(c, role)
    p = c.part(name, G.ellipse(x, y, rx, ry), role, z, shading=[], mask=None, tone=tn[1])
    p.fill(G.ellipse(x, y - ry * 0.25, rx * 0.62, ry * 0.5), tn[0])
    if glow:
        p.fill(G.ellipse(x, y, rx * 0.45, ry * 0.45), 'energy.base', mask=None)
    return p


# ----------------------------------------------------------------------------- body designs

def _v_at(c: Ctx, y: float, theta: float = 0.0, r=1.0) -> float:
    """Surface v whose projection (at ``theta``) lands on screen height ``y``."""
    form: TorsoForm = c.form
    v = (y - form.top) / form.H
    for _ in range(3):
        v -= (form.P(c.dir, theta, v, r(v) if callable(r) else r)[1] - y) / form.H
    return v


def marine_kit(c: Ctx, *, shell_add: float = 0.0, neck: str = 'round', chest_w: float = 0.9, pauldron_add: float = 0.0,
               chest: bool = True, pauldron: bool = True, spine: bool = True, tassets: bool = True, node_: bool = True) -> dict:
    """The vanilla marine construction shared by every power-armor design: silhouettes follow
    the measured vanilla PowerArmor fit for each body type (rwtex/data/armor_fit.json), the
    internal plates are parametric.  ``shell_add`` widens (+px) or slims (-px) the shell,
    ``neck`` is round | gorget | v, ``chest_w`` the chest plate half-width (theta) - a narrower
    chest shows more of the shoulder flanks - and ``pauldron_add`` grows the east pauldron (px).
    Returns the main parts so variants can build on them."""
    form: TorsoForm = c.form
    k = c.k
    out: dict = {}
    L = layout(c)
    front_bot, back_bot, belt_front, belt_back = L['front_bot'], L['back_bot'], L['belt_front'], L['belt_back']
    bot = edge(front_bot, back_bot)
    lo, hi = around(c)
    v_top = fit_top(c)
    add = lambda tb: [(v, o + shell_add * min(1.0, max(0.0, (v - v_top) / 0.12))) for v, o in tb]
    if c.dir == 'east':
        sr = offr(c, add(fit(c, 'east_front', 0, 0.62)), add(fit(c, 'east_back', 0, 0.5)))
    else:
        sr = offr(c, add(fit(c, c.dir, 0, front_bot if c.dir == 'south' else back_bot)))
    shell = vplate(c, 'shell', band(lo, hi, v_top, bot, 90), 5, r=sr, cols=(-0.64, 0.64))
    out['shell'] = shell
    v_pt = layout(c)['front_bot'] - 0.24
    if neck == 'v':
        if c.dir == 'south':
            neck_v(c, v_top, v_pt)
        lip_bot = form.y(v_pt)
    else:
        lip_bot = neck_ring(c, style=neck)
    # belt: near-black band with dark segments, lower at the front than at the back
    btop = edge(front_bot - 0.012, back_bot - 0.01)
    bbot = edge(belt_front, belt_back)
    belt_r = offr(c, [(0.4, -2.5), (0.8, -3.0)])
    belt = vplate(c, 'belt', band(lo, hi, btop, bbot, 90), 4, 'undersuit', r=belt_r, tone=lambda *_: 3 if c.dir == 'south' else 1,
                  mask=None)
    if belt is not None:
        seg_top = edge(front_bot - 0.012, back_bot - 0.01)
        seg_bot = edge(front_bot + 0.03, back_bot + 0.035)
        for t0, t1 in ((0.22, 0.55), (-0.55, -0.22), (PI - 0.45, PI + 0.45)):
            r_ = form.ring(c.dir, band(t0, t1, seg_top, seg_bot, 10), belt_r)
            if len(r_) >= 3:
                belt.fill(r_, 'undersuit.base')
    out['belt'] = belt
    if chest and c.dir in ('south', 'east'):
        cr = offr(c, [(0.3, 0.3), (0.45, 0.3), (0.6, -0.5)])
        a_ = form.a(0.4)[1]
        rx_lip = max(0.33 * max(form.a(v)[1] for v in (0.25, 0.3, 0.35)) + 4.0 * k, 9.0 * k)
        tn = math.asin(min(0.95, 0.68 * rx_lip / max(a_, 1.0)))
        vn = _v_at(c, lip_bot + 2.2 * k, 0.0, cr) if c.dir == 'south' else 0.4
        top_c = min(vn - 0.05, 0.335)
        cw = chest_w - (0.08 if c.bt == 'Thin' else 0.0)
        bottom = [(-cw - 0.02, 0.49), (-cw + 0.04, 0.57), (-0.6, front_bot - 0.005), (-0.16, front_bot - 0.005), (-0.13, front_bot - 0.035),
                  (0.13, front_bot - 0.035), (0.16, front_bot - 0.005), (0.6, front_bot - 0.005), (cw - 0.04, 0.57), (cw + 0.02, 0.49)]
        if neck == 'v':
            top_c = v_top + 0.17
            cpoly = [(cw, top_c), (0.0, v_pt + 0.085), (-cw, top_c)] + bottom
        else:
            cpoly = [(cw, top_c + 0.02), (0.62, top_c), (tn + 0.08, vn - 0.05), (tn, vn), (-tn, vn), (-tn - 0.08, vn - 0.05),
                     (-0.62, top_c), (-cw, top_c + 0.02)] + bottom
        fv = top_c + 0.06
        fc = cw - 0.24
        out['chest'] = vplate(c, 'chest', cpoly, 6, r=cr, cols=(-fc, fc), rows=(fv,),
                              tone=lambda view, th, v: (2 if abs(th) > fc and v > fv else 1) if view == 'south' else vtone(view, th, v),
                              gap=2.6, within=shell)
    if pauldron and c.dir == 'east':
        pb = front_bot + 0.06
        pp = [(1.25, 0.25), (0.75, 0.28), (0.45, 0.4), (0.42, pb - 0.12), (0.55, pb - 0.05), (0.75, pb), (1.15, pb),
              (1.4, pb - 0.07), (1.66, pb - 0.17), (1.66, 0.38)]
        out['pauldron'] = vplate(c, 'pauldron', pp, 7, r=offr(c, [(0.2, 1.5 + pauldron_add), (0.7, 1.5 + pauldron_add)]), cols=(1.12,),
                                 tone=lambda view, th, v: 1 if th < 1.12 else 2, gap=2.6, within=shell)
    if spine and c.dir == 'north':
        sb = L['spine_bot']
        sp = [(PI - 0.95, v_top), (PI + 0.95, v_top), (PI + 0.33, 0.2), (PI + 0.3, sb), (PI - 0.3, sb), (PI - 0.33, 0.2)]
        out['spine'] = vplate(c, 'backplate', sp, 6, r=offr(c, [(0.1, 0.3), (0.5, 0.3)]), rows=(sb - 0.025,),
                              tone=lambda view, th, v: 3 if v > sb - 0.025 else 2, gap=2.6, within=shell)
    if tassets:
        low = lambda key: fit(c, key, belt_front - 0.03, L['tasset_bot'] + 0.04) or [(0.7, 2.0), (1.0, 0.0)]
        a_hip = form.a(0.8)[1]
        sw = max(4.5, min(8.0, 0.3 * a_hip / k + 0.8))       # side tasset width, px at 128
        if c.dir == 'south':
            v0, v1 = L['tasset_c_top'], L['tasset_bot']
            vm = v0 + 0.022
            ct = [(-0.37, v0), (-0.12, v0), (-0.08, vm + 0.005), (0.08, vm + 0.005), (0.12, v0), (0.37, v0), (0.3, v1), (-0.3, v1)]
            out['tasset_c'] = vplate(c, 'tasset_c', ct, 3, r=offr(c, [(v0, 0.5), (v1, 0.0)]), rows=(vm, v1 - 0.025),
                                     tone=lambda view, th, v: 2 if v < vm else (3 if v > v1 - 0.025 else 1))
            tr = offr(c, low('south'))
            s0, s1 = belt_front + 0.01, v1 - 0.04
            sd = [(1.75, s0)]
            for i, v in enumerate(np.linspace(s0, s1, 4)):
                ext = form.a(v)[1] * tr(v)
                w = sw * k * (1.0 - 0.45 * i / 3)
                sd.append((math.asin(float(np.clip((ext - w) / ext, -0.99, 0.99))), v))
            sd.append((1.75, s1))
            for s_, poly in ((1, sd), (-1, mirror(sd))):
                vplate(c, f'tasset_{s_}', poly, 3, r=tr, tone=lambda *_: 2, wrap=0.2)
        elif c.dir == 'north':
            v0, hb = belt_back + 0.005, L['hip_bot']
            ct = [(PI - 0.42, v0), (PI + 0.42, v0), (PI + 0.46, (v0 + hb) / 2), (PI + 0.3, hb), (PI - 0.3, hb), (PI - 0.46, (v0 + hb) / 2)]
            vplate(c, 'tasset_b', ct, 3, r=offr(c, [(0.6, 0.5), (0.9, 0.0)]), tone=lambda *_: 3)
            tr = offr(c, low('north'))
            inner = []
            h0, h1 = v0 + 0.1, hb + 0.04
            for i, v in enumerate(np.linspace(h0, h1, 3)):
                ext = form.a(v)[1] * tr(v)
                w = (sw + 1.5) * k * (1.0 - 0.35 * i / 2)
                inner.append((PI - math.asin(float(np.clip((ext - w) / ext, -0.99, 0.99))), v))
            sd = [(PI - 1.75, h0)] + inner + [(PI - 1.75, h1)]
            for s_, poly in ((1, sd), (-1, [(2 * PI - t, v) for t, v in sd][::-1])):
                vplate(c, f'tasset_b{s_}', poly, 3, r=tr, tone=lambda *_: 3, wrap=0.2)
        else:
            tb_ = L['tasset_bot']
            ft = [(-0.1, belt_front + 0.07), (0.78, belt_front + 0.07), (0.7, tb_ - 0.015), (-0.1, tb_)]
            vplate(c, 'tasset_f', ft, 3, r=offr(c, [(v, o + 1.0) for v, o in low('east_front')]), cols=(0.5,),
                   tone=lambda view, th, v: 1 if th < 0.5 else 2)
            t0_, t1_ = belt_back + 0.11, L['tasset_bot'] - 0.035
            tm = (t0_ + t1_) / 2
            th = [(1.5, t0_), (2.7, t0_), (2.75, tm - 0.04), (2.25, tm + 0.06), (1.75, t1_), (1.42, t1_ - 0.045), (1.3, tm - 0.04)]
            vplate(c, 'thigh', th, 3, r=offr(c, low('east_back')), tone=lambda *_: 2)
    if node_ and c.dir == 'south':
        out['node'] = node(c, 'belt_node', 0.0, (front_bot + belt_front) / 2 + 0.01, 4.3 * min(1.4, max(0.8, form.a(0.7)[1] / k / 19.0)), 8.5)
    return out


def d3_marine(c: Ctx) -> None:
    """Marine power armor (spacer): the plain vanilla construction."""
    base_suit(c, c.p.get('fibers', False))
    marine_kit(c)


def d3_recon(c: Ctx) -> None:
    """Recon armor: slimmer shell, a deep V collar instead of the round neck ring."""
    base_suit(c)
    marine_kit(c, shell_add=-2.0, neck='v', chest_w=0.82)


def d3_cataphract(c: Ctx) -> None:
    """Cataphract (ultratech): the marine shell bulked up - raised gorget, broader shoulder
    flanks and a heavier pauldron."""
    base_suit(c, c.p.get('fibers', False))
    marine_kit(c, shell_add=2.0, neck='gorget', chest_w=0.78, pauldron_add=1.5)


def bionic_spine(c: Ctx, top: float, bot: float, z: float = 7.0, glow: bool = True) -> None:
    """Segmented bionic spine down the back: steel vertebra plates over a dark channel, every
    other one with a glowing node.  Seen edge-on as a ridge in the east view."""
    form: TorsoForm = c.form
    k = c.k
    if c.dir == 'south':
        return
    w = 0.22 if c.dir == 'north' else 0.14
    ch = vplate(c, 'spine', band(PI - w, PI + w, top, bot, 6), z, 'accent', r=offr(c, [(0.0, 1.0), (1.0, 1.0)]),
                tone=lambda *_: 1, mask=None, wrap=0.25)
    if ch is None:
        return
    n = max(4, int(round((bot - top) * form.H / (5.2 * k))))
    step = (bot - top) / n
    for i in range(n):
        v0 = top + i * step + step * 0.12
        v1 = v0 + step * 0.7
        seg = vplate(c, f'vertebra{i}', band(PI - w * 0.8, PI + w * 0.8, v0, v1, 6), z + 0.1, 'trim',
                     r=offr(c, [(0.0, 1.8), (1.0, 1.8)]), tone=lambda view, th, v: 1 if view == 'north' else 2, mask=None,
                     wrap=0.25)
        if glow and seg is not None and i % 2 == 1:
            x, y = form.P(c.dir, PI, (v0 + v1) / 2, offr(c, [(0.0, 2.0), (1.0, 2.0)])((v0 + v1) / 2))
            if c.dir == 'north':
                seg.fill(G.ellipse(x, y, 1.1 * k, 0.9 * k), 'energy.base', mask=None)


def d3_bionic(c: Ctx) -> None:
    """Bionic assault suit: the marine construction over an artificial-muscle undersuit (DMS
    bionic suit), with a segmented bionic spine in place of the back plate, a glowing power
    core in the chest, cyan seams along the chest chamfers, a bionic hip node on the belt and
    exposed bionic joint caps on the pauldrons (vanilla bionic-eye palette: light steel, black
    ring, teal lens)."""
    glow = c.p.get('glow', True)
    base_suit(c, True)
    parts = marine_kit(c, spine=False, node_=False, chest_w=0.86)
    L = layout(c)
    v_top = fit_top(c)
    bionic_spine(c, v_top + 0.03, L['back_bot'] + 0.02, glow=glow)
    form: TorsoForm = c.form
    k = c.k
    if c.dir == 'south':
        ch = parts.get('chest')
        if ch is not None and glow:
            fc = 0.86 - 0.24
            for s_ in (1, -1):
                sline(c, ch, [(s_ * (fc + 0.02), 0.44), (s_ * (fc - 0.03), L['front_bot'] - 0.06)], 1.0, 1.0, 'energy.base', mask=None)
        x, y = form.P('south', 0.0, 0.47, 1.02)
        core = c.part('core', G.ellipse(x, y, 4.2 * k, 3.6 * k), 'joint', 8.5, mask=None, shading=[], tone='base')
        core.fill(G.ellipse(x, y - 0.8 * k, 3.0 * k, 2.0 * k), 'light')
        core.fill(G.ellipse(x, y, 2.6 * k, 2.3 * k), 'black')
        core.fill(G.ellipse(x, y, 1.8 * k, 1.6 * k), 'energy.base' if glow else 'lens.base')
        core.fill(G.ellipse(x - 0.6 * k, y - 0.5 * k, 0.6 * k, 0.5 * k), 'energy.light' if glow else 'lens.light')
        node(c, 'belt_node', 0.0, (L['front_bot'] + L['belt_front']) / 2 + 0.01, 4.3 * min(1.4, max(0.8, form.a(0.7)[1] / k / 19.0)),
             8.5, role='joint', glow=glow)
    if c.dir == 'east':
        sjoint(c, 'shoulder_joint', 1.0, 0.36, 3.2, 8.0, r=1.0 + 3.0 * k / max(form.d(0.36)[1], 1.0), glow=glow)


# ----------------------------------------------------------------------------- helmets

# ----------------------------------------------------------------------------- helmet kit
#
# Calibrated on vanilla PowerArmorHelmet / ReconHelmet: the shell is the head silhouette inset
# ~1.5 px (the outline does the rest), big faces are flat (white front, #ccc dome sides, #999-ish
# side and back in the east / north views), seams are single dark lines, and visor openings are
# real HOLES - transparent, framed by the black outline - so the pawn's face shows through.

def htone(view: str, th: float, ph: float) -> int:
    """Vanilla helmet values: south white with #ccc dome flanks; east light front, #ccc band,
    darker side and back; north dark with a lighter crown."""
    if view == 'south':
        return 2 if abs(th) > 1.05 else 1
    if view == 'north':
        return 2 if ph > 1.05 else 3
    return 1 if th < 0.55 else (2 if th < 1.15 else 3)


def hshell(c: Ctx, name: str = 'shell', z: float = 5.0, holes=(), expand: float = -1.4, role: str = 'shell',
           tone: Optional[Callable] = None, cols=(-2.2, -1.15, -1.05, -0.55, 0.55, 1.05, 1.15, 2.2), rows=(1.05,),
           mask='auto') -> Part:
    """Helmet shell on the head form: the head silhouette, flat value cells, and see-through
    ``holes`` given as (theta, phi) polygons (visor openings).  A hole is kept inside the
    silhouette so the outline frames it like vanilla's visor."""
    hf: HeadForm = c.form
    tf = tone or htone
    tones = _tones(c, role)
    outer = c.f.silhouette(expand)
    rings = [outer]
    for h in holes:
        hr = hf.ring(h, 1.0)
        if len(hr) >= 3:
            # the outline frames a hole from the inside: grow it so the opening keeps its size
            rings.append(G.offset(G.simplify_ring(hr, FACET_TOL * c.k * 0.6), 2.4 * c.k))
    cells = []
    tb = [-PI] + list(cols) + [PI]
    fb = [-1.45] + list(rows) + [1.57]
    for i in range(len(tb) - 1):
        for j in range(len(fb) - 1):
            cell = [(tb[i], fb[j]), (tb[i + 1], fb[j]), (tb[i + 1], fb[j + 1]), (tb[i], fb[j + 1])]
            cr = hf.ring(cell, 1.12)
            if len(cr) < 3:
                continue
            idx = int(np.clip(tf(c.dir, (tb[i] + tb[i + 1]) / 2, (fb[j] + fb[j + 1]) / 2), 0, 3))
            cells.append((idx, G.simplify_ring(cr, FACET_TOL * c.k), abs(G.signed_area(cr))))
    areas: dict = {}
    for idx, _, a in cells:
        areas[idx] = areas.get(idx, 0.0) + a
    base = max(areas, key=areas.get) if areas else 1
    p = c.part(name, rings, role, z, shading=[], mask=mask, tone=tones[base])
    for idx, cr, _ in cells:
        if idx != base:
            p.fill(cr, tones[idx])
    return p


def hseam(c: Ctx, p: Part, pts, width: float = 1.3, tone='black', r: float = 1.06, **kw) -> None:
    """Seam line drawn on the helmet surface (visible stretches only)."""
    hf: HeadForm = c.form
    run: list = []
    runs = [run]
    for a, b in zip(pts[:-1], pts[1:]):
        for t in np.linspace(0, 1, 10, endpoint=False):
            th, ph = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            if hf.normal(th, ph)[2] > 0.02:
                run.append(hf.P(th, ph, r))
            elif run:
                run = []
                runs.append(run)
    th, ph = pts[-1]
    if hf.normal(th, ph)[2] > 0.02:
        run.append(hf.P(th, ph, r))
    for rr in runs:
        if len(rr) >= 2:
            p.details.append(Line(G.poly(rr), width * c.k, tone, **kw))


def hplate(c: Ctx, name: str, poly, z: float, role: str = 'shell', r: float = 1.08, tone: Optional[Callable] = None,
           mask='auto', fill: Optional[str] = None) -> Optional[Part]:
    """Raised plate on the helmet (ridge, crest, chin guard) with one flat value."""
    hf: HeadForm = c.form
    ring = hf.ring(poly, r)
    if len(ring) < 3:
        return None
    P = np.asarray(poly, float)
    idx = int(np.clip((tone or htone)(c.dir, float(P[:, 0].mean()), float(P[:, 1].mean())), 0, 3))
    return c.part(name, G.simplify_ring(ring, FACET_TOL * c.k * 0.6), role, z, shading=[], mask=mask,
                  tone=fill or _tones(c, role)[idx])


VISOR_T = [(0.74, 0.08), (0.32, 0.08), (0.22, -0.02), (0.17, -0.16), (-0.17, -0.16), (-0.22, -0.02), (-0.32, 0.08), (-0.74, 0.08),
           (-0.78, -0.08), (-0.62, -0.25), (-0.24, -0.29), (-0.18, -0.56), (0.18, -0.56), (0.24, -0.29), (0.62, -0.25), (0.78, -0.08)]


VISOR_SIDE = [(0.18, 0.08), (0.72, 0.08), (0.78, -0.08), (0.6, -0.26), (0.36, -0.3), (0.3, -0.56), (0.18, -0.56)]


def _front_hole(c: Ctx, poly, side=None):
    """In the east view a front opening is seen from the side: use the ``side`` outline (or
    keep the hole off the front edge) so the outline frames it like vanilla's visor."""
    if c.dir != 'east':
        return poly
    if side is not None:
        return side
    return [(max(t, 0.16), f) for t, f in poly]


def h3_marine(c: Ctx) -> None:
    """Vanilla marine helmet: rounded shell, top slot, brow V crease, see-through T visor."""
    sh = hshell(c, holes=[_front_hole(c, VISOR_T, VISOR_SIDE)])
    hplate(c, 'slot', [(-0.19, 0.98), (0.19, 0.98), (0.17, 1.22), (-0.17, 1.22)], 6, 'undersuit', r=0.99, mask=None, fill='undersuit.base')
    hseam(c, sh, [(0.82, 0.74), (0.0, 0.12), (-0.82, 0.74)])
    hseam(c, sh, [(2.7, 0.9), (1.45, 0.32), (1.15, -0.2)])
    hseam(c, sh, [(-2.7, 0.9), (-1.45, 0.32), (-1.15, -0.2)])
    hseam(c, sh, [(PI - 0.7, 0.78), (PI, 0.86), (PI + 0.7, 0.78)])


def h3_recon(c: Ctx) -> None:
    """Vanilla recon helmet: an open-face frame (cheek guards down the sides), a dark visor bar
    across the eyes, an antenna on one side and an ear module on the other."""
    hf: HeadForm = c.form
    k = c.k
    face = [(0.62, 0.12), (0.4, 0.2), (-0.4, 0.2), (-0.62, 0.12), (-0.66, -0.55), (-0.45, -0.95), (0.45, -0.95), (0.66, -0.55)]
    sh = hshell(c, holes=[_front_hole(c, face)])
    hseam(c, sh, [(0.7, 0.75), (0.25, 0.32)])
    hseam(c, sh, [(-0.7, 0.75), (-0.25, 0.32)])
    hplate(c, 'visor', [(-0.7, 0.02), (0.7, 0.02), (0.68, -0.1), (-0.68, -0.1)], 6, 'accent', r=1.02, mask=None,
           tone=lambda *_: 1)
    for side, kind in ((1, 'antenna'), (-1, 'ear')):
        th = side * 1.5
        if hf.normal(th, 0.0)[2] < -0.3:
            continue
        x, y = hf.P(th, 0.05, 1.08)
        if kind == 'antenna':
            ring = G.rounded(G.rect(x - 2.0 * k, y - 22 * k, x + 2.0 * k, y + 6 * k), 1.6 * k)
        else:
            ring = G.chamfer(G.rect(x - 3.2 * k, y - 4 * k, x + 3.2 * k, y + 9 * k), 1.4 * k)
        c.part(f'recon_{kind}', ring, 'accent', 7 if hf.normal(th, 0.0)[2] > 0 else 2, shading=[], mask=None, tone='base')


def h3_cataphract(c: Ctx) -> None:
    """Cataphract helm (ultratech): fully closed, a T-shaped visor slit, a brow ridge and an
    optional crest."""
    sh = hshell(c, expand=-0.8)
    if c.p.get('crest'):
        hplate(c, 'crest', [(-0.13, 0.35), (0.13, 0.35), (0.13, 1.57), (-0.13, 1.57)], 7.5, 'trim', r=1.24, mask=None)
    hseam(c, sh, [(1.0, 0.42), (0.0, 0.3), (-1.0, 0.42)], 1.4)
    hplate(c, 'slit', [(-0.8, 0.06), (0.8, 0.06), (0.78, -0.07), (0.1, -0.07), (0.09, -0.62), (-0.09, -0.62), (-0.1, -0.07),
                       (-0.78, -0.07)], 6.5, 'lens', r=1.04, mask=None, tone=lambda *_: 1)
    hseam(c, sh, [(2.6, 0.7), (1.4, 0.1), (1.0, -0.5)])
    hseam(c, sh, [(-2.6, 0.7), (-1.4, 0.1), (-1.0, -0.5)])


def h3_bionic(c: Ctx) -> None:
    """Bionic assault helm: the DMS bionic suit's white featureless mask made into armor - closed
    shell, dark sensor band with a cyan trace, ONE bionic eye in the vanilla bionic-eye palette
    (light plate, black ring, teal lens), ear ports, and a neural port that continues the
    bionic spine down the back of the neck."""
    hf: HeadForm = c.form
    k = c.k
    glow = c.p.get('glow', True)
    sh = hshell(c, expand=-1.2)
    hseam(c, sh, [(0.85, 0.7), (0.0, 0.42), (-0.85, 0.7)])
    hseam(c, sh, [(2.6, 0.85), (1.5, 0.35), (1.25, -0.25)])
    hseam(c, sh, [(-2.6, 0.85), (-1.5, 0.35), (-1.25, -0.25)])
    hseam(c, sh, [(0.5, -0.45), (0.0, -0.62), (-0.5, -0.45)], 1.1, 'deep')
    band_ = hplate(c, 'band', [(-1.0, 0.13), (1.0, 0.13), (0.98, -0.11), (-0.98, -0.11)], 6, 'accent', r=1.04, mask=None,
                   tone=lambda *_: 1)
    if band_ is not None and glow:
        pts = [hf.P(t, 0.01, 1.05) for t in np.linspace(-0.9, 0.12, 12) if hf.normal(t, 0.01)[2] > 0.05]
        if len(pts) > 1:
            band_.details.append(Line(G.poly(pts), 1.0 * k, 'energy.base', mask=None))
    th, ph = -0.4, 0.01
    n = hf.normal(th, ph)
    if n[2] > 0.1:
        x, y = hf.P(th, ph, 1.08)
        rx, ry = 4.8 * k * max(0.55, n[2]), 4.6 * k
        e = c.part('eye', G.ellipse(x, y, rx, ry), 'joint', 8, mask=None, shading=[], tone='base')
        e.fill(G.ellipse(x, y - ry * 0.3, rx * 0.8, ry * 0.5), 'light')
        e.fill(G.ellipse(x, y, rx * 0.66, ry * 0.66), 'black')
        e.fill(G.ellipse(x, y, rx * 0.44, ry * 0.44), 'lens.base')
        e.fill(G.ellipse(x - rx * 0.15, y - ry * 0.16, rx * 0.16, ry * 0.16), 'energy.light' if glow else 'lens.light')
    for side in (1, -1):
        th = side * 1.52
        n = hf.normal(th, -0.12)
        if n[2] > 0.12:
            x, y = hf.P(th, -0.12, 1.07)
            jp = c.part(f'earport_{side}', G.ellipse(x, y, 3.2 * k * max(0.5, n[2]), 3.6 * k), 'joint', 7.5, mask=None,
                        shading=[], tone='base')
            jp.fill(G.ellipse(x, y, 1.9 * k * max(0.5, n[2]), 2.1 * k), 'black')
            jp.fill(G.ellipse(x, y, 1.0 * k * max(0.5, n[2]), 1.1 * k), 'energy.base' if glow else 'shade')
    if c.dir in ('north', 'east'):
        port = hplate(c, 'port', [(PI - 0.3, -0.25), (PI + 0.3, -0.25), (PI + 0.26, -1.15), (PI - 0.26, -1.15)], 7, 'accent',
                      r=1.06, mask=None, tone=lambda *_: 1)
        if port is not None:
            for i, ph_ in enumerate((-0.42, -0.66, -0.9)):
                if hf.normal(PI, ph_)[2] > 0.05:
                    x, y = hf.P(PI, ph_, 1.08)
                    port.fill(G.chamfer(G.rect(x - 3.0 * k, y - 1.2 * k, x + 3.0 * k, y + 1.2 * k), 0.6 * k), 'trim.base')
                    if glow and i == 1:
                        port.fill(G.circle(x, y, 0.9 * k), 'energy.base', mask=None)


DESIGNS.update({'marine': d3_marine, 'recon': d3_recon, 'cataphract': d3_cataphract, 'bionic': d3_bionic})
HELMET_DESIGNS.update({'marine': h3_marine, 'recon': h3_recon, 'cataphract': h3_cataphract, 'bionic': h3_bionic})
FORM_DESIGNS = {'marine', 'recon', 'cataphract', 'bionic'}
