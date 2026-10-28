"""Vector geometry toolkit.

Everything is expressed in *canvas pixels of the final texture* (e.g. 0..128), y pointing
down like image coordinates.  Shapes are lists of closed rings (``numpy`` arrays of shape
(N, 2)).  Curves are flattened on creation at sub-pixel resolution so the rasteriser and
the SVG exporter see the same geometry.
"""
from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple, Union

import numpy as np

Ring = np.ndarray
Pt = Tuple[float, float]
Num = Union[int, float]

# flattening resolution: max segment length in canvas px for arcs/curves
FLAT = 0.6


def P(*pts: Pt) -> Ring:
    return np.asarray(pts, dtype=np.float64).reshape(-1, 2)


def poly(pts: Iterable[Pt]) -> Ring:
    return np.asarray(list(pts), dtype=np.float64).reshape(-1, 2)


def rect(x0: Num, y0: Num, x1: Num, y1: Num) -> Ring:
    return P((x0, y0), (x1, y0), (x1, y1), (x0, y1))


def _arc_n(r: float, sweep: float) -> int:
    return max(2, int(math.ceil(abs(sweep) * max(r, 0.5) / FLAT)))


def arc_pts(cx: Num, cy: Num, rx: Num, ry: Num, a0: float, a1: float, n: int | None = None) -> Ring:
    """Points along an elliptical arc, angles in degrees (0 = +x, 90 = +y/down)."""
    t0, t1 = math.radians(a0), math.radians(a1)
    if n is None:
        n = _arc_n(max(rx, ry), t1 - t0)
    t = np.linspace(t0, t1, n + 1)
    return np.stack([cx + rx * np.cos(t), cy + ry * np.sin(t)], axis=1)


def ellipse(cx: Num, cy: Num, rx: Num, ry: Num | None = None) -> Ring:
    ry = rx if ry is None else ry
    pts = arc_pts(cx, cy, rx, ry, 0, 360)
    return pts[:-1]


def circle(cx: Num, cy: Num, r: Num) -> Ring:
    return ellipse(cx, cy, r, r)


def capsule(x0: Num, y0: Num, x1: Num, y1: Num, r: Num) -> Ring:
    """Stadium shape around the segment (x0,y0)-(x1,y1)."""
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    a = arc_pts(x1, y1, r, r, ang - 90, ang + 90)
    b = arc_pts(x0, y0, r, r, ang + 90, ang + 270)
    return np.vstack([a, b])


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.hypot(v[0], v[1])
    return v / n if n > 1e-9 else v * 0


def rounded(pts: Iterable[Pt] | Ring, r: Union[Num, Sequence[Num]]) -> Ring:
    """Polygon with rounded corners. ``r`` may be a scalar or one radius per vertex."""
    pts = poly(pts) if not isinstance(pts, np.ndarray) else pts
    n = len(pts)
    rs = [r] * n if np.isscalar(r) else list(r)
    out: List[np.ndarray] = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        ri = float(rs[i])
        u, v = _unit(p0 - p1), _unit(p2 - p1)
        cosang = float(np.clip(np.dot(u, v), -1.0, 1.0))
        theta = math.acos(cosang)
        if ri <= 0 or theta < 1e-3 or abs(theta - math.pi) < 1e-3:
            out.append(p1[None, :])
            continue
        t = ri / math.tan(theta / 2)
        lim = 0.5 * min(np.hypot(*(p0 - p1)), np.hypot(*(p2 - p1)))
        if t > lim:
            t = lim
            ri = t * math.tan(theta / 2)
        a = p1 + u * t
        b = p1 + v * t
        bis = _unit(u + v)
        c = p1 + bis * (ri / math.sin(theta / 2))
        a0 = math.atan2(a[1] - c[1], a[0] - c[0])
        a1 = math.atan2(b[1] - c[1], b[0] - c[0])
        d = a1 - a0
        while d > math.pi:
            d -= 2 * math.pi
        while d < -math.pi:
            d += 2 * math.pi
        k = max(2, int(math.ceil(abs(d) * ri / FLAT)))
        ts = np.linspace(a0, a0 + d, k + 1)
        out.append(np.stack([c[0] + ri * np.cos(ts), c[1] + ri * np.sin(ts)], axis=1))
    return np.vstack(out)


