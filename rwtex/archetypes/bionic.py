"""Bionic body-part items in the *Bionic Icons* language (AUTOMATIC1111/BionicIcons, MIT).

A tier-coloured rounded case seen from the front, a darker lid band along the bottom with a
glowing tier strip, and an engraved organ pictogram on the face.  Tier colours follow the
vanilla HealthItem tints (prosthetic (154,124,104), bionic (189,169,118), archotech
(155,165,148)) and Bionic Icons' strip colours.

``mask=True`` instead produces a neutral case plus a CutoutComplex mask (R = case,
G = pictogram) so the game can tint per tier like Bionic Icons does.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

import numpy as np

from .. import geom as G
from ..materials import get as getmat
from ..parts import common as C
from ..render import Bevel, Fill, Glow, Line, Part, Scene, Split
from ..styles import get as get_style
from . import register


def _P(pts, x0, y0, w, h):
    return np.array([(x0 + u * w, y0 + v * h) for u, v in pts])


# pictograms in a unit box (0..1), drawn as solid silhouettes ---------------------------------
def pic_arm(b):
    return [G.spline(_P([(0.08, 0.95), (0.05, 0.55), (0.22, 0.3), (0.45, 0.32), (0.55, 0.42), (0.68, 0.18), (0.62, 0.05),
                         (0.78, 0.02), (0.9, 0.18), (0.88, 0.38), (0.7, 0.6), (0.5, 0.66), (0.42, 0.95)], *b))]


def pic_leg(b):
    return [G.spline(_P([(0.32, 0.02), (0.62, 0.02), (0.62, 0.38), (0.55, 0.55), (0.58, 0.8), (0.9, 0.86), (0.92, 0.98),
                         (0.38, 0.98), (0.38, 0.62), (0.3, 0.42)], *b))]


def pic_hand(b):
    x0, y0, w, h = b
    palm = G.rounded(_P([(0.22, 0.45), (0.78, 0.45), (0.74, 0.95), (0.28, 0.95)], *b), 0.12 * w)
    rings = [palm]
    for i, (u, top) in enumerate(((0.28, 0.12), (0.42, 0.04), (0.56, 0.06), (0.7, 0.16))):
        rings.append(G.capsule(x0 + u * w, y0 + top * h, x0 + u * w, y0 + 0.55 * h, 0.065 * w))
    rings.append(G.capsule(x0 + 0.22 * w, y0 + 0.7 * h, x0 + 0.06 * w, y0 + 0.45 * h, 0.07 * w))
    return rings


def pic_eye(b):
    x0, y0, w, h = b
    outer = G.Path().move(x0 + 0.02 * w, y0 + 0.5 * h).quad(x0 + 0.5 * w, y0 + 0.02 * h, x0 + 0.98 * w, y0 + 0.5 * h) \
        .quad(x0 + 0.5 * w, y0 + 0.98 * h, x0 + 0.02 * w, y0 + 0.5 * h).close().ring
    inner = G.Path().move(x0 + 0.14 * w, y0 + 0.5 * h).quad(x0 + 0.5 * w, y0 + 0.16 * h, x0 + 0.86 * w, y0 + 0.5 * h) \
        .quad(x0 + 0.5 * w, y0 + 0.84 * h, x0 + 0.14 * w, y0 + 0.5 * h).close().ring
    iris = G.circle(x0 + 0.5 * w, y0 + 0.5 * h, 0.2 * min(w, h))
    return [outer, inner, iris]


def pic_heart(b):
    return [G.spline(_P([(0.5, 0.95), (0.12, 0.6), (0.1, 0.32), (0.25, 0.15), (0.42, 0.2), (0.48, 0.05), (0.62, 0.05),
                         (0.6, 0.18), (0.78, 0.18), (0.9, 0.35), (0.86, 0.62)], *b))]


def pic_lung(b):
    x0, y0, w, h = b
    left = G.spline(_P([(0.45, 0.3), (0.42, 0.92), (0.12, 0.95), (0.06, 0.6), (0.2, 0.22), (0.38, 0.2)], *b))
    right = G.mirror_x(left, x0 + 0.5 * w)
    trach = G.rounded(G.rect(x0 + 0.45 * w, y0 + 0.02 * h, x0 + 0.55 * w, y0 + 0.45 * h), 0.03 * w)
    return [left, right, trach]


def pic_spine(b):
    x0, y0, w, h = b
    out = []
    for i in range(5):
        y = y0 + (0.04 + i * 0.19) * h
        out.append(G.rounded(G.rect(x0 + 0.3 * w, y, x0 + 0.7 * w, y + 0.13 * h), 0.04 * w))
        out.append(G.rounded(G.rect(x0 + 0.15 * w, y + 0.04 * h, x0 + 0.85 * w, y + 0.09 * h), 0.02 * w))
    return out


def pic_kidney(b):
    return [G.spline(_P([(0.55, 0.05), (0.85, 0.2), (0.88, 0.75), (0.6, 0.95), (0.32, 0.85), (0.38, 0.6), (0.5, 0.5),
                         (0.36, 0.38), (0.3, 0.15)], *b))]


def pic_liver(b):
    return [G.spline(_P([(0.05, 0.35), (0.35, 0.12), (0.95, 0.15), (0.85, 0.4), (0.55, 0.75), (0.3, 0.85), (0.1, 0.65)], *b))]


def pic_stomach(b):
    return [G.spline(_P([(0.6, 0.02), (0.72, 0.02), (0.72, 0.25), (0.9, 0.45), (0.8, 0.85), (0.45, 0.95), (0.15, 0.82),
                         (0.2, 0.7), (0.45, 0.72), (0.55, 0.5), (0.58, 0.25)], *b))]


def pic_jaw(b):
    x0, y0, w, h = b
    outer = G.Path().move(x0 + 0.05 * w, y0 + 0.15 * h).line(x0 + 0.2 * w, y0 + 0.15 * h).quad(x0 + 0.5 * w, y0 + 0.75 * h, x0 + 0.8 * w, y0 + 0.15 * h) \
        .line(x0 + 0.95 * w, y0 + 0.15 * h).quad(x0 + 0.9 * w, y0 + 0.95 * h, x0 + 0.5 * w, y0 + 0.95 * h) \
        .quad(x0 + 0.1 * w, y0 + 0.95 * h, x0 + 0.05 * w, y0 + 0.15 * h).close().ring
    return [outer]


def pic_brain(b):
    return [G.wobble(G.spline(_P([(0.1, 0.55), (0.12, 0.25), (0.35, 0.08), (0.65, 0.08), (0.9, 0.25), (0.92, 0.55),
                                  (0.75, 0.82), (0.5, 0.78), (0.3, 0.85)], *b)), 0.03 * b[2], 0.1 * b[2], 3)]


def pic_ear(b):
    x0, y0, w, h = b
    return [G.Path().move(x0 + 0.3 * w, y0 + 0.3 * h).quad(x0 + 0.35 * w, y0 + 0.02 * h, x0 + 0.65 * w, y0 + 0.05 * h)
            .quad(x0 + 0.95 * w, y0 + 0.15 * h, x0 + 0.8 * w, y0 + 0.55 * h).quad(x0 + 0.65 * w, y0 + 0.75 * h, x0 + 0.65 * w, y0 + 0.95 * h)
            .line(x0 + 0.45 * w, y0 + 0.95 * h).quad(x0 + 0.45 * w, y0 + 0.65 * h, x0 + 0.62 * w, y0 + 0.48 * h)
            .quad(x0 + 0.72 * w, y0 + 0.25 * h, x0 + 0.55 * w, y0 + 0.22 * h).quad(x0 + 0.45 * w, y0 + 0.25 * h, x0 + 0.46 * w, y0 + 0.35 * h).close().ring]


def pic_generic(b):
    x0, y0, w, h = b
    return [G.rect(x0 + 0.38 * w, y0 + 0.1 * h, x0 + 0.62 * w, y0 + 0.9 * h), G.rect(x0 + 0.1 * w, y0 + 0.38 * h, x0 + 0.9 * w, y0 + 0.62 * h)]


PICTOGRAMS: Dict[str, Callable] = {
    'arm': pic_arm, 'shoulder': pic_arm, 'leg': pic_leg, 'hand': pic_hand, 'eye': pic_eye, 'heart': pic_heart,
    'lung': pic_lung, 'spine': pic_spine, 'kidney': pic_kidney, 'liver': pic_liver, 'stomach': pic_stomach,
    'jaw': pic_jaw, 'brain': pic_brain, 'ear': pic_ear, 'generic': pic_generic,
}


@register('bionic_part')
def bionic_part(style='bionic', size: int = 64, seed: int = 0, name: str = 'BionicPart', *, tier: str = 'bionic',
                part: str = 'arm', mask: bool = False, case: Optional[str] = None, strip: Optional[str] = None,
                outline: Optional[float] = None, **_ignored) -> Scene:
    st = get_style(style)
    tiers = st.tiers or get_style('bionic').tiers
    t = dict(tiers.get(tier, tiers['bionic']))
    case_m = getmat(case or ('tint_white' if mask else t['case']))
    strip_m = strip or t.get('strip')
    k = size / 64.0
    s = Scene(size, name=name, outline=outline if outline is not None else 2.2 * k, inner=1.0 * k)
    X = lambda v: v * k  # noqa: E731
    body = G.rounded(G.rect(X(7), X(9), X(57), X(55)), X(7))
    cp = Part('case', body, case_m, z=1, mask='r' if mask else None,
              shading=[Bevel(X(1.4), X(1.4)), Split(at=0.94, tone='shade')])
    s.add(cp)
    lid = G.rounded(G.rect(X(7), X(42), X(57), X(55)), [0, 0, X(7), X(7)])
    lp = Part('lid', lid, case_m, z=2, tone='shade', mask='r' if mask else None, outline=X(0.9),
              shading=[Bevel(X(1.0), X(1.2), light_tone='base', shade_tone='deep')])
    lp.line([(X(9), X(48.8)), (X(55), X(48.8))], X(1.0), 'deep')
    s.add(lp)
    if strip_m:
        sp = Part('strip', G.rounded(G.rect(X(10), X(43.6), X(54), X(46.6)), X(1.2)), strip_m, z=3, outline=None, mask=None,
                  shading=[Bevel(X(0.6), 0, light_tone='light')])
        sp.glow = Glow(None, X(1.6), 0.5, 'bloom')
        s.add(sp)
    if t.get('traces'):
        cp.detail(Line(G.poly([(X(12), X(37)), (X(22), X(37)), (X(22), X(33)), (X(30), X(33))]), X(1.0), f'{t["traces"]}.base', mask=None),
                  Fill([G.circle(X(30), X(33), X(1.3))], f'{t["traces"]}.light', mask=None))
    # pictogram: engraved = darker fill, shadow on the lit side, highlight on the far side
    fn = PICTOGRAMS.get(part, pic_generic)
    rings = fn((X(18), X(13), X(28), X(27)))
    tone = (0.25, 0.25, 0.25)
    dark = tuple(c * 0.55 for c in case_m.base) if not mask else tuple(c * 0.25 for c in case_m.base)
    ico = Fill(rings, dark, mask='g' if mask else None,
               shading=[Bevel(X(0.9), X(0.9), light_tone=tuple(c * 0.35 for c in case_m.base),
                              shade_tone=case_m.light, angle=None)])
    cp.detail(ico)
    s.meta.update(dict(archetype='bionic_part', style=st.key, kind='item', tier=tier, part=part, mask=mask))
    return s
