"""Colour helpers. All colours are handled internally as float RGB tuples in 0..1."""
from __future__ import annotations

import colorsys
from typing import Iterable, Sequence, Tuple, Union

RGB = Tuple[float, float, float]
ColorLike = Union[str, Sequence[float], Sequence[int]]


def rgb(c: ColorLike) -> RGB:
    """Parse '#rrggbb', '#rgb', (r,g,b) in 0-255 ints or 0-1 floats."""
    if isinstance(c, str):
        s = c.strip().lstrip('#')
        if len(s) == 3:
            s = ''.join(ch * 2 for ch in s)
        if len(s) != 6:
            raise ValueError(f'bad colour {c!r}')
        return tuple(int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]
    vals = list(c)[:3]
    if any(isinstance(v, int) and v > 1 for v in vals) or any(v > 1.0 for v in vals):
        return tuple(max(0.0, min(1.0, v / 255.0)) for v in vals)  # type: ignore[return-value]
    return tuple(float(v) for v in vals)  # type: ignore[return-value]


def to_hex(c: ColorLike) -> str:
    r, g, b = rgb(c)
    return '#%02x%02x%02x' % tuple(int(round(max(0, min(1, v)) * 255)) for v in (r, g, b))


def to255(c: ColorLike) -> Tuple[int, int, int]:
    r, g, b = rgb(c)
    return tuple(int(round(max(0, min(1, v)) * 255)) for v in (r, g, b))  # type: ignore[return-value]


def mix(a: ColorLike, b: ColorLike, t: float) -> RGB:
    a, b = rgb(a), rgb(b)
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))  # type: ignore[return-value]


def mul(a: ColorLike, b: ColorLike) -> RGB:
    a, b = rgb(a), rgb(b)
    return tuple(a[i] * b[i] for i in range(3))  # type: ignore[return-value]


def shift_hsv(c: ColorLike, dh: float = 0.0, ds: float = 0.0, dv: float = 0.0) -> RGB:
    h, s, v = colorsys.rgb_to_hsv(*rgb(c))
    h = (h + dh) % 1.0
    s = max(0.0, min(1.0, s + ds))
    v = max(0.0, min(1.0, v + dv))
    return colorsys.hsv_to_rgb(h, s, v)


def luminance(c: ColorLike) -> float:
    r, g, b = rgb(c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ramp(base: ColorLike, light: float = 0.16, shade: float = -0.14, deep: float = -0.30,
         hue_shift: float = 0.0) -> dict:
    """Build a RimWorld-style 4-tone ramp from a base colour.

    Vanilla uses near-pure value steps (greys: #4d4d4d / #666666 / #919191) with only a
    slight saturation increase in shadows for coloured materials.  ``hue_shift`` nudges
    lights warm/cool if a material wants it.
    """
    b = rgb(base)
    _, s, _ = colorsys.rgb_to_hsv(*b)
    sat_bump = 0.06 if s > 0.12 else 0.0
    return {
        'base': b,
        'light': shift_hsv(b, hue_shift, -sat_bump * 0.5, light),
        'shade': shift_hsv(b, -hue_shift * 0.5, sat_bump, shade),
        'deep': shift_hsv(b, -hue_shift, sat_bump * 1.5, deep),
    }


def cutout_complex(tex_rgb, mask_rgb, color_one: ColorLike, color_two: ColorLike = (1, 1, 1)):
    """Approximate RimWorld's CutoutComplex tinting (numpy arrays in 0..1).

    out = lerp(lerp(tex, tex*colorOne, mask.r), tex*colorTwo, mask.g)
    """
    import numpy as np
    c1 = np.array(rgb(color_one), dtype=np.float32)
    c2 = np.array(rgb(color_two), dtype=np.float32)
    mr = mask_rgb[..., 0:1]
    mg = mask_rgb[..., 1:2]
    out = tex_rgb * (1 - mr) + tex_rgb * c1 * mr
    out = out * (1 - mg) + tex_rgb * c2 * mg
    return out


def parse_many(cs: Iterable[ColorLike]):
    return [rgb(c) for c in cs]