def chamfer(pts: Iterable[Pt] | Ring, c: Union[Num, Sequence[Num]]) -> Ring:
    """Polygon with 45-degree style corner cuts of length ``c`` (scalar or per vertex)."""
    pts = poly(pts) if not isinstance(pts, np.ndarray) else pts
    n = len(pts)
    cs = [c] * n if np.isscalar(c) else list(c)
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        ci = float(cs[i])
        if ci <= 0:
            out.append(p1)
            continue
        l0, l2 = np.hypot(*(p0 - p1)), np.hypot(*(p2 - p1))
        ci = min(ci, 0.5 * l0, 0.5 * l2)
        out.append(p1 + _unit(p0 - p1) * ci)
        out.append(p1 + _unit(p2 - p1) * ci)
    return np.asarray(out)


def bezier(p0: Pt, p1: Pt, p2: Pt, p3: Pt, n: int | None = None) -> Ring:
    p = np.asarray([p0, p1, p2, p3], dtype=np.float64)
    if n is None:
        L = sum(np.hypot(*(p[i + 1] - p[i])) for i in range(3))
        n = max(2, int(math.ceil(L / FLAT)))
    t = np.linspace(0, 1, n + 1)[:, None]
    return ((1 - t) ** 3) * p[0] + 3 * ((1 - t) ** 2) * t * p[1] + 3 * (1 - t) * t ** 2 * p[2] + t ** 3 * p[3]


def qbezier(p0: Pt, p1: Pt, p2: Pt, n: int | None = None) -> Ring:
    p = np.asarray([p0, p1, p2], dtype=np.float64)
    if n is None:
        L = np.hypot(*(p[1] - p[0])) + np.hypot(*(p[2] - p[1]))
        n = max(2, int(math.ceil(L / FLAT)))
    t = np.linspace(0, 1, n + 1)[:, None]
    return ((1 - t) ** 2) * p[0] + 2 * (1 - t) * t * p[1] + t ** 2 * p[2]


def spline(pts: Iterable[Pt], closed: bool = True, alpha: float = 0.5) -> Ring:
    """Centripetal Catmull-Rom spline through the points."""
    pts = poly(pts)
    n = len(pts)
    if n < 3:
        return pts
    if closed:
        ext = np.vstack([pts[-1:], pts, pts[:2]])
        segs = n
    else:
        ext = np.vstack([pts[:1] * 2 - pts[1:2], pts, pts[-1:] * 2 - pts[-2:-1]])
        segs = n - 1
    out = []
    for i in range(segs):
        p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]

        def tj(ti, a, b):
            return ti + max(np.hypot(*(b - a)), 1e-6) ** alpha
        t0 = 0.0
        t1 = tj(t0, p0, p1)
        t2 = tj(t1, p1, p2)
        t3 = tj(t2, p2, p3)
        k = max(2, int(math.ceil(np.hypot(*(p2 - p1)) / FLAT)))
        ts = np.linspace(t1, t2, k, endpoint=False)[:, None]
        a1 = (t1 - ts) / (t1 - t0) * p0 + (ts - t0) / (t1 - t0) * p1
        a2 = (t2 - ts) / (t2 - t1) * p1 + (ts - t1) / (t2 - t1) * p2
        a3 = (t3 - ts) / (t3 - t2) * p2 + (ts - t2) / (t3 - t2) * p3
        b1 = (t2 - ts) / (t2 - t0) * a1 + (ts - t0) / (t2 - t0) * a2
        b2 = (t3 - ts) / (t3 - t1) * a2 + (ts - t1) / (t3 - t1) * a3
        c = (t2 - ts) / (t2 - t1) * b1 + (ts - t1) / (t2 - t1) * b2
        out.append(c)
    if not closed:
        out.append(pts[-1:])
    return np.vstack(out)


