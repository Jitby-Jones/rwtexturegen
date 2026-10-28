"""Bows and crossbows - the neolithic/medieval answer to 'ranged weapon'.

Vanilla bows are drawn upright (limbs vertical, belly facing right, string on the left)
and pointing right; crossbows are horizontal like rifles with the prod at the front.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from .. import geom as G
from ..parts import common as C
from ..render import Bevel, Fill, Line, Part, Scene, Split
from ..styles import get as get_style
from . import register

BOW_STYLE = {
    'neolithic': dict(kind='recurve', mats=dict(limb='wood', grip='hide', string='sinew', tip='bone')),
    'medieval': dict(kind='crossbow', mats=dict(limb='blade_white', stock='wood', grip='leather', string='sinew', tip='iron_dark')),
    'industrial': dict(kind='compound', mats=dict(limb='polymer', stock='gunmetal', grip='rubber', string='sinew', tip='gunmetal')),
}


def _limb(cx, cy, height, depth, thick, kind, k):
    """Return the bow stave ring (vertical) - belly faces right."""
    top = cy - height / 2
    bot = cy + height / 2
    if kind == 'long':
        outer = G.qbezier((cx - depth * 0.15, top), (cx + depth * 1.25, cy), (cx - depth * 0.15, bot))
        inner = G.qbezier((cx - depth * 0.15 - thick * 0.3, bot - thick), (cx + depth * 1.25 - thick * 1.6, cy), (cx - depth * 0.15 - thick * 0.3, top + thick))
    elif kind == 'recurve':
        outer = np.vstack([G.qbezier((cx - depth * 0.35, top - 1 * k), (cx + depth * 0.15, top + height * 0.05), (cx + depth * 0.55, top + height * 0.22)),
                           G.bezier((cx + depth * 0.55, top + height * 0.22), (cx + depth * 0.9, cy - height * 0.15), (cx + depth * 0.2, cy - height * 0.05), (cx + depth * 0.2, cy))[1:],
                           G.bezier((cx + depth * 0.2, cy), (cx + depth * 0.2, cy + height * 0.05), (cx + depth * 0.9, cy + height * 0.15), (cx + depth * 0.55, bot - height * 0.22))[1:],
                           G.qbezier((cx + depth * 0.55, bot - height * 0.22), (cx + depth * 0.15, bot - height * 0.05), (cx - depth * 0.35, bot + 1 * k))[1:]])
        inner = outer[::-1] + np.array([-thick * 0.9, 0])
        inner[0] = outer[-1] + np.array([-thick * 0.6, -thick * 0.2])
        inner[-1] = outer[0] + np.array([-thick * 0.6, thick * 0.2])
    else:  # short D bow
        outer = G.qbezier((cx - depth * 0.1, top), (cx + depth * 1.1, cy), (cx - depth * 0.1, bot))
        inner = G.qbezier((cx - depth * 0.1 - thick * 0.4, bot - thick * 0.8), (cx + depth * 1.1 - thick * 1.7, cy), (cx - depth * 0.1 - thick * 0.4, top + thick * 0.8))
    return np.vstack([outer, inner])


@register('bow')
def bow(style='neolithic', size: int = 128, seed: int = 0, name: str = 'bow', *, kind: Optional[str] = None,
        mats: Optional[dict] = None, outline: Optional[float] = None, **_ignored) -> Scene:
    st = get_style(style)
    d = dict(BOW_STYLE.get(st.key, BOW_STYLE['neolithic']))
    dm = dict(d['mats'])
    dm.update(mats or {})
    kind = kind or d['kind']
    k = size / 128.0
    X = lambda v: v * k  # noqa: E731
    s = Scene(size, name=name, outline=outline)
    yc = X(64)
    if kind in ('short', 'recurve', 'long'):
        height = X({'short': 92, 'recurve': 104, 'long': 118}[kind])
        depth = X({'short': 36, 'recurve': 40, 'long': 30}[kind])
        cx = X(52)
        stave = _limb(cx, yc, height, depth, X(5.5), kind, k)
        p = Part('stave', stave, dm['limb'], z=2, shading=[Bevel(X(1.0), X(1.4), angle=-160)])
        if st.key == 'neolithic':
            p.detail(*C.grain(cx, cx + depth * 0.6, yc, X(18), 2, k, seed))
        s.add(p)
        top, bot = yc - height / 2, yc + height / 2
        s.add(Part('string', G.capsule(cx - depth * 0.33, top + X(1), cx - depth * 0.33, bot - X(1), X(0.7)), dm['string'], z=1,
                   outline=None, silhouette=True))
        gx = cx + depth * (0.18 if kind == 'recurve' else 0.42)
        g = Part('grip', G.rounded(G.rect(gx - X(3.6), yc - X(7), gx + X(3.6), yc + X(7)), X(1.5)), dm['grip'], z=3,
                 shading=[Bevel(X(0.8), X(1.0), angle=-160)])
        g.detail(*C.diag_bands(gx - X(3), gx + X(3), yc, X(6), 3, X(1.4), X(0.8), 'sinew.base'))
        s.add(g)
    elif kind in ('crossbow', 'compound'):
        sx0, sx1 = X(8), X(100)
        stock = G.Path().move(sx0, yc - X(2)).line(sx1, yc - X(3)).line(sx1, yc + X(3)).line(X(52), yc + X(4)) \
            .line(X(44), yc + X(16)).line(X(36), yc + X(15)).line(X(38), yc + X(5)).quad(X(20), yc + X(7), sx0, yc + X(14)).close().ring
        p = Part('stock', stock, dm.get('stock', 'wood'), z=2, shading=[st.bevel(k), Split(at=0.6, tone='shade')])
        if dm.get('stock', 'wood').startswith('wood'):
            p.detail(*C.grain(X(12), X(90), yc + X(1), X(2), 3, k, seed))
        s.add(p)
        px = X(100)
        prod = G.Path().move(px, yc - X(3)).quad(px + X(10), yc - X(22), px + X(4), yc - X(44)).line(px + X(1), yc - X(43)) \
            .quad(px + X(5), yc - X(22), px - X(3), yc - X(3)).close().ring
        prod2 = G.mirror_y(prod, yc)
        for i, r in enumerate((prod, prod2)):
            s.add(Part(f'prod{i}', r, dm['limb'], z=3, shading=[Bevel(X(1.0), X(1.2), angle=-160)]))
        s.add(Part('string', G.poly([(px + X(2.6), yc - X(43)), (X(70), yc - X(1)), (X(70), yc + X(1)), (px + X(2.6), yc + X(43)),
                                     (px + X(3.8), yc + X(42.5)), (X(71.5), yc), (px + X(3.8), yc - X(42.5))]), dm['string'], z=1.5, outline=None))
        s.add(Part('bolt', G.rect(X(70), yc - X(4.6), X(110), yc - X(3)), 'iron_dark', z=4, shading=[Bevel(X(0.5), X(0.5))]))
        s.add(Part('nose', G.chamfer(G.rect(X(96), yc - X(4.5), X(106), yc + X(4.5)), X(1.2)), dm.get('tip', 'iron_dark'), z=4,
                   shading=[st.bevel(k)]))
        if kind == 'compound':
            for sgn in (-1, 1):
                s.add(Part(f'cam{sgn}', G.circle(px + X(4), yc + sgn * X(42), X(4)), 'gunmetal', z=4, shading=[Bevel(X(0.8), X(0.8))]))
    else:
        raise ValueError(f'unknown bow kind {kind!r}')
    s.meta.update(dict(archetype='bow', style=st.key, kind='ranged', bow=kind))
    return s
