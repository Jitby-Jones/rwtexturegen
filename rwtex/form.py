"""3D form proxies so apparel plates obey RimWorld's 3/4 perspective.

Vanilla armor reads as *simple but deep* because every plate is a small set of flat facets
wrapped around a rounded body seen slightly from above: horizontal bands bow downward in the
middle, the neck hole is a foreshortened ellipse, side planes are narrow and darker, and
back-facing parts disappear.  A flat 2D mapping cannot do that, so plates are authored on a
3D proxy instead:

* :class:`TorsoForm` - elliptic-cylinder torso per body type: half-width ``a(v)`` from the
  south silhouette, half-depth ``d(v)`` from the east silhouette (v = 0 shoulders .. 1 bottom).
* :class:`HeadForm` - ellipsoid head fitted to the head silhouette.

Surface coordinates: ``theta`` around the body (0 = front, +pi/2 = the pawn's right side,
pi = back) and ``v`` (height) - or ``(theta, phi)`` (azimuth, latitude) on the head.
Each view (south/east/north) projects these to screen space and gives camera-space normals
for flat facet shading with a top-front light.
"""
from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

import numpy as np

from .archetypes.apparel import templates

def _n(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


# Vanilla's key light is attached to the PAWN's front (+ above), not to the camera: front
# planes read white in every view, the camera-facing side in the east view is light grey and
# the whole back in the north view is grey.  Camera space: x right, y up, z toward viewer.
LIGHTS = {'south': _n([0.0, 0.75, 0.65]), 'east': _n([0.55, 0.75, 0.25]), 'north': _n([0.0, 0.75, 0.25])}
LIGHT = LIGHTS['south']
TONES = ('light', 'base', 'shade', 'deep')
THRESH = (0.72, 0.45, -0.2)    # lambert -> tone index (vanilla: white front, grey sides, dark undersides)
TILT = 0.18                   # how far the near side of a cross-section drops on screen (3/4 view)


def tone_for(n: np.ndarray, view: str = 'south', thresh=THRESH) -> int:
    i = float(np.dot(n, LIGHTS[view]))
    for j, t in enumerate(thresh):
        if i >= t:
            return j
    return len(thresh)


def _rows(key: str, kind: str, k: float, scale: float, center) -> np.ndarray:
    a = np.asarray(templates()[kind][key], dtype=float)
    cx0, cy0 = center
    y = ((a[:, 0] + 0.5 - cy0) * scale + cy0) * k
    xl = ((a[:, 1] - cx0) * scale + cx0) * k
    xr = ((a[:, 2] - cx0) * scale + cx0) * k
    return np.stack([y, xl, xr], axis=1)


def clip_poly(poly: np.ndarray, x_min: float, x_max: float) -> np.ndarray:
    """Sutherland-Hodgman clip of a polygon (param space) to x_min <= x <= x_max."""
    def clip(pts, keep, inter):
        out = []
        n = len(pts)
        for i in range(n):
            cur, prev = pts[i], pts[i - 1]
            ci, pi_ = keep(cur), keep(prev)
            if ci:
                if not pi_:
                    out.append(inter(prev, cur))
                out.append(cur)
            elif pi_:
                out.append(inter(prev, cur))
        return out

    def ix(xc):
        def f(a, b):
            t = (xc - a[0]) / (b[0] - a[0]) if b[0] != a[0] else 0.0
            return np.array([xc, a[1] + (b[1] - a[1]) * t])
        return f
    pts = [np.asarray(p, float) for p in poly]
    pts = clip(pts, lambda p: p[0] >= x_min, ix(x_min))
    if not pts:
        return np.zeros((0, 2))
    pts = clip(pts, lambda p: p[0] <= x_max, ix(x_max))
    return np.asarray(pts) if pts else np.zeros((0, 2))


def densify(poly: np.ndarray, step_t: float = 0.06, step_v: float = 0.02) -> np.ndarray:
    out = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        m = max(1, int(max(abs(b[0] - a[0]) / step_t, abs(b[1] - a[1]) / step_v)))
        for j in range(m):
            out.append(a + (b - a) * (j / m))
    return np.asarray(out)


VIS = {'south': (-math.pi / 2, math.pi / 2), 'east': (0.0, math.pi), 'north': (math.pi / 2, 3 * math.pi / 2)}


def _area(p: np.ndarray) -> float:
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))