class Path:
    """Minimal path builder: ``Path().move(x,y).line(..).quad(..).cubic(..).close()``.

    ``rings`` returns the flattened closed rings.  Use for shapes with mixed straight and
    curved edges (blade edges, stocks, pauldrons).
    """

    def __init__(self) -> None:
        self._rings: List[List[np.ndarray]] = []
        self._cur: List[np.ndarray] | None = None
        self._pos = np.zeros(2)

    def move(self, x: Num, y: Num) -> 'Path':
        self._cur = [np.array([[x, y]], dtype=np.float64)]
        self._rings.append(self._cur)
        self._pos = np.array([x, y], dtype=np.float64)
        return self

    def line(self, x: Num, y: Num) -> 'Path':
        assert self._cur is not None, 'call move() first'
        self._cur.append(np.array([[x, y]], dtype=np.float64))
        self._pos = np.array([x, y], dtype=np.float64)
        return self

    def lines(self, pts: Iterable[Pt]) -> 'Path':
        for x, y in pts:
            self.line(x, y)
        return self

    def quad(self, cx: Num, cy: Num, x: Num, y: Num) -> 'Path':
        seg = qbezier(tuple(self._pos), (cx, cy), (x, y))
        self._cur.append(seg[1:])  # type: ignore[union-attr]
        self._pos = np.array([x, y], dtype=np.float64)
        return self

    def cubic(self, c1x: Num, c1y: Num, c2x: Num, c2y: Num, x: Num, y: Num) -> 'Path':
        seg = bezier(tuple(self._pos), (c1x, c1y), (c2x, c2y), (x, y))
        self._cur.append(seg[1:])  # type: ignore[union-attr]
        self._pos = np.array([x, y], dtype=np.float64)
        return self

    def arc(self, cx: Num, cy: Num, rx: Num, ry: Num, a0: float, a1: float) -> 'Path':
        seg = arc_pts(cx, cy, rx, ry, a0, a1)
        if self._cur is None:
            self.move(*seg[0])
        self._cur.append(seg)  # type: ignore[union-attr]
        self._pos = seg[-1].copy()
        return self

    def close(self) -> 'Path':
        self._cur = None
        return self

    @property
    def rings(self) -> List[Ring]:
        out = []
        for parts in self._rings:
            r = np.vstack(parts)
            # drop consecutive duplicates
            keep = np.ones(len(r), bool)
            keep[1:] = np.any(np.abs(np.diff(r, axis=0)) > 1e-9, axis=1)
            r = r[keep]
            if len(r) > 2 and np.allclose(r[0], r[-1]):
                r = r[:-1]
            out.append(r)
        return out

    @property
    def ring(self) -> Ring:
        return self.rings[0]


# ----------------------------------------------------------------------------- transforms

def translate(r: Ring, dx: Num, dy: Num) -> Ring:
    return r + np.array([dx, dy], dtype=np.float64)


def scale(r: Ring, sx: Num, sy: Num | None = None, ox: Num = 0, oy: Num = 0) -> Ring:
    sy = sx if sy is None else sy
    o = np.array([ox, oy], dtype=np.float64)
    return (r - o) * np.array([sx, sy]) + o


def rotate(r: Ring, deg: float, ox: Num = 0, oy: Num = 0) -> Ring:
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    o = np.array([ox, oy], dtype=np.float64)
    m = np.array([[c, -s], [s, c]])
    return (r - o) @ m.T + o


def mirror_x(r: Ring, axis: Num) -> Ring:
    out = r.copy()
    out[:, 0] = 2 * axis - out[:, 0]
    return out[::-1]


def mirror_y(r: Ring, axis: Num) -> Ring:
    out = r.copy()
    out[:, 1] = 2 * axis - out[:, 1]
    return out[::-1]


def bbox(rings: Union[Ring, Sequence[Ring]]) -> Tuple[float, float, float, float]:
    if isinstance(rings, np.ndarray):
        rings = [rings]
    allp = np.vstack([r for r in rings if len(r)])
    return float(allp[:, 0].min()), float(allp[:, 1].min()), float(allp[:, 0].max()), float(allp[:, 1].max())


