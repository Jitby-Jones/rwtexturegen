"""Style-aware shape helpers and decoration motifs shared by all archetypes.

All coordinates are canvas px at the scene size; ``k`` = size / 128 scales motif sizes.
Motif functions return lists of :class:`~rwtex.render.Line` / :class:`~rwtex.render.Fill`
details (attach with ``part.detail(*details)``) unless documented otherwise.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

import numpy as np

from .. import geom as G
from ..render import Bevel, Fill, Gradient, Line, Rim, Split
from ..styles import Style

Pt = Tuple[float, float]


def corner_shape(pts: Sequence[Pt], st: Style, c: Optional[float] = None, corners: Optional[str] = None,
                 seed: int = 0, k: float = 1.0) -> np.ndarray:
    """Turn a polygon into the style's corner language (rounded, chamfered, organic...)."""
    corners = corners or st.corners
    c = st.corner_px * k if c is None else c
    pts = G.poly(pts)
    if corners in ('rounded',):
        r = G.rounded(pts, c)
    elif corners == 'organic':
        r = G.rounded(pts, c * 1.4)
    elif corners in ('chamfered', 'faceted', 'jagged'):
        r = G.chamfer(pts, c)
    else:  # sharp / monolithic
        r = G.rounded(pts, min(c, 0.35 * k))
    irr = float(st.s('irregularity', 0.0))
    if corners == 'organic' or irr >= 0.3:
        r = G.wobble(r, irr * 0.55 * k, 5.0 * k, seed)
    return r


def box(x0: float, y0: float, x1: float, y1: float, st: Style, c: Optional[float] = None,
        corners: Optional[str] = None, seed: int = 0, k: float = 1.0) -> np.ndarray:
    return corner_shape([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], st, c, corners, seed, k)


def std_shading(st: Style, scale: float = 1.0, split: Optional[bool] = None, at: float = 0.55,
                split_tone: str = 'shade') -> list:
    ops: list = [st.bevel(scale)]
    if (st.wants_split() if split is None else split):
        ops.append(Split(at=at, tone=split_tone))
    return ops


# ----------------------------------------------------------------------------- motifs

def vent_slots(x0: float, y0: float, x1: float, y1: float, n: int, k: float = 1.0, vertical: bool = True,
               tone='black', gap: float = 0.45) -> List[Fill]:
    """Row of rounded slot holes inside the box (vanilla charge rifle / DMS vents)."""
    out = []
    if vertical:  # slots are vertical bars arranged left->right
        w = (x1 - x0) / n
        for i in range(n):
            a = x0 + i * w + w * gap / 2
            b = x0 + (i + 1) * w - w * gap / 2
            out.append(Fill([G.rounded(G.rect(a, y0, b, y1), min(b - a, y1 - y0) * 0.35)], tone, mask=None))
    else:
        h = (y1 - y0) / n
        for i in range(n):
            a = y0 + i * h + h * gap / 2
            b = y0 + (i + 1) * h - h * gap / 2
            out.append(Fill([G.rounded(G.rect(x0, a, x1, b), min(x1 - x0, b - a) * 0.35)], tone, mask=None))
    return out


def rivets(points: Sequence[Pt], r: float, tone='deep', glint='light') -> List[Fill]:
    out: List[Fill] = []
    for x, y in points:
        out.append(Fill([G.circle(x, y, r)], tone))
        if glint and r >= 0.8:
            out.append(Fill([G.circle(x - r * 0.3, y - r * 0.3, r * 0.4)], glint))
    return out


def screws(points: Sequence[Pt], r: float, tone='deep') -> list:
    out: list = []
    for x, y in points:
        out.append(Fill([G.circle(x, y, r)], tone))
        out.append(Line(G.poly([(x - r * 0.6, y + r * 0.6), (x + r * 0.6, y - r * 0.6)]), max(0.5, r * 0.45), 'base'))
    return out


def seam(pts: Sequence[Pt], width: float = 1.0, tone='deep') -> Line:
    return Line(G.poly(pts), width, tone)


def diag_bands(x0: float, x1: float, yc: float, h: float, n: int, band: float, slant: float, tone,
               mask='inherit') -> List[Fill]:
    """Diagonal bands across a horizontal bar (lashing / leather wrap)."""
    out = []
    step = (x1 - x0) / n
    for i in range(n):
        cx = x0 + step * (i + 0.5)
        pts = [(cx - band / 2 - slant, yc - h), (cx + band / 2 - slant, yc - h),
               (cx + band / 2 + slant, yc + h), (cx - band / 2 + slant, yc + h)]
        out.append(Fill([G.poly(pts)], tone, mask=mask))
    return out


def wrap_lines(x0: float, x1: float, yc: float, h: float, n: int, width: float, slant: float, tone='deep') -> List[Line]:
    out = []
    step = (x1 - x0) / n
    for i in range(n):
        cx = x0 + step * (i + 0.5)
        out.append(Line(G.poly([(cx - slant, yc - h), (cx + slant, yc + h)]), width, tone))
    return out


