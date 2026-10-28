"""Melee weapon parts.  Vanilla convention: drawn horizontally, pommel left, tip RIGHT.

Blade profiles return a :class:`BladeGeom` describing the outline *and* the top/bottom
edge samples, so facet splits and edge motifs can follow any blade shape.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

from .. import geom as G
from ..render import Bevel, Fill, Glow, Line, Part, Rim, Split
from ..styles import Style
from . import common as C

Pt = Tuple[float, float]


@dataclass
class BladeGeom:
    ring: np.ndarray
    top: np.ndarray      # spine/top edge samples from base to tip start (x increasing)
    bot: np.ndarray      # bottom edge samples from base to tip start (x increasing)
    tip: Pt              # point
    x0: float
    x1: float
    yc: float
    h: float

    def mid_at(self, x: float) -> float:
        xs = np.concatenate([self.top[:, 0], [self.tip[0]]])
        ys_t = np.concatenate([self.top[:, 1], [self.tip[1]]])
        xb = np.concatenate([self.bot[:, 0], [self.tip[0]]])
        ys_b = np.concatenate([self.bot[:, 1], [self.tip[1]]])
        return 0.5 * (np.interp(x, xs, ys_t) + np.interp(x, xb, ys_b))

    def hh_at(self, x: float) -> float:
        yt = np.interp(x, self.top[:, 0], self.top[:, 1])
        yb = np.interp(x, self.bot[:, 0], self.bot[:, 1])
        return 0.5 * (yb - yt)

    def mid_line(self, xa: float, xb: float, n: int = 24, off: float = 0.0) -> np.ndarray:
        xs = np.linspace(xa, xb, n)
        return np.stack([xs, [self.mid_at(x) + off for x in xs]], axis=1)

    def lower_facet(self, frac: float = 0.5) -> np.ndarray:
        """Polygon from the facet line (``frac`` of the way from top to bottom) to the bottom
        edge, through the tip.  frac=0.5 is the centre line."""
        xs = self.top[:, 0]
        ys = []
        for x in xs:
            yt = np.interp(x, self.top[:, 0], self.top[:, 1])
            yb = np.interp(x, self.bot[:, 0], self.bot[:, 1])
            ys.append(yt + (yb - yt) * frac)
        upper = np.stack([xs, ys], axis=1)
        return np.vstack([upper, [self.tip], self.bot[::-1]])


def _body(x0: float, xs: float, top_fn, bot_fn, n: int = 40):
    t = np.linspace(0, 1, n)
    x = x0 + (xs - x0) * t
    top = np.stack([x, [top_fn(v) for v in t]], axis=1)
    bot = np.stack([x, [bot_fn(v) for v in t]], axis=1)
    return top, bot


def _assemble(top: np.ndarray, tip_top: np.ndarray, tip: Pt, tip_bot: np.ndarray, bot: np.ndarray,
              x0, x1, yc, h) -> BladeGeom:
    """tip_top: points from top end to (not incl.) tip; tip_bot: points from tip (excl.) to bottom end."""
    ring = np.vstack([top, tip_top, [tip], tip_bot, bot[::-1]])
    return BladeGeom(ring, top, bot, tip, x0, x1, yc, h)


def blade_geom(profile: str, x0: float, x1: float, yc: float, h: float, k: float = 1.0, *,
               curve: float = 0.0, taper: float = 0.15, flare: float = 2.0, tip_len: Optional[float] = None,
               waves: int = 3, wave_amp: float = 1.2, teeth: int = 6, seed: int = 0,
               notches: Sequence[Tuple[float, float, float]] = ()) -> BladeGeom:
    """Build a blade outline.  ``h`` = blade height at the base.  ``curve`` bends the blade
    upward (+) toward the tip.  ``notches`` = [(t, depth, width)] cut into the spine."""
    hh = h / 2.0
    tl = tip_len if tip_len is not None else h * 1.05
    L = x1 - x0

    def bend(t):
        return -curve * t * t

    if profile == 'flared':  # vanilla monosword
        fl = flare * k
        xf = x1 - 12.5 * k
        top = np.array([[x0, yc - hh], [xf, yc - hh], [xf, yc - hh - fl], [xf + 3 * k, yc - hh - fl]])
        bot = np.array([[x0, yc + hh], [xf, yc + hh], [xf, yc + hh + fl], [xf + 3 * k, yc + hh + fl]])
        qt = G.qbezier((xf + 3 * k, yc - hh - fl), (x1 - 3.5 * k, yc - hh - fl + 1.5 * k), (x1, yc))
        qb = G.qbezier((x1, yc), (x1 - 3.5 * k, yc + hh + fl - 1.5 * k), (xf + 3 * k, yc + hh + fl))
        return _assemble(top, qt[1:-1], (x1, yc), qb[1:-1], bot, x0, x1, yc, h)

    if profile in ('straight', 'leaf', 'wavy', 'serrated'):
        xs = x1 - tl

        def half(t):
            v = hh * (1 - taper * t)
            if profile == 'leaf':
                v = hh * (1 + 0.3 * math.sin(math.pi * min(1, t * 1.05)) - 0.15 * t)
            if profile == 'wavy':
                v = hh * (1 - taper * t)
            return v

        def wv(t):
            return wave_amp * k * math.sin(2 * math.pi * waves * t) if profile == 'wavy' else 0.0

        top, bot = _body(x0, xs, lambda t: yc + bend(t) - half(t) + wv(t), lambda t: yc + bend(t) + half(t) + wv(t))
        ye = yc + bend(1.0)
        tip = (x1, ye + bend(1.0) * 0.2)
        he = half(1.0)
        qt = G.qbezier((xs, ye - he), (x1 - tl * 0.35, ye - he * 0.7), tip)
        qb = G.qbezier(tip, (x1 - tl * 0.35, ye + he * 0.7), (xs, ye + he))
        if profile == 'serrated':
            n_t = max(3, teeth)
            xa, xb = x0 + L * 0.08, x0 + L * 0.45
            zz = G.zigzag((xa, yc - hh), (xb, yc - hh * (1 - taper * 0.45)), n_t, 2.2 * k, side=1.0)
            pre = top[top[:, 0] < xa]
            post = top[top[:, 0] > xb]
            top = np.vstack([pre, zz, post])
        return _assemble(top, qt[1:-1], tip, qb[1:-1], bot, x0, x1, yc, h)

    if profile == 'tanto':
        xs = x1 - tl * 0.9
        top, bot = _body(x0, xs, lambda t: yc + bend(t) - hh * (1 - taper * 0.3 * t), lambda t: yc + bend(t) + hh)
        tip = (x1, yc + bend(1) + hh * 0.35)
        tip_top = np.array([[xs + tl * 0.15, yc + bend(1) - hh * 0.95]])
        tip_bot = np.array([[x1 - tl * 0.25, yc + bend(1) + hh * 0.98]])
        return _assemble(top, tip_top, tip, tip_bot, bot, x0, x1, yc, h)

    if profile == 'clip':  # bowie / machete
        xs = x1 - tl * 1.2
        belly = 0.12

        top, bot = _body(x0, xs, lambda t: yc - hh, lambda t: yc + hh * (1 + belly * t))
        tip = (x1, yc - hh * 0.25)
        qt = G.qbezier((xs, yc - hh), (x1 - tl * 0.55, yc - hh * 0.55), tip)
        qb = G.qbezier(tip, (x1 - tl * 0.1, yc + hh * 1.1), (xs, yc + hh * (1 + belly)))
        return _assemble(top, qt[1:-1], tip, qb[1:-1], bot, x0, x1, yc, h)

    if profile == 'curved':  # scimitar / plasmasword
        c = curve if curve else 5.0 * k
        xs = x1 - tl * 0.8

        def bnd(t):
            return -c * t * t
        top, bot = _body(x0, xs, lambda t: yc + bnd(t) - hh * (1 - 0.1 * t), lambda t: yc + bnd(t) + hh * (1 + 0.5 * t ** 1.4))
        ye = yc + bnd(1.0)
        tip = (x1, ye - hh * 0.55)
        tip_top = np.array([[xs + tl * 0.05, ye - hh * 0.95]])
        qb = G.qbezier(tip, (x1 - tl * 0.05, ye + hh * 1.2), (xs, ye + hh * 1.5))
        return _assemble(top, tip_top, tip, qb[1:-1], bot, x0, x1, yc, h)

    if profile == 'cleaver':
        xs = x1 - 2.5 * k
        top, bot = _body(x0, xs, lambda t: yc - hh, lambda t: yc + hh * (1 + 0.45 * t))
        tip = (x1, yc - hh * 0.2)
        tip_top = np.array([[x1 - 0.5 * k, yc - hh]])
        tip_bot = np.array([[x1 - 1.5 * k, yc + hh * 1.45]])
        return _assemble(top, tip_top, tip, tip_bot, bot, x0, x1, yc, h)

    if profile == 'knapped':
        xs = x1 - tl * 0.9
        top, bot = _body(x0, xs, lambda t: yc - hh * (1 + 0.25 * math.sin(math.pi * t)), lambda t: yc + hh * (1 + 0.25 * math.sin(math.pi * t)), n=12)
        top = G.zigzag(tuple(top[0]), tuple(top[-1]), 7, 1.6 * k, side=1.0, jitter=0.6, seed=seed)
        top[:, 1] += np.interp(top[:, 0], [x0, (x0 + xs) / 2, xs], [0, -hh * 0.25, 0])
        bot = G.zigzag(tuple(bot[0]), tuple(bot[-1]), 7, 1.6 * k, side=-1.0, jitter=0.6, seed=seed + 1)
        bot[:, 1] += np.interp(bot[:, 0], [x0, (x0 + xs) / 2, xs], [0, hh * 0.25, 0])
        tip = (x1, yc + 0.5 * k)
        return _assemble(top, np.zeros((0, 2)), tip, np.zeros((0, 2)), bot, x0, x1, yc, h)

    if profile == 'stepped':  # archotech
        segs = [1.0, 1.12, 0.94, 1.06]
        xs = x1 - tl * 0.9
        edges = np.linspace(x0, xs, len(segs) + 1)
        top_pts, bot_pts = [], []
        for i, s in enumerate(segs):
            top_pts += [(edges[i], yc - hh * s), (edges[i + 1], yc - hh * s)]
            bot_pts += [(edges[i], yc + hh * s), (edges[i + 1], yc + hh * s)]
        top, bot = np.array(top_pts), np.array(bot_pts)
        st = (xs + x1) / 2
        tip_top = np.array([[xs, yc - hh * 0.62], [st, yc - hh * 0.62], [st, yc - hh * 0.3]])
        tip_bot = np.array([[st, yc + hh * 0.3], [st, yc + hh * 0.62], [xs, yc + hh * 0.62]])
        tip = (x1, yc)
        ring = np.vstack([top, tip_top, [[x1, yc - hh * 0.3]], [tip], [[x1, yc + hh * 0.3]], tip_bot, bot[::-1]])
        return BladeGeom(ring, top, bot, tip, x0, x1, yc, h)

    if profile == 'jagged':  # anomaly
        xs = x1 - tl
        top = G.zigzag((x0, yc - hh), (xs, yc - hh * 0.8), max(3, teeth - 1), 3.0 * k, side=1.0, jitter=0.7, seed=seed)
        bot = G.zigzag((x0, yc + hh), (xs, yc + hh * 0.9), 3, 2.0 * k, side=-1.0, jitter=0.7, seed=seed + 7)
        tip = (x1, yc - hh * 1.1)
        tip_top = np.array([[xs + tl * 0.4, yc - hh * 0.6]])
        tip_bot = G.qbezier(tip, (x1 - tl * 0.15, yc + hh * 0.9), (xs, yc + hh * 0.9))[1:-1]
        return _assemble(top, tip_top, tip, tip_bot, bot, x0, x1, yc, h)

    if profile == 'scythe':  # mechanoid
        top = G.qbezier((x0, yc - hh), (x0 + L * 0.65, yc - hh * 1.9 - curve), (x1, yc + hh * 0.6))
        bot = G.qbezier((x0, yc + hh), (x0 + L * 0.55, yc - hh * 0.2 - curve * 0.5), (x1 - 3 * k, yc + hh * 0.9))
        tip = (x1 + 1 * k, yc + hh * 1.2)
        ring = np.vstack([top, [tip], bot[::-1]])
        return BladeGeom(ring, top, bot, tip, x0, x1, yc, h)

    raise ValueError(f'unknown blade profile {profile!r}')


def apply_notches(bg: BladeGeom, notches: Sequence[Tuple[float, float, float]], k: float) -> BladeGeom:
    """Cut rectangular notches into the spine: [(t, depth_px, width_px)]."""
    if not notches:
        return bg
    top = bg.top.copy()
    pts = [tuple(p) for p in top]
    for t, depth, width in notches:
        xc = bg.x0 + (bg.top[-1, 0] - bg.x0) * t
        xa, xb = xc - width * k / 2, xc + width * k / 2
        ya = float(np.interp(xa, top[:, 0], top[:, 1]))
        yb = float(np.interp(xb, top[:, 0], top[:, 1]))
        new = [p for p in pts if p[0] < xa] + [(xa, ya), (xa + 0.6 * k, ya + depth * k), (xb, yb + depth * k * 0.2), (xb, yb)] + [p for p in pts if p[0] > xb]
        pts = new
    top2 = np.array(pts)
    tip_part = bg.ring[len(bg.top):len(bg.ring) - len(bg.bot)]
    ring = np.vstack([top2, tip_part, bg.bot[::-1]])
    return BladeGeom(ring, top2, bg.bot, bg.tip, bg.x0, bg.x1, bg.yc, bg.h)


def blade_part(bg: BladeGeom, mat, st: Style, k: float, *, white: bool = True, facet: float = 0.5,
               rim: bool = True, name: str = 'blade', z: float = 3) -> Part:
    """Blade with vanilla-style shading: grey 1px rims, lower facet, facet line."""
    p = Part(name, bg.ring, mat, z=z)
    if white:
        if rim:
            p.shade(Bevel(1.0 * k, 1.0 * k, light_tone='#aaaaaa', shade_tone='deep', angle=-90))
        p.fill(bg.lower_facet(facet), 'shade')
        p.line(bg.mid_line(bg.x0, bg.tip[0] - 1.5 * k, off=(facet - 0.5) * 0), 1.0 * k, 'line')
        if rim:
            # re-apply the bottom rim over the facet fill
            p.shade(Bevel(0.0, 1.0 * k, shade_tone='deep', angle=-90))
    else:
        p.shade(st.bevel(k))
        p.fill(bg.lower_facet(facet), 'shade')
        p.shade(Bevel(0.0, 1.2 * k, shade_tone='deep', angle=-90))
    return p


# ----------------------------------------------------------------------------- guards

def guard_part(kind: str, gx: float, yc: float, w: float, h: float, mat, st: Style, k: float,
               seed: int = 0, name: str = 'guard', z: float = 4) -> List[Part]:
    """Crossguard family, centred on x=gx (blade side to the right)."""
    hw, hh = w / 2, h / 2
    parts: List[Part] = []
    if kind == 'none':
        return parts
    if kind == 'block':
        r = C.box(gx - hw, yc - hh, gx + hw, yc + hh, st, c=min(1.5 * k, st.corner_px * k * 0.5), k=k, seed=seed)
        p = Part(name, r, mat, z=z).shade(Bevel(1.2 * k, 1.2 * k, light_tone='deep', shade_tone='deep', angle=-90),
                                           Split(at=0.62, tone='shade'))
        parts.append(p)
    elif kind == 'cross':
        r = G.Path().move(gx - hw, yc - hh + w * 0.6).quad(gx - hw, yc - hh - 0.6 * k, gx, yc - hh - 0.6 * k) \
            .quad(gx + hw, yc - hh - 0.6 * k, gx + hw, yc - hh + w * 0.6).line(gx + hw * 0.7, yc) \
            .line(gx + hw, yc + hh - w * 0.6).quad(gx + hw, yc + hh + 0.6 * k, gx, yc + hh + 0.6 * k) \
            .quad(gx - hw, yc + hh + 0.6 * k, gx - hw, yc + hh - w * 0.6).line(gx - hw * 0.7, yc).close().ring
        parts.append(Part(name, r, mat, z=z).shade(st.bevel(k * 0.8)))
    elif kind == 'crescent':
        outer = G.arc_pts(gx + hh * 0.55, yc, hh * 0.95, hh, 120, 240)
        inner = G.arc_pts(gx + hh * 0.85, yc, hh * 0.8, hh * 0.7, 235, 125)
        r = np.vstack([outer, inner])
        parts.append(Part(name, r, mat, z=z).shade(st.bevel(k)))
    elif kind == 'ring':
        ro = G.circle(gx, yc, hh)
        ri = G.circle(gx, yc, hh - w * 0.75)
        parts.append(Part(name, [ro, ri], mat, z=z).shade(st.bevel(k), Split(at=0.6, tone='shade')))
    elif kind == 'disc':
        r = G.ellipse(gx, yc, hw, hh)
        parts.append(Part(name, r, mat, z=z).shade(st.bevel(k), Split(at=0.6, tone='shade')))
    elif kind == 'wing':  # imperial: swept wings toward the tip
        up = G.Path().move(gx - hw, yc - 2 * k).line(gx - hw, yc - hh * 0.55).cubic(gx - hw, yc - hh * 1.05, gx + hw * 2.5, yc - hh * 1.25, gx + hw * 3.2, yc - hh * 0.9) \
            .cubic(gx + hw * 1.6, yc - hh * 0.75, gx + hw, yc - hh * 0.45, gx + hw, yc - 2 * k).close().ring
        dn = G.mirror_y(up, yc)
        parts.append(Part(name + '_up', up, mat, z=z).shade(st.bevel(k), Split(at=0.6, tone='shade')))
        parts.append(Part(name + '_dn', dn, mat, z=z).shade(st.bevel(k), Split(at=0.6, tone='shade')))
        core = G.rounded(G.rect(gx - hw * 0.9, yc - hh * 0.35, gx + hw * 0.9, yc + hh * 0.35), 1.2 * k)
        parts.append(Part(name, core, mat, z=z + 0.1).shade(st.bevel(k)))
    elif kind == 'claw':  # anomaly: hooked barbs
        up = G.Path().move(gx - hw, yc - 1 * k).line(gx - hw * 0.6, yc - hh * 0.8).quad(gx + hw * 0.5, yc - hh * 1.25, gx + hw * 2.4, yc - hh * 1.1) \
            .quad(gx + hw * 0.6, yc - hh * 0.75, gx + hw, yc - 1 * k).close().ring
        dn = G.mirror_y(G.scale(up, 1.0, 0.8, gx, yc), yc)
        parts += [Part(name + '_up', up, mat, z=z).shade(st.bevel(k)), Part(name + '_dn', dn, mat, z=z).shade(st.bevel(k))]
    elif kind == 'nested':  # archotech stacked blocks
        a = G.rect(gx - hw, yc - hh, gx + hw * 0.2, yc + hh)
        b = G.rect(gx - hw * 0.2, yc - hh * 0.72, gx + hw, yc + hh * 0.72)
        parts.append(Part(name, a, mat, z=z).shade(Bevel(1 * k, 1 * k)))
        parts.append(Part(name + '_b', b, 'archo_olive', z=z + 0.1).shade(Bevel(1 * k, 1 * k)))
    elif kind == 'carapace':  # mechanoid kite plate
        r = G.chamfer([(gx - hw, yc - hh * 0.75), (gx + hw * 0.4, yc - hh), (gx + hw, yc - hh * 0.2), (gx + hw, yc + hh * 0.2),
                       (gx + hw * 0.4, yc + hh), (gx - hw, yc + hh * 0.75)], 1.5 * k)
        p = Part(name, r, mat, z=z).shade(st.bevel(k), Split(at=0.5, tone='shade'))
        p.line([(gx - hw * 0.6, yc), (gx + hw * 0.7, yc)], 1.0 * k, 'deep')
        parts.append(p)
    elif kind == 'finger':  # industrial: small lug under the grip side
        r = C.box(gx - hw, yc - hh * 0.55, gx + hw, yc + hh * 0.55, st, k=k)
        lug = G.rounded([(gx - hw, yc + hh * 0.3), (gx + hw, yc + hh * 0.3), (gx + hw * 0.4, yc + hh * 1.05), (gx - hw * 1.3, yc + hh * 1.0)], 1.2 * k)
        parts.append(Part(name + '_lug', lug, mat, z=z - 0.1).shade(st.bevel(k)))
        parts.append(Part(name, r, mat, z=z).shade(st.bevel(k)))
    else:
        raise ValueError(f'unknown guard {kind!r}')
    return parts


# ----------------------------------------------------------------------------- grips & pommels

def grip_part(kind: str, x0: float, x1: float, yc: float, h: float, mat, st: Style, k: float,
              seed: int = 0, wrap_mat: Optional[str] = None, name: str = 'grip', z: float = 1) -> Part:
    hh = h / 2
    if kind == 'twisted':
        r = G.Path().move(x0, yc - hh).cubic(x0 + (x1 - x0) * 0.3, yc - hh * 1.5, x0 + (x1 - x0) * 0.6, yc - hh * 0.5, x1, yc - hh) \
            .line(x1, yc + hh).cubic(x0 + (x1 - x0) * 0.6, yc + hh * 1.4, x0 + (x1 - x0) * 0.3, yc + hh * 0.4, x0, yc + hh).close().ring
    else:
        r = C.box(x0, yc - hh, x1, yc + hh, st, c=min(st.corner_px * k, hh * 0.6), k=k, seed=seed)
    p = Part(name, r, mat, z=z)
    p.shade(Bevel(1.0 * k, 1.2 * k, light_tone='deep', shade_tone='shade', angle=-90))
    L = x1 - x0
    if kind == 'wrapped':
        tone = f'{wrap_mat}.light' if wrap_mat else 'light'
        p.detail(*C.wrap_lines(x0 + 1 * k, x1 - 1 * k, yc, hh, max(3, int(L / (4.5 * k))), 1.0 * k, hh * 0.55, tone=tone))
    elif kind == 'segmented':
        p.detail(*C.ring_lines(x0, x1, yc, hh, max(2, int(L / (5 * k))), 1.0 * k, 'deep'))
    elif kind == 'lashed':
        band = f'{wrap_mat or "sinew"}.base'
        p.detail(*C.diag_bands(x0 + 2 * k, x1 - 2 * k, yc, hh, max(3, int(L / (6 * k))), 2.4 * k, 1.2 * k, band))
        p.detail(*C.grain(x0, x1, yc, hh, 2, k, seed))
    elif kind == 'ribbed':
        p.detail(*C.ring_lines(x0, x1, yc, hh * 0.8, max(3, int(L / (3.5 * k))), 1.2 * k, 'light'))
    elif kind == 'riveted':
        p.detail(*C.rivets([(x0 + L * 0.25, yc), (x0 + L * 0.6, yc)], 1.1 * k, 'steel_bright.base', 'steel_bright.light'))
    elif kind == 'frame':
        p.detail(Fill([G.rect(x0 + L * 0.15, yc - hh * 0.35, x1 - L * 0.15, yc + hh * 0.35)], 'archo_olive.shade'))
        p.detail(*C.led(x0 + L * 0.5, yc, 1.3 * k, 'archo_yellow.base', 'archo_yellow.light'))
    elif kind == 'twisted':
        for i in range(4):
            xa = x0 + L * (0.1 + i * 0.22)
            p.line([(xa, yc - hh), (xa + L * 0.12, yc + hh)], 1.0 * k, 'shade')
    return p


def pommel_part(kind: str, x: float, yc: float, s: float, mat, st: Style, k: float, seed: int = 0,
                name: str = 'pommel', z: float = 2) -> Optional[Part]:
    """Pommel whose right edge sits at ``x`` (it overlaps the grip end); ``s`` = size."""
    if kind == 'none':
        return None
    if kind == 'round':
        r = G.circle(x - s * 0.35, yc, s / 2)
    elif kind == 'disc':
        r = G.ellipse(x - s * 0.25, yc, s * 0.32, s * 0.62)
    elif kind == 'diamond':
        r = G.rounded([(x - s * 1.05, yc), (x - s * 0.35, yc - s * 0.55), (x + s * 0.1, yc), (x - s * 0.35, yc + s * 0.55)], 0.8 * k)
    elif kind == 'fishtail':
        r = G.rounded([(x, yc - s * 0.3), (x - s * 0.6, yc - s * 0.32), (x - s * 1.0, yc - s * 0.62), (x - s * 0.8, yc), (x - s * 1.0, yc + s * 0.62),
                       (x - s * 0.6, yc + s * 0.32), (x, yc + s * 0.3)], 0.7 * k)
    elif kind == 'cap':
        r = C.box(x - s * 0.55, yc - s * 0.42, x + s * 0.1, yc + s * 0.42, st, c=min(st.corner_px * k, s * 0.2), k=k)
    elif kind == 'ring':
        r = [G.circle(x - s * 0.4, yc, s * 0.5), G.circle(x - s * 0.4, yc, s * 0.24)]
    elif kind == 'spike':
        r = G.rounded([(x, yc - s * 0.38), (x - s * 0.4, yc - s * 0.3), (x - s * 1.25, yc), (x - s * 0.4, yc + s * 0.3), (x, yc + s * 0.38)], 0.5 * k)
    elif kind == 'knob':
        r = G.wobble(G.circle(x - s * 0.3, yc, s * 0.55), 0.6 * k, 4 * k, seed)
    elif kind == 'cube':
        r = G.rect(x - s * 0.75, yc - s * 0.45, x + s * 0.05, yc + s * 0.45)
    else:
        raise ValueError(f'unknown pommel {kind!r}')
    p = Part(name, r, mat, z=z)
    p.shade(st.bevel(k), Split(at=0.62, tone='shade'))
    return p


# ----------------------------------------------------------------------------- edge motifs

def edge_motif(kind: str, bg: BladeGeom, k: float, mat='mono_edge', t0: float = 0.06, t1: float = 0.55,
               width: float = 4.0, offset: float = 0.0, seed: int = 0) -> List:
    """Emissive / decorative details along the blade centre line (persona & ultratech)."""
    xa = bg.x0 + (bg.tip[0] - bg.x0) * t0
    xb = bg.x0 + (bg.tip[0] - bg.x0) * t1
    w = width * k
    m = mat
    out: List = []
    if kind == 'none':
        return out
    y = lambda x: bg.mid_at(x) + offset * k  # noqa: E731
    if kind == 'line':  # vanilla monosword: bulb + line
        bx = xa + w * 0.8
        out.append(Line(bg.mid_line(bx, xb, off=offset * k), w, f'{m}.base', mask=None))
        out.append(Fill([G.circle(bx, y(bx), w * 0.78)], f'{m}.shade', mask=None))
        out.append(Fill([G.circle(bx - w * 0.45, y(bx) - w * 0.2, w * 0.24)], f'{m}.light', mask=None))
    elif kind == 'dashes':
        n = 4
        seg = (xb - xa) / n
        for i in range(n):
            a = xa + i * seg
            out.append(Line(bg.mid_line(a, a + seg * 0.6, 6, off=offset * k), w * 0.8, f'{m}.base', mask=None))
    elif kind == 'dots':
        for x in np.linspace(xa, xb, 6):
            out.append(Fill([G.circle(x, y(x), w * 0.42)], f'{m}.base', mask=None))
    elif kind == 'double':
        for o in (-w * 0.55, w * 0.55):
            out.append(Line(bg.mid_line(xa, xb, off=offset * k + o), w * 0.4, f'{m}.base', mask=None))
        out.append(Fill([G.circle(xa, y(xa), w * 0.6)], f'{m}.shade', mask=None))
    elif kind == 'wedge':
        out.append(Fill([G.poly([(xa, y(xa) - w * 0.7), (xb, y(xb)), (xa, y(xa) + w * 0.7)])], f'{m}.base', mask=None))
    elif kind == 'ring':
        out.append(Fill([G.circle(xa + w, y(xa + w), w * 0.95), G.circle(xa + w, y(xa + w), w * 0.5)], f'{m}.base', mask=None))
        out.append(Line(bg.mid_line(xa + w * 2.2, xb, off=offset * k), w * 0.5, f'{m}.base', mask=None))
    elif kind == 'split':  # line that forks into two branches ending in nodes (new variant motif)
        xm = xa + (xb - xa) * 0.42
        out.append(Line(bg.mid_line(xa + w, xm, off=offset * k), w * 0.75, f'{m}.base', mask=None))
        out.append(Fill([G.circle(xa + w * 0.6, y(xa + w * 0.6), w * 0.7)], f'{m}.shade', mask=None))
        for sgn in (-1, 1):
            br = [(xm, y(xm)), (xm + w * 1.2, y(xm) + sgn * w * 0.9), (xb, y(xb) + sgn * w * 0.9)]
            out.append(Line(G.poly(br), w * 0.45, f'{m}.base', mask=None))
            out.append(Fill([G.circle(xb, y(xb) + sgn * w * 0.9, w * 0.42)], f'{m}.light', mask=None))
    elif kind == 'circuit':
        hh = bg.hh_at((xa + xb) / 2)
        out += C.circuit(xa, xb, y(xa) - hh * 0.55, y(xa) + hh * 0.55, k, seed=seed, n=2)
    elif kind == 'conduit':
        out.append(Line(bg.mid_line(xa, xb, off=offset * k), w * 0.55, 'mech_conduit.base', mask=None))
        out.append(Line(bg.mid_line(xa, xb, off=offset * k - w * 0.12), w * 0.2, 'mech_conduit.light', mask=None))
    elif kind == 'ichor':
        pts = bg.mid_line(xa, xb, 9, off=offset * k)
        rng = np.random.default_rng(seed)
        pts[1:-1, 1] += rng.uniform(-1, 1, len(pts) - 2) * w * 0.35
        out.append(Line(pts, w * 0.45, f'{m}.base', mask=None))
    elif kind == 'fuller':
        out.append(Line(bg.mid_line(xa, xb, off=offset * k), w * 0.5, 'shade'))
        out.append(Line(bg.mid_line(xa, xb, off=offset * k - w * 0.25), w * 0.2, 'deep'))
    else:
        raise ValueError(f'unknown edge motif {kind!r}')
    return out