def signed_area(r: Ring) -> float:
    x, y = r[:, 0], r[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def offset(r: Ring, d: float, miter_limit: float = 2.5) -> Ring:
    """Approximate polygon offset (positive = grow).  Good for insets of simple panels."""
    n = len(r)
    if n < 3:
        return r.copy()
    sgn = 1.0 if signed_area(r) > 0 else -1.0  # orientation in y-down coords
    out = np.empty_like(r)
    for i in range(n):
        p0, p1, p2 = r[i - 1], r[i], r[(i + 1) % n]
        e0, e1 = _unit(p1 - p0), _unit(p2 - p1)
        # outward normals (for y-down + positive signed area, outward is (dy, -dx))
        n0 = np.array([e0[1], -e0[0]]) * sgn
        n1 = np.array([e1[1], -e1[0]]) * sgn
        m = n0 + n1
        mn = np.hypot(*m)
        if mn < 1e-9:
            out[i] = p1 + n0 * d
            continue
        m /= mn
        cos_half = max(np.dot(m, n0), 1.0 / miter_limit)
        out[i] = p1 + m * (d / cos_half)
    return out


def lerp(a, b, t):
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    return a + (b - a) * t


def rdp(points: Ring, tol: float) -> Ring:
    """Ramer-Douglas-Peucker simplification (open polyline)."""
    if len(points) < 3:
        return points
    stack = [(0, len(points) - 1)]
    keep = np.zeros(len(points), bool)
    keep[0] = keep[-1] = True
    while stack:
        s, e = stack.pop()
        if e <= s + 1:
            continue
        a, b = points[s], points[e]
        ab = b - a
        L = np.hypot(*ab)
        seg = points[s + 1:e]
        if L < 1e-12:
            d = np.hypot(*(seg - a).T)
        else:
            d = np.abs(ab[0] * (seg[:, 1] - a[1]) - ab[1] * (seg[:, 0] - a[0])) / L
        i = int(np.argmax(d))
        if d[i] > tol:
            k = s + 1 + i
            keep[k] = True
            stack.append((s, k))
            stack.append((k, e))
    return points[keep]


def simplify_ring(r: Ring, tol: float = 0.05) -> Ring:
    if len(r) < 8:
        return r
    closed = np.vstack([r, r[:1]])
    s = rdp(closed, tol)
    return s[:-1] if len(s) > 3 else r


def resample(r: Ring, step: float = 1.0, closed: bool = True) -> Ring:
    """Resample a ring/polyline to roughly uniform spacing (needed before wobble)."""
    pts = np.vstack([r, r[:1]]) if closed else r
    seg = np.hypot(*np.diff(pts, axis=0).T)
    L = np.concatenate([[0], np.cumsum(seg)])
    n = max(3, int(L[-1] / step))
    t = np.linspace(0, L[-1], n, endpoint=not closed)
    x = np.interp(t, L, pts[:, 0])
    y = np.interp(t, L, pts[:, 1])
    return np.stack([x, y], axis=1)


def wobble(r: Ring, amp: float, wavelength: float = 6.0, seed: int = 0, closed: bool = True) -> Ring:
    """Displace a ring along its normals with smooth value noise (hand-made / knapped edges)."""
    if amp <= 0:
        return r
    rs = resample(r, max(0.5, wavelength / 6.0), closed)
    n = len(rs)
    rng = np.random.default_rng(seed)
    seg = np.hypot(*np.diff(np.vstack([rs, rs[:1]]), axis=0).T)
    L = np.concatenate([[0], np.cumsum(seg)])[:n]
    knots = max(3, int(L[-1] / wavelength) + 1)
    vals = rng.uniform(-1, 1, knots + 1)
    if closed:
        vals[-1] = vals[0]
    u = L / max(L[-1], 1e-6) * knots
    i0 = np.floor(u).astype(int).clip(0, knots - 1)
    f = u - i0
    f = f * f * (3 - 2 * f)
    d = vals[i0] * (1 - f) + vals[i0 + 1] * f
    nx = np.roll(rs[:, 1], -1) - np.roll(rs[:, 1], 1)
    ny = -(np.roll(rs[:, 0], -1) - np.roll(rs[:, 0], 1))
    nn = np.hypot(nx, ny) + 1e-9
    sgn = 1.0 if signed_area(rs) > 0 else -1.0
    return rs + np.stack([nx / nn, ny / nn], axis=1) * (d * amp * sgn)[:, None]


def zigzag(p0: Pt, p1: Pt, teeth: int, depth: float, side: float = 1.0, jitter: float = 0.0, seed: int = 0) -> Ring:
    """Points from p0 to p1 with ``teeth`` triangular teeth offset to one side (serration, knapping)."""
    rng = np.random.default_rng(seed)
    a, b = np.asarray(p0, float), np.asarray(p1, float)
    d = b - a
    nrm = np.array([-d[1], d[0]]) / (np.hypot(*d) + 1e-9) * side
    pts = []
    for i in range(teeth):
        t0 = i / teeth
        tm = (i + 0.5 + rng.uniform(-jitter, jitter) * 0.5) / teeth
        dep = depth * (1 + rng.uniform(-jitter, jitter))
        pts.append(a + d * t0)
        pts.append(a + d * tm + nrm * dep)
    pts.append(b)
    return np.asarray(pts)


def along(p0: Pt, p1: Pt, t: float) -> Pt:
    return (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)


def polyline(pts: Iterable[Pt]) -> np.ndarray:
    return poly(pts)


def strip(x0: Num, x1: Num, y: Num, h: Num) -> Ring:
    """Horizontal band centred on ``y`` (handy for stripes and edge lines)."""
    return rect(x0, y - h / 2, x1, y + h / 2)


def taper(x0: Num, x1: Num, yc0: Num, h0: Num, yc1: Num, h1: Num) -> Ring:
    """Quad from x0 (centre yc0, height h0) to x1 (centre yc1, height h1)."""
    return P((x0, yc0 - h0 / 2), (x1, yc1 - h1 / 2), (x1, yc1 + h1 / 2), (x0, yc0 + h0 / 2))