def visible_part(poly, view: str, wrap: float = 0.0) -> np.ndarray:
    """Clip a (theta, v) polygon to the half of the body facing the camera, trying the
    2*pi-shifted copies so patches near theta = +-pi work in every view."""
    lo, hi = VIS[view]
    p = np.asarray(poly, float)
    best = None
    for shift in (0.0, 2 * math.pi, -2 * math.pi):
        q = p.copy()
        q[:, 0] += shift
        cl = clip_poly(q, lo - wrap, hi + wrap)
        if len(cl) >= 3:
            a = _area(cl)
            if best is None or a > best[0]:
                best = (a, cl)
    return best[1] if best else np.zeros((0, 2))


class TorsoForm:
    def __init__(self, bt: str, k: float = 1.0, scale: float = 1.0, center=(64.0, 64.0)):
        self.k = k * scale
        self.S = _rows(f'{bt}_south', 'bodies', k, scale, center)
        self.E = _rows(f'{bt}_east', 'bodies', k, scale, center)
        self.N = _rows(f'{bt}_north', 'bodies', k, scale, center)
        self.top = float(self.S[:, 0].min() - 0.5 * self.k)
        self.bot = float(self.S[:, 0].max() + 0.5 * self.k)
        self.H = self.bot - self.top
        w = self.S[:, 2] - self.S[:, 1]
        n = len(w)
        self.y_sh = float(self.S[int(np.argmax(w[:max(2, int(n * 0.35))])), 0])
        lo = int(n * 0.6)
        self.y_hip = float(self.S[lo + int(np.argmax(w[lo:])), 0])
        we = self.E[:, 2] - self.E[:, 1]
        ne = len(we)
        self.ye_sh = float(self.E[int(np.argmax(we[:max(2, int(ne * 0.35))])), 0])
        self.ye_hip = float(self.E[int(ne * 0.6) + int(np.argmax(we[int(ne * 0.6):])), 0])

    # profile -----------------------------------------------------------------------------------
    def y(self, v: float) -> float:
        return self.top + v * self.H

    def _ext(self, R: np.ndarray, y: float, y_sh: float, y_hip: float) -> Tuple[float, float]:
        yy = min(max(y, y_sh), y_hip)
        xl = float(np.interp(yy, R[:, 0], R[:, 1]))
        xr = float(np.interp(yy, R[:, 0], R[:, 2]))
        return (xl + xr) / 2, (xr - xl) / 2

    def a(self, v: float) -> Tuple[float, float]:
        """(centre x, half width) seen from the front."""
        return self._ext(self.S, self.y(v), self.y_sh, self.y_hip)

    def d(self, v: float) -> Tuple[float, float]:
        """(centre x, half depth) seen from the side (east view)."""
        return self._ext(self.E, self.y(v), self.ye_sh, self.ye_hip)

    def cap(self, v: float) -> float:
        """Radius factor: shoulders round over the top (v < 0) like a dome."""
        if v >= 0.06:
            return 1.0
        t = (0.06 - v) / 0.22
        return float(math.sqrt(max(0.0, 1.0 - min(1.0, t) ** 2)))

    # projection -----------------------------------------------------------------------------------
    def P(self, view: str, theta: float, v: float, r: float = 1.0, cap: bool = True) -> Tuple[float, float]:
        cs, a = self.a(v)
        ce, dd = self.d(v)
        c = self.cap(v) if cap else 1.0
        y = self.y(v)
        if view == 'south':
            return cs - a * r * c * math.sin(theta), y + TILT * dd * r * c * (math.cos(theta) - 0.5)
        if view == 'north':
            cn, an = self._ext(self.N, y, self.y_sh, self.y_hip)
            return cn + an * r * c * math.sin(theta), y + TILT * dd * r * c * (-math.cos(theta) - 0.5)
        return ce + dd * r * c * math.cos(theta), y + TILT * a * r * c * (math.sin(theta) - 0.5)

    def normal(self, view: str, theta: float, v: float) -> np.ndarray:
        dv = 0.03
        _, a0 = self.a(v - dv)
        _, a1 = self.a(v + dv)
        slope = (a1 * self.cap(v + dv) - a0 * self.cap(v - dv)) / (2 * dv * self.H)
        ny = float(np.clip(slope * 0.45, -0.18, 0.5)) + (0.55 if v < 0.06 else 0.0) * (1 - self.cap(v)) * 2
        if view == 'south':
            n = np.array([-math.sin(theta), ny, math.cos(theta)])
        elif view == 'north':
            n = np.array([math.sin(theta), ny, -math.cos(theta)])
        else:
            n = np.array([math.cos(theta), ny, math.sin(theta)])
        return n / np.linalg.norm(n)

    def ring(self, view: str, poly_tv, r=1.0, wrap: float = 0.0, cap: bool = True) -> np.ndarray:
        """Project a (theta, v) polygon; ``r`` is a radius factor or a callable v -> r
        (e.g. splayed tassets).  ``wrap`` extends visibility past the silhouette for parts
        that stick out (pauldrons)."""
        clipped = visible_part(poly_tv, view, wrap)
        if len(clipped) < 3:
            return np.zeros((0, 2))
        d = densify(clipped)
        rf = r if callable(r) else (lambda v, _r=r: _r)
        return np.array([self.P(view, t, v, rf(v), cap) for t, v in d])