def ring_lines(x0: float, x1: float, yc: float, h: float, n: int, width: float, tone='deep') -> List[Line]:
    out = []
    step = (x1 - x0) / (n + 1)
    for i in range(n):
        x = x0 + step * (i + 1)
        out.append(Line(G.poly([(x, yc - h), (x, yc + h)]), width, tone))
    return out


def grain(x0: float, x1: float, yc: float, h: float, n: int, k: float, seed: int = 0, tone='shade') -> List[Line]:
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        y = yc + rng.uniform(-h * 0.6, h * 0.6)
        a = x0 + rng.uniform(0, (x1 - x0) * 0.4)
        b = min(x1, a + rng.uniform((x1 - x0) * 0.3, (x1 - x0) * 0.7))
        pts = [(a, y), ((a + b) / 2, y + rng.uniform(-0.6, 0.6) * k), (b, y + rng.uniform(-0.5, 0.5) * k)]
        out.append(Line(G.poly(pts), 0.8 * k, tone))
    return out


def circuit(x0: float, x1: float, y0: float, y1: float, k: float, seed: int = 0, n: int = 2,
            tone='archo_yellow.base', via_tone='archo_yellow.light', width: float = 1.0) -> list:
    """Archotech traces: right-angle polylines inside a box ending in round vias."""
    rng = np.random.default_rng(seed)
    out: list = []
    lanes = np.linspace(y0 + (y1 - y0) * 0.25, y1 - (y1 - y0) * 0.25, max(1, n))
    for i, y in enumerate(lanes):
        xa = x0 + rng.uniform(0.0, 0.15) * (x1 - x0)
        xb = x1 - rng.uniform(0.05, 0.25) * (x1 - x0)
        pts = [(xa, y)]
        x = xa
        while x < xb - 6 * k:
            x = min(xb, x + rng.uniform(5, 12) * k)
            pts.append((x, pts[-1][1]))
            if rng.random() < 0.6:
                ny = float(np.clip(pts[-1][1] + rng.choice([-1, 1]) * rng.uniform(1.5, 3.5) * k, y0 + 1.5 * k, y1 - 1.5 * k))
                pts.append((x, ny))
        out.append(Line(G.poly(pts), width * k, tone, mask=None))
        out.append(Fill([G.circle(pts[-1][0], pts[-1][1], 1.3 * k)], via_tone, mask=None))
        out.append(Fill([G.circle(pts[0][0], pts[0][1], 1.0 * k)], tone, mask=None))
    return out


def led(x: float, y: float, r: float, tone='led_cyan.base', core='led_cyan.light') -> List[Fill]:
    return [Fill([G.circle(x, y, r)], tone, mask=None), Fill([G.circle(x - r * 0.25, y - r * 0.25, r * 0.45)], core, mask=None)]


def hazard_stripes(x0: float, y0: float, x1: float, y1: float, n: int, k: float,
                   tone_a='hazard_yellow.base', tone_b='black') -> List[Fill]:
    """Yellow/black diagonal stripe block (clip to part)."""
    out = [Fill([G.rect(x0, y0, x1, y1)], tone_a, mask=None)]
    w = (x1 - x0) / n
    h = y1 - y0
    for i in range(0, n + 1, 2):
        a = x0 + i * w
        out.append(Fill([G.poly([(a, y0), (a + w, y0), (a + w - h * 0.7, y1), (a - h * 0.7, y1)])], tone_b, mask=None))
    return out


def chevron(cx: float, cy: float, w: float, h: float, width: float, tone='deep') -> Line:
    return Line(G.poly([(cx - w / 2, cy - h / 2), (cx, cy + h / 2), (cx + w / 2, cy - h / 2)]), width, tone)


def scratches(x0: float, y0: float, x1: float, y1: float, n: int, k: float, seed: int = 0, tone='light') -> List[Line]:
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        x = rng.uniform(x0, x1)
        y = rng.uniform(y0, y1)
        L = rng.uniform(1.5, 3.5) * k
        out.append(Line(G.poly([(x, y), (x + L * 0.7, y - L * 0.7)]), 0.7 * k, tone))
    return out


def knap_facets(x0: float, x1: float, yc: float, h: float, n: int, k: float, seed: int = 0) -> list:
    """Short facet strokes from both edges toward the centre (knapped flint)."""
    rng = np.random.default_rng(seed)
    out: list = []
    xs = np.linspace(x0, x1, n + 2)[1:-1]
    for i, x in enumerate(xs):
        side = -1 if i % 2 == 0 else 1
        y_edge = yc + side * h * 0.48
        y_in = yc + side * h * rng.uniform(0.05, 0.2)
        out.append(Line(G.poly([(x - 1.5 * k, y_edge), (x + 1.0 * k, y_in)]), 0.8 * k, 'shade'))
    return out


def spikes_along(p0: Pt, p1: Pt, n: int, depth: float, side: float, k: float, seed: int = 0) -> np.ndarray:
    return G.zigzag(p0, p1, n, depth, side, jitter=0.45, seed=seed)
