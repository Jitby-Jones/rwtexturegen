"""Scene graph, rasteriser, CutoutComplex mask pass and SVG exporter.

A :class:`Scene` is an ordered list of :class:`Part` objects.  Each part is a vector shape
(even-odd rings) with a :class:`~rwtex.materials.Material`, shading operations and detail
overlays.  Rendering reproduces the vanilla RimWorld recipe:

1. thick pure-black *outer* outline around the union silhouette (~3 px at 128 px);
2. parts painted back-to-front; each part's own thinner black outline is painted *under*
   its fill so it only shows where it overlaps lower parts (inner part lines);
3. flat base colour + light/shade bands (bevel by light direction, facet splits);
4. details (engraved lines, vents, decals, emissive strips) clipped to the part;
5. optional glow/halo for emissive parts;
6. supersampled rasterisation (default 8x for 128 px) box-filtered down for clean AA,
   transparent pixels keep black RGB (avoids the white compression halo).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import geom
from .color import RGB, rgb, to_hex
from .materials import BLACK, Material, MaterialLike, get as getmat

ColorRef = Union[str, Tuple[float, float, float], Sequence[float]]
Rings = List[np.ndarray]


# ----------------------------------------------------------------------------- shading ops

@dataclass
class Bevel:
    """Edge bands from the light direction: lit band on edges facing the light, shade band
    on edges facing away.  Widths are in output pixels."""
    light: float = 1.5
    shade: float = 1.5
    light_tone: ColorRef = 'light'
    shade_tone: ColorRef = 'shade'
    angle: Optional[float] = None  # direction *toward* the light in degrees; None = scene light


@dataclass
class Split:
    """Hard two-tone facet split (vanilla blades: white top / #ddd bottom)."""
    at: float = 0.55
    angle: float = 90.0  # axis direction; 90 = downward (region beyond ``at`` gets ``tone``)
    tone: ColorRef = 'shade'
    soft: float = 0.0


@dataclass
class Gradient:
    tones: Tuple[ColorRef, ...] = ('light', 'base', 'shade')
    angle: float = 90.0
    opacity: float = 1.0


@dataclass
class Rim:
    """Inner band along every edge (inset panel look)."""
    width: float = 1.0
    tone: ColorRef = 'deep'


@dataclass
class Facets:
    """Chamfered-plate shading (the vanilla armor look): an inset front face plus side facets
    whose tone follows how much each edge faces the light.  ``tones`` go from facing the light
    to facing away; ``width`` is the bevel width in px."""
    width: float = 2.5
    tones: Tuple[ColorRef, ...] = ('light', 'base', 'shade', 'deep')
    thresholds: Tuple[float, ...] = (0.45, -0.25, -0.8)
    angle: Optional[float] = None
    simplify: float = 0.35


@dataclass
class Dome:
    """Soft radial highlight for curved shells (helmet domes, pauldrons)."""
    tones: Tuple[ColorRef, ...] = ('light', 'base', 'shade')
    center: Tuple[float, float] = (-0.25, -0.35)   # highlight offset in bbox-relative units
    radius: float = 1.1
    opacity: float = 1.0


ShadeOp = Union[Bevel, Split, Gradient, Rim, Facets, Dome]


# ----------------------------------------------------------------------------- detail ops

@dataclass
class Line:
    pts: np.ndarray
    width: float = 1.0
    tone: ColorRef = 'line'
    closed: bool = False
    clip: bool = True
    mask: Optional[str] = 'inherit'


@dataclass
class Fill:
    rings: Rings
    tone: ColorRef = 'light'
    clip: bool = True
    mask: Optional[str] = 'inherit'
    opacity: float = 1.0
    outline: float = 0.0
    outline_tone: ColorRef = 'black'
    shading: List[ShadeOp] = field(default_factory=list)


Detail = Union[Line, Fill]


@dataclass
class Glow:
    color: Optional[ColorRef] = None
    radius: float = 3.0
    strength: float = 0.55
    mode: str = 'halo'  # 'halo' (soft, behind, may extend past the outline) | 'bloom' (on top)


MASK_COLORS = {'r': (1.0, 0.0, 0.0), 'g': (0.0, 1.0, 0.0), 'b': (0.0, 0.0, 1.0),
               'rg': (1.0, 1.0, 0.0), 'none': (0.0, 0.0, 0.0)}


class Part:
    """One vector shape with material, shading and details."""

    def __init__(self, name: str, rings: Union[np.ndarray, Rings], mat: MaterialLike = 'gunmetal', *,
                 z: float = 0.0, outline: Union[str, float, None] = 'auto', silhouette: bool = True,
                 mask: Union[str, Tuple[float, float, float], None] = 'material',
                 shading: Optional[List[ShadeOp]] = None, details: Optional[List[Detail]] = None,
                 glow: Optional[Glow] = None, clip: Union[None, 'Part', np.ndarray, Rings] = None,
                 opacity: float = 1.0, tone: ColorRef = 'base', tags: Iterable[str] = ()):
        self.name = name
        self.rings: Rings = [rings] if isinstance(rings, np.ndarray) else list(rings)
        self.mat: Material = getmat(mat)
        self.z = z
        self.outline = outline
        self.silhouette = silhouette
        self.mask = mask
        self.shading: List[ShadeOp] = list(shading or [])
        self.details: List[Detail] = list(details or [])
        self.glow = glow
        if isinstance(clip, Part):
            clip = clip.rings
        elif isinstance(clip, np.ndarray):
            clip = [clip]
        self.clip: Optional[Rings] = clip
        self.opacity = opacity
        self.tone = tone
        self.tags = set(tags)

    # fluent helpers --------------------------------------------------------------------
    def shade(self, *ops: ShadeOp) -> 'Part':
        self.shading.extend(ops)
        return self

    def detail(self, *ops: Detail) -> 'Part':
        self.details.extend(ops)
        return self

    def line(self, pts, width: float = 1.0, tone: ColorRef = 'line', **kw) -> 'Part':
        self.details.append(Line(geom.poly(pts), width, tone, **kw))
        return self

    def fill(self, rings, tone: ColorRef = 'light', **kw) -> 'Part':
        rings = [rings] if isinstance(rings, np.ndarray) else list(rings)
        self.details.append(Fill(rings, tone, **kw))
        return self

    def bbox(self):
        return geom.bbox(self.rings)

    def mask_color(self) -> Tuple[float, float, float]:
        m = self.mask
        if m == 'material':
            m = self.mat.mask
        if m is None:
            return (0.0, 0.0, 0.0)
        if isinstance(m, str):
            return MASK_COLORS[m]
        return tuple(float(v) for v in m)  # type: ignore[return-value]

    def __repr__(self) -> str:
        return f'Part({self.name!r}, mat={self.mat.name}, z={self.z})'


# ----------------------------------------------------------------------------- helpers

def resolve(ref: ColorRef, mat: Material) -> RGB:
    if isinstance(ref, (tuple, list, np.ndarray)):
        return rgb(ref)
    if isinstance(ref, str):
        if ref.startswith('#'):
            return rgb(ref)
        if '.' in ref:
            mname, tone = ref.rsplit('.', 1)
            return getmat(mname).tone(tone)
        try:
            return mat.tone(ref)
        except KeyError:
            return getmat(ref).base
    raise TypeError(f'bad colour ref {ref!r}')


def _shift(m: np.ndarray, dx: int, dy: int) -> np.ndarray:
    """out[y, x] = m[y + dy, x + dx] (zero outside)."""
    h, w = m.shape
    out = np.zeros_like(m)
    if abs(dx) >= w or abs(dy) >= h:
        return out
    ys = slice(max(0, -dy), min(h, h - dy))
    yd = slice(max(0, dy), min(h, h + dy))
    xs = slice(max(0, -dx), min(w, w - dx))
    xd = slice(max(0, dx), min(w, w + dx))
    out[ys, xs] = m[yd, xd]
    return out


def _erode(m: np.ndarray, r: float) -> np.ndarray:
    if r <= 0:
        return m
    out = m.copy()
    n = max(8, int(r * 3))
    for k in range(n):
        a = 2 * math.pi * k / n
        out = np.minimum(out, _shift(m, int(round(math.cos(a) * r)), int(round(math.sin(a) * r))))
    # include the half-radius ring for smoother corners
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        out = np.minimum(out, _shift(m, int(round(math.cos(a) * r * 0.6)), int(round(math.sin(a) * r * 0.6))))
    return out


class _Win:
    __slots__ = ('y0', 'x0', 'y1', 'x1')

    def __init__(self, y0, x0, y1, x1):
        self.y0, self.x0, self.y1, self.x1 = y0, x0, y1, x1

    @property
    def shape(self):
        return (self.y1 - self.y0, self.x1 - self.x0)

    def sl(self):
        return (slice(self.y0, self.y1), slice(self.x0, self.x1))

    def empty(self):
        return self.y1 <= self.y0 or self.x1 <= self.x0


class Scene:
    """A texture under construction."""

    def __init__(self, size: Union[int, Tuple[int, int]] = 128, ss: Optional[int] = None,
                 outline: Optional[float] = None, inner: Optional[float] = None,
                 light_angle: float = -105.0, name: str = 'texture',
                 occlusion: Optional[Tuple[float, float, float]] = None):
        if isinstance(size, int):
            self.w = self.h = size
        else:
            self.w, self.h = size
        ref = min(self.w, self.h)
        self.ss = ss or max(2, min(8, 1024 // ref))
        k = ref / 128.0
        self.outline = 3.0 * k if outline is None else outline   # visible outer outline px
        self.inner = 1.4 * k if inner is None else inner        # visible inner line px
        self.light_angle = light_angle
        self.occlusion = occlusion   # (distance px, strength 0..1, blur px): contact shadows under upper parts
        self._occl = None
        self.parts: List[Part] = []
        self.name = name
        self.meta: dict = {}

    # building ------------------------------------------------------------------------------
    def add(self, name_or_part: Union[str, Part], rings=None, mat: MaterialLike = 'gunmetal', **kw) -> Part:
        if isinstance(name_or_part, Part):
            p = name_or_part
        else:
            p = Part(name_or_part, rings, mat, **kw)
        if 'z' not in kw and not isinstance(name_or_part, Part):
            p.z = len(self.parts)
        self.parts.append(p)
        return p

    def extend(self, parts: Iterable[Part]) -> None:
        for p in parts:
            self.add(p)

    def get(self, name: str) -> Part:
        for p in self.parts:
            if p.name == name:
                return p
        raise KeyError(name)

    def ordered(self) -> List[Part]:
        return sorted(self.parts, key=lambda p: p.z)

    def bbox(self):
        return geom.bbox([r for p in self.parts if p.silhouette for r in p.rings])

    # raster primitives ------------------------------------------------------------------------
    def _win(self, rings: Rings, pad_px: float = 0.0) -> _Win:
        x0, y0, x1, y1 = geom.bbox(rings)
        s = self.ss
        pad = pad_px * s + 2
        return _Win(max(0, int(math.floor(y0 * s - pad))), max(0, int(math.floor(x0 * s - pad))),
                    min(self.h * s, int(math.ceil(y1 * s + pad))), min(self.w * s, int(math.ceil(x1 * s + pad))))

    def _pts(self, r: np.ndarray, win: _Win):
        s = self.ss
        return [(float(x * s - win.x0 - 0.5), float(y * s - win.y0 - 0.5)) for x, y in r]

    def _fill(self, rings: Rings, win: _Win) -> np.ndarray:
        h, w = win.shape
        if len(rings) == 1:
            im = Image.new('L', (w, h), 0)
            if len(rings[0]) >= 3:
                ImageDraw.Draw(im).polygon(self._pts(rings[0], win), fill=255)
            return np.asarray(im, dtype=np.float32) / 255.0
        acc = np.zeros((h, w), dtype=bool)
        for r in rings:
            if len(r) < 3:
                continue
            im = Image.new('L', (w, h), 0)
            ImageDraw.Draw(im).polygon(self._pts(r, win), fill=255)
            acc ^= np.asarray(im) > 127
        return acc.astype(np.float32)

    def _stroke(self, lines: Rings, width_px: float, win: _Win, closed: bool = True) -> np.ndarray:
        h, w = win.shape
        im = Image.new('L', (w, h), 0)
        d = ImageDraw.Draw(im)
        wd = max(1, int(round(width_px * self.ss)))
        rad = wd / 2.0
        for r in lines:
            pts = self._pts(r, win)
            if len(pts) < 2:
                if pts:
                    x, y = pts[0]
                    d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=255)
                continue
            seq = pts + pts[:2] if closed else pts
            d.line(seq, fill=255, width=wd, joint='curve')
            ends = pts if closed and len(pts) < 6 else [pts[0], pts[-1]]
            for (x, y) in ends:
                d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=255)
        return np.asarray(im, dtype=np.float32) / 255.0

    @staticmethod
    def _over(canvas: np.ndarray, win: _Win, alpha: np.ndarray, color) -> None:
        dst = canvas[win.sl()]
        a = alpha[..., None]
        col = np.asarray(color, dtype=np.float32)
        dst[..., :3] = col * a + dst[..., :3] * (1.0 - a)
        dst[..., 3:4] = a + dst[..., 3:4] * (1.0 - a)

    def _light_vec(self, angle: Optional[float]) -> Tuple[float, float]:
        a = math.radians(self.light_angle if angle is None else angle)
        return math.cos(a), math.sin(a)

    # part rendering --------------------------------------------------------------------------
    def _part_masks(self, p: Part) -> Tuple[_Win, np.ndarray]:
        lw = self._line_w(p)
        win = self._win(p.rings, pad_px=max(lw, 1.0) + 1)
        m = self._fill(p.rings, win)
        if p.clip:
            m = m * self._fill(p.clip, win)
        return win, m

    def _line_w(self, p: Part) -> float:
        if p.outline in (None, False, 0):
            return 0.0
        if p.outline == 'auto':
            return self.inner
        return float(p.outline)

    def _shade_masks(self, op: ShadeOp, m: np.ndarray, win: _Win, mat: Material):
        """Yield (alpha, colour) pairs for a shading op on mask ``m``."""
        s = self.ss
        if isinstance(op, Bevel):
            lx, ly = self._light_vec(op.angle)
            if op.light > 0:
                dx, dy = int(round(lx * op.light * s)), int(round(ly * op.light * s))
                yield m * (1.0 - _shift(m, dx, dy)), resolve(op.light_tone, mat)
            if op.shade > 0:
                dx, dy = int(round(-lx * op.shade * s)), int(round(-ly * op.shade * s))
                yield m * (1.0 - _shift(m, dx, dy)), resolve(op.shade_tone, mat)
        elif isinstance(op, (Split, Gradient)):
            h, w = m.shape
            a = math.radians(op.angle)
            nx, ny = math.cos(a), math.sin(a)
            yy, xx = np.ogrid[0:h, 0:w]
            t = (xx * nx + yy * ny).astype(np.float32)
            sel = m > 0.5
            if not sel.any():
                return
            tv = np.broadcast_to(t, m.shape)[sel]
            tmin, tmax = float(tv.min()), float(tv.max())
            if isinstance(op, Split):
                t0 = tmin + op.at * (tmax - tmin)
                if op.soft > 0:
                    band = np.clip((t - t0) / (op.soft * s) + 0.5, 0, 1)
                else:
                    band = (t >= t0).astype(np.float32)
                yield m * band, resolve(op.tone, mat)
            else:
                tn = np.clip((t - tmin) / max(tmax - tmin, 1e-6), 0, 1)
                cols = np.array([resolve(c, mat) for c in op.tones], dtype=np.float32)
                k = len(cols) - 1
                pos = tn * k
                i0 = np.clip(np.floor(pos).astype(int), 0, k - 1)
                f = (pos - i0)[..., None]
                col = cols[i0] * (1 - f) + cols[i0 + 1] * f
                col = np.broadcast_to(col, (h, w, 3))
                yield m * op.opacity, col
        elif isinstance(op, Rim):
            e = _erode(m, op.width * s)
            yield m * (1.0 - e), resolve(op.tone, mat)
        elif isinstance(op, Dome):
            h, w = m.shape
            sel = m > 0.5
            if not sel.any():
                return
            ys, xs = np.nonzero(sel)
            cx = (xs.min() + xs.max()) / 2 + op.center[0] * (xs.max() - xs.min()) / 2
            cy = (ys.min() + ys.max()) / 2 + op.center[1] * (ys.max() - ys.min()) / 2
            rad = op.radius * max(xs.max() - xs.min(), ys.max() - ys.min()) / 2
            yy, xx = np.ogrid[0:h, 0:w]
            d = np.clip(np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(rad, 1), 0, 1).astype(np.float32)
            cols = np.array([resolve(c, mat) for c in op.tones], dtype=np.float32)
            k = len(cols) - 1
            pos = d * k
            i0 = np.clip(np.floor(pos).astype(int), 0, k - 1)
            f = (pos - i0)[..., None]
            col = cols[i0] * (1 - f) + cols[i0 + 1] * f
            yield m * op.opacity, col

    def _facet_masks(self, op: 'Facets', rings: Rings, m: np.ndarray, win: _Win, mat: Material):
        """Rasterise side facets of a chamfered plate, one mask per tone."""
        s = self.ss
        h, w = m.shape
        layers = [Image.new('L', (w, h), 0) for _ in op.tones]
        draws = [ImageDraw.Draw(im) for im in layers]
        for quad, lvl in facet_geometry(op, rings, self._light_vec(op.angle)):
            draws[lvl].polygon([(float(x * s - win.x0 - 0.5), float(y * s - win.y0 - 0.5)) for x, y in quad], fill=255)
        for im, tone in zip(layers, op.tones):
            a = np.asarray(im, dtype=np.float32) / 255.0
            if a.any():
                yield a * m, resolve(tone, mat)

    def _render_part(self, canvas: np.ndarray, p: Part) -> None:
        win, m = self._part_masks(p)
        if win.empty():
            return
        lw = self._line_w(p)
        if lw > 0:
            st = self._stroke(p.rings, 2 * lw, win, closed=True)
            if p.clip:
                st = st * self._fill(p.clip, win)
            self._over(canvas, win, st * p.opacity, BLACK)
        self._over(canvas, win, m * p.opacity, resolve(p.tone, p.mat))
        for op in p.shading:
            gen = self._facet_masks(op, p.rings, m, win, p.mat) if isinstance(op, Facets) else self._shade_masks(op, m, win, p.mat)
            for a, col in gen:
                self._over(canvas, win, a * p.opacity, col)
        for d in p.details:
            self._render_detail(canvas, p, d, m, win)
        if self._occl is not None:
            self._apply_occlusion(canvas, p, m, win)

    def _render_detail(self, canvas, p: Part, d: Detail, m: np.ndarray, win: _Win) -> None:
        if isinstance(d, Line):
            if d.clip:
                dwin, clipm = win, m
            else:
                dwin, clipm = self._win([d.pts], pad_px=d.width + 1), None
            a = self._stroke([d.pts], d.width, dwin, closed=d.closed)
            if clipm is not None:
                a = a * clipm
            self._over(canvas, dwin, a, resolve(d.tone, p.mat))
        elif isinstance(d, Fill):
            if d.clip:
                dwin = win
            else:
                dwin = self._win(d.rings, pad_px=d.outline + 1)
            if d.outline > 0:
                st = self._stroke(d.rings, 2 * d.outline, dwin, closed=True)
                if d.clip:
                    st = st * m
                self._over(canvas, dwin, st * d.opacity, resolve(d.outline_tone, p.mat))
            a = self._fill(d.rings, dwin)
            if d.clip:
                a = a * m
            self._over(canvas, dwin, a * d.opacity, resolve(d.tone, p.mat))
            for op in d.shading:
                gen = self._facet_masks(op, d.rings, a, dwin, p.mat) if isinstance(op, Facets) else self._shade_masks(op, a, dwin, p.mat)
                for sa, col in gen:
                    self._over(canvas, dwin, sa * d.opacity, col)

    # occlusion ---------------------------------------------------------------------------------
    def _occlusion_unions(self, order: List[Part]) -> dict:
        """For each part, the union mask of every part drawn after it (casts contact shadows)."""
        s = self.ss
        H, W = self.h * s, self.w * s
        U = np.zeros((H, W), np.float32)
        res = {}
        for p in reversed(order):
            res[id(p)] = U.copy() if p.silhouette or True else None
            win, m = self._part_masks(p)
            if not win.empty() and p.silhouette:
                sl = win.sl()
                U[sl] = np.maximum(U[sl], m)
        return res

    def _apply_occlusion(self, canvas: np.ndarray, p: Part, m: np.ndarray, win: _Win) -> None:
        U = self._occl.get(id(p))
        if U is None:
            return
        dist, strength, blur = self.occlusion
        s = self.ss
        lx, ly = self._light_vec(None)
        pad = int((dist + blur * 2 + 2) * s)
        y0, x0 = max(0, win.y0 - pad), max(0, win.x0 - pad)
        y1, x1 = min(U.shape[0], win.y1 + pad), min(U.shape[1], win.x1 + pad)
        crop = U[y0:y1, x0:x1]
        if not crop.any():
            return
        sh = _shift(crop, int(round(lx * dist * s)), int(round(ly * dist * s)))
        sh = np.maximum(sh, crop * 0.0)
        im = Image.fromarray((sh * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(max(0.5, blur * s)))
        shadow = np.asarray(im, np.float32) / 255.0
        shadow = shadow[win.y0 - y0:win.y0 - y0 + m.shape[0], win.x0 - x0:win.x0 - x0 + m.shape[1]]
        dst = canvas[win.sl()]
        dark = 1.0 - strength * shadow * m
        dst[..., :3] *= dark[..., None]

    # glow -------------------------------------------------------------------------------------
    def _glow_layer(self, mode: str) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        s = self.ss
        H, W = self.h * s, self.w * s
        acc_a = np.zeros((H, W), np.float32)
        acc_c = np.zeros((H, W, 3), np.float32)
        any_ = False
        for p in self.ordered():
            g = p.glow
            if g is None or g.mode != mode:
                continue
            win, m = self._part_masks(p)
            full = np.zeros((H, W), np.float32)
            full[win.sl()] = m
            im = Image.fromarray((full * 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(g.radius * s))
            b = np.asarray(im, np.float32) / 255.0 * g.strength
            col = np.array(resolve(g.color, p.mat) if g.color is not None else p.mat.tone('glow'), np.float32)
            acc_c = acc_c * (1 - b[..., None]) + col * b[..., None]
            acc_a = 1 - (1 - acc_a) * (1 - b)
            any_ = True
        return (acc_a, acc_c) if any_ else None

    # public render ----------------------------------------------------------------------------
    def silhouette_mask(self, extra: float = 0.0) -> np.ndarray:
        """Union silhouette dilated by the outer outline (+extra px), at supersampled res."""
        s = self.ss
        H, W = self.h * s, self.w * s
        out = np.zeros((H, W), np.float32)
        R = self.outline + extra
        for p in self.parts:
            if not p.silhouette:
                continue
            win = self._win(p.rings, pad_px=R + 1)
            if win.empty():
                continue
            m = self._fill(p.rings, win)
            if p.clip:
                m = m * self._fill(p.clip, win)
            if R > 0:
                st = self._stroke(p.rings, 2 * R, win, closed=True)
                if p.clip:
                    st = st * self._fill(p.clip, win) if False else st
                m = np.maximum(m, st)
            sl = win.sl()
            out[sl] = np.maximum(out[sl], m)
        return out

    def render_ss(self, glow: bool = True) -> np.ndarray:
        s = self.ss
        H, W = self.h * s, self.w * s
        canvas = np.zeros((H, W, 4), np.float32)
        full = _Win(0, 0, H, W)
        if glow:
            halo = self._glow_layer('halo')
            if halo is not None:
                a, c = halo
                self._over(canvas, full, a, c)
        if self.outline > 0:
            self._over(canvas, full, self.silhouette_mask(), BLACK)
        order = self.ordered()
        self._occl = self._occlusion_unions(order) if self.occlusion else None
        for p in order:
            self._render_part(canvas, p)
        self._occl = None
        if glow:
            bloom = self._glow_layer('bloom')
            if bloom is not None:
                a, c = bloom
                inside = canvas[..., 3:4]
                rgbp = canvas[..., :3]
                # screen blend restricted to existing coverage
                lit = 1 - (1 - rgbp) * (1 - c * a[..., None] * inside)
                canvas[..., :3] = rgbp * (1 - inside) + lit * inside
        return canvas

    def render(self, glow: bool = True) -> Image.Image:
        return downsample(self.render_ss(glow), self.ss)

    def render_mask(self) -> Image.Image:
        """CutoutComplex mask: red = primary colour, green = secondary, black = untinted."""
        s = self.ss
        H, W = self.h * s, self.w * s
        canvas = np.zeros((H, W, 4), np.float32)
        canvas[..., 3] = 1.0
        for p in self.ordered():
            win, m = self._part_masks(p)
            if win.empty():
                continue
            lw = self._line_w(p)
            if lw > 0:
                st = self._stroke(p.rings, 2 * lw, win, closed=True)
                self._over(canvas, win, st, BLACK)
            pc = p.mask_color()
            self._over(canvas, win, m, pc)
            for d in p.details:
                if d.mask == 'inherit':
                    continue
                dc = MASK_COLORS['none'] if d.mask is None else (MASK_COLORS[d.mask] if isinstance(d.mask, str) else d.mask)
                if isinstance(d, Line):
                    dwin = win if d.clip else self._win([d.pts], pad_px=d.width + 1)
                    a = self._stroke([d.pts], d.width, dwin, closed=d.closed)
                    if d.clip:
                        a = a * m
                else:
                    dwin = win if d.clip else self._win(d.rings, pad_px=d.outline + 1)
                    a = self._fill(d.rings, dwin)
                    if d.clip:
                        a = a * m
                self._over(canvas, dwin, a, dc)
        img = downsample(canvas, s)
        return img.convert('RGB')

    def has_mask(self) -> bool:
        return any(p.mask_color() != (0.0, 0.0, 0.0) for p in self.parts)

    # svg --------------------------------------------------------------------------------------
    def to_svg(self, glow: bool = True) -> str:
        return _svg(self, glow)


def _inside(pts: np.ndarray, rings: Rings) -> np.ndarray:
    """Even-odd point-in-polygon for many points against all rings."""
    res = np.zeros(len(pts), bool)
    x, y = pts[:, 0][:, None], pts[:, 1][:, None]
    for r in rings:
        if len(r) < 3:
            continue
        x1, y1 = r[:, 0][None, :], r[:, 1][None, :]
        x2, y2 = np.roll(r[:, 0], -1)[None, :], np.roll(r[:, 1], -1)[None, :]
        cond = (y1 > y) != (y2 > y)
        xint = (x2 - x1) * (y - y1) / np.where(np.abs(y2 - y1) < 1e-12, 1e-12, (y2 - y1)) + x1
        res ^= (np.sum(cond & (x < xint), axis=1) % 2).astype(bool)
    return res


def facet_geometry(op: 'Facets', rings: Rings, light: Tuple[float, float]):
    """Side-facet quads (+ tone level) of a chamfered plate - shared by raster and SVG."""
    lx, ly = light
    out = []
    for r in rings:
        if len(r) < 3:
            continue
        rr = geom.simplify_ring(r, op.simplify) if len(r) > 8 else r
        n = len(rr)
        nxt = np.roll(rr, -1, axis=0)
        e = nxt - rr
        L = np.hypot(e[:, 0], e[:, 1]) + 1e-9
        nrm = np.stack([e[:, 1] / L, -e[:, 0] / L], axis=1)
        mid = (rr + nxt) / 2
        inside = _inside(mid + nrm * 0.6, rings)
        nrm[inside] *= -1
        vn = nrm + np.roll(nrm, 1, axis=0)
        vl = np.hypot(vn[:, 0], vn[:, 1]) + 1e-9
        vn = vn / vl[:, None]
        cosh = np.clip((vn * nrm).sum(1), 0.4, 1.0)
        inset = rr - vn * (op.width / cosh)[:, None]
        facing = nrm[:, 0] * lx + nrm[:, 1] * ly
        for i in range(n):
            t = facing[i]
            lvl = len(op.tones) - 1
            for j, th in enumerate(op.thresholds):
                if t > th:
                    lvl = j
                    break
            j2 = (i + 1) % n
            out.append((np.array([rr[i], rr[j2], inset[j2], inset[i]]), lvl))
    return out


def downsample(canvas: np.ndarray, ss: int) -> Image.Image:
    H, W = canvas.shape[0] // ss, canvas.shape[1] // ss
    c = canvas[:H * ss, :W * ss].reshape(H, ss, W, ss, canvas.shape[2]).mean(axis=(1, 3))
    a = c[..., 3:4]
    col = np.where(a > 1e-5, c[..., :3] / np.maximum(a, 1e-5), 0.0)
    out = (np.clip(np.concatenate([col, a], axis=2), 0, 1) * 255 + 0.5).astype(np.uint8)
    out[out[..., 3] == 0, :3] = 0   # faint halo edges can round to alpha 0: keep their RGB black
    return Image.fromarray(out, 'RGBA')


# ----------------------------------------------------------------------------- SVG export

def _d(rings: Rings) -> str:
    out = []
    for r in rings:
        r2 = geom.simplify_ring(r, 0.03)
        if len(r2) < 2:
            continue
        pts = ' '.join(f'{x:.2f},{y:.2f}' for x, y in r2)
        out.append(f'M{pts}Z')
    return ''.join(out)


def _pl(pts: np.ndarray) -> str:
    return ' '.join(f'{x:.2f},{y:.2f}' for x, y in pts)


def _svg(scene: Scene, glow: bool) -> str:
    defs: List[str] = []
    body: List[str] = []
    W, H = scene.w, scene.h
    R = scene.outline
    big = max(W, H) * 4

    def col(ref, mat):
        c = resolve(ref, mat)
        return to_hex(c)

    if glow:
        for i, p in enumerate(scene.ordered()):
            if p.glow is not None and p.glow.mode == 'halo':
                fid = f'glow{i}'
                defs.append(f'<filter id="{fid}" x="-50%" y="-50%" width="200%" height="200%">'
                            f'<feGaussianBlur stdDeviation="{p.glow.radius:.2f}"/></filter>')
                gc = col(p.glow.color, p.mat) if p.glow.color is not None else to_hex(p.mat.tone('glow'))
                body.append(f'<path d="{_d(p.rings)}" fill="{gc}" opacity="{p.glow.strength:.2f}" '
                            f'filter="url(#{fid})" fill-rule="evenodd"/>')
    sil = [p for p in scene.parts if p.silhouette]
    if R > 0 and sil:
        body.append(f'<g id="outline" fill="#000000" stroke="#000000" stroke-width="{2 * R:.2f}" '
                    f'stroke-linejoin="round" fill-rule="evenodd">')
        for p in sil:
            body.append(f'<path d="{_d(p.rings)}"/>')
        body.append('</g>')
    for i, p in enumerate(scene.ordered()):
        d = _d(p.rings)
        cid = f'clip{i}'
        clip_rings = p.rings if not p.clip else p.clip
        defs.append(f'<clipPath id="{cid}"><path d="{_d(clip_rings)}" clip-rule="evenodd"/></clipPath>')
        g = [f'<g id="{p.name}" opacity="{p.opacity:.2f}">' if p.opacity < 1 else f'<g id="{p.name}">']
        pclip = f' clip-path="url(#{cid}x)"' if p.clip else ''
        if p.clip:
            defs.append(f'<clipPath id="{cid}x"><path d="{_d(p.clip)}" clip-rule="evenodd"/></clipPath>')
        lw = scene._line_w(p)
        if lw > 0:
            g.append(f'<path d="{d}" fill="none" stroke="#000000" stroke-width="{2 * lw:.2f}" stroke-linejoin="round"{pclip}/>')
        g.append(f'<path d="{d}" fill="{col(p.tone, p.mat)}" fill-rule="evenodd"{pclip}/>')
        x0, y0, x1, y1 = geom.bbox(p.rings)
        for j, op in enumerate(p.shading):
            if isinstance(op, Bevel):
                lx, ly = scene._light_vec(op.angle)
                for k, (wd, tone, sgn) in enumerate(((op.light, op.light_tone, 1), (op.shade, op.shade_tone, -1))):
                    if wd <= 0:
                        continue
                    mid = f'm{i}_{j}_{k}'
                    tx, ty = -sgn * lx * wd, -sgn * ly * wd
                    defs.append(f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
                                f'<path d="{d}" fill="#ffffff" fill-rule="evenodd"/>'
                                f'<path d="{d}" fill="#000000" fill-rule="evenodd" transform="translate({tx:.2f},{ty:.2f})"/></mask>')
                    g.append(f'<path d="{d}" fill="{col(tone, p.mat)}" fill-rule="evenodd" mask="url(#{mid})"{pclip}/>')
            elif isinstance(op, Split):
                a = math.radians(op.angle)
                nx, ny = math.cos(a), math.sin(a)
                pts = np.vstack(p.rings)
                t = pts[:, 0] * nx + pts[:, 1] * ny
                t0 = t.min() + op.at * (t.max() - t.min())
                cx, cy = nx * t0, ny * t0
                tx, ty = -ny, nx
                hp = geom.P((cx + tx * big, cy + ty * big), (cx + tx * big + nx * big, cy + ty * big + ny * big),
                            (cx - tx * big + nx * big, cy - ty * big + ny * big), (cx - tx * big, cy - ty * big))
                g.append(f'<path d="{_d([hp])}" fill="{col(op.tone, p.mat)}" clip-path="url(#{cid})"/>')
            elif isinstance(op, Gradient):
                gid = f'grad{i}_{j}'
                a = math.radians(op.angle)
                nx, ny = math.cos(a), math.sin(a)
                pts = np.vstack(p.rings)
                t = pts[:, 0] * nx + pts[:, 1] * ny
                stops = ''.join(f'<stop offset="{k / max(1, len(op.tones) - 1):.3f}" stop-color="{col(c, p.mat)}"/>'
                                for k, c in enumerate(op.tones))
                defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" '
                            f'x1="{nx * t.min():.2f}" y1="{ny * t.min():.2f}" x2="{nx * t.max():.2f}" y2="{ny * t.max():.2f}">{stops}</linearGradient>')
                g.append(f'<path d="{d}" fill="url(#{gid})" opacity="{op.opacity:.2f}" fill-rule="evenodd"{pclip}/>')
            elif isinstance(op, Rim):
                g.append(f'<path d="{d}" fill="none" stroke="{col(op.tone, p.mat)}" stroke-width="{2 * op.width:.2f}" clip-path="url(#{cid})"/>')
            elif isinstance(op, Facets):
                for quad, lvl in facet_geometry(op, p.rings, scene._light_vec(op.angle)):
                    g.append(f'<polygon points="{_pl(quad)}" fill="{col(op.tones[lvl], p.mat)}" clip-path="url(#{cid})"/>')
            elif isinstance(op, Dome):
                gid = f'dome{i}_{j}'
                cxr = (x0 + x1) / 2 + op.center[0] * (x1 - x0) / 2
                cyr = (y0 + y1) / 2 + op.center[1] * (y1 - y0) / 2
                rad = op.radius * max(x1 - x0, y1 - y0) / 2
                stops = ''.join(f'<stop offset="{k / max(1, len(op.tones) - 1):.3f}" stop-color="{col(c, p.mat)}"/>'
                                for k, c in enumerate(op.tones))
                defs.append(f'<radialGradient id="{gid}" gradientUnits="userSpaceOnUse" cx="{cxr:.2f}" cy="{cyr:.2f}" r="{rad:.2f}">{stops}</radialGradient>')
                g.append(f'<path d="{d}" fill="url(#{gid})" fill-rule="evenodd"{pclip}/>')
        for det in p.details:
            cp = f' clip-path="url(#{cid})"' if det.clip else ''
            if isinstance(det, Line):
                tag = 'polygon' if det.closed else 'polyline'
                g.append(f'<{tag} points="{_pl(det.pts)}" fill="none" stroke="{col(det.tone, p.mat)}" '
                         f'stroke-width="{det.width:.2f}" stroke-linecap="round" stroke-linejoin="round"{cp}/>')
            else:
                dd = _d(det.rings)
                if det.outline > 0:
                    g.append(f'<path d="{dd}" fill="none" stroke="{col(det.outline_tone, p.mat)}" '
                             f'stroke-width="{2 * det.outline:.2f}" stroke-linejoin="round"{cp}/>')
                op_ = f' opacity="{det.opacity:.2f}"' if det.opacity < 1 else ''
                g.append(f'<path d="{dd}" fill="{col(det.tone, p.mat)}" fill-rule="evenodd"{op_}{cp}/>')
        g.append('</g>')
        body.extend(g)
    title = scene.name.replace('&', 'and').replace('<', '').replace('>', '')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            f'<title>{title}</title><defs>{"".join(defs)}</defs>{"".join(body)}</svg>')