class HeadForm:
    """Ellipsoid head fitted to the head silhouette (Average head template)."""

    def __init__(self, view: str, k: float = 1.0, scale: float = 1.0, center=(64.0, 64.0)):
        R = _rows(f'Average_{view}', 'heads', k, scale, center)
        self.k = k * scale
        self.view = view
        self.y0, self.y1 = float(R[:, 0].min()), float(R[:, 0].max())
        w = R[:, 2] - R[:, 1]
        i = int(np.argmax(w))
        self.cx = float((R[i, 1] + R[i, 2]) / 2)
        self.cy = (self.y0 + self.y1) / 2
        self.rx = float(w[i] / 2)
        self.ry = (self.y1 - self.y0) / 2
        self.R = R

    def P(self, theta: float, phi: float, r: float = 1.0) -> Tuple[float, float]:
        """theta: azimuth (0 = face), phi: latitude (+ up)."""
        cp = math.cos(phi)
        if self.view == 'south':
            x = -math.sin(theta) * cp
            z = math.cos(theta) * cp
        elif self.view == 'north':
            x = math.sin(theta) * cp
            z = -math.cos(theta) * cp
        else:
            x = math.cos(theta) * cp
            z = math.sin(theta) * cp
        y = math.sin(phi)
        return self.cx + x * self.rx * r, self.cy - y * self.ry * r * 0.92 + z * self.ry * r * TILT * 0.55

    def normal(self, theta: float, phi: float) -> np.ndarray:
        cp = math.cos(phi)
        if self.view == 'south':
            n = np.array([-math.sin(theta) * cp, math.sin(phi), math.cos(theta) * cp])
        elif self.view == 'north':
            n = np.array([math.sin(theta) * cp, math.sin(phi), -math.cos(theta) * cp])
        else:
            n = np.array([math.cos(theta) * cp, math.sin(phi), math.sin(theta) * cp])
        return n / np.linalg.norm(n)

    def visible(self, theta: float, phi: float) -> bool:
        return self.normal(theta, phi)[2] > -0.05

    def ring(self, poly_tp, r: float = 1.0) -> np.ndarray:
        clipped = visible_part(poly_tp, self.view, 0.05)
        if len(clipped) < 3:
            return np.zeros((0, 2))
        d = densify(clipped, 0.08, 0.06)
        return np.array([self.P(t, ph, r) for t, ph in d])
