"""Rifle archetype (horizontal, muzzle RIGHT, bore vertically centred at y=63.5 on a 128 canvas).

Layout measured from the vanilla assault rifle / charge rifle: stock x4-34 (wedge, top at
the bore line), grip angled back under x34-46, magazine x52-66, handguard x68-104,
front sight post at x~107, barrel to x~124.
"""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np

from .. import geom as G
from ..materials import get as getmat
from ..parts import common as C
from ..render import Bevel, Fill, Glow, Line, Part, Rim, Scene, Split
from ..styles import get as get_style
from . import register

RIFLE_STYLE: Dict[str, dict] = {
    'industrial': dict(stock='fixed', receiver='ar', grip='angled', mag='curved', handguard='round', sight='carry',
                       muzzle='flash', extras=[],
                       mats=dict(stock='polymer', receiver='gunmetal', upper='gunmetal', grip='polymer', mag='gunmetal',
                                 handguard='polymer', barrel='gunmetal', sight='gunmetal', muzzle='gunmetal')),
    'spacer': dict(stock='block', receiver='block', grip='angled', mag='cells', handguard='shroud', sight='none',
                   muzzle='none', extras=['vents'],
                   mats=dict(stock='gunmetal', receiver='gunmetal', upper='spacer_grey', grip='polymer', mag='charge_cell',
                             handguard='polymer', barrel='gunmetal', sight='gunmetal', muzzle='gunmetal')),
    'ultratech': dict(stock='sleek', receiver='sleek', grip='angled', mag='cell', handguard='sleek', sight='dot',
                      muzzle='emitter', extras=['edge_line'],
                      mats=dict(stock='ceramic', receiver='ceramic', upper='graphite', grip='graphite', mag='graphite',
                                handguard='ceramic', barrel='graphite', sight='graphite', muzzle='graphite', energy='mono_cyan')),
    'archotech': dict(stock='stepped', receiver='stepped', grip='angled', mag='none', handguard='stepped', sight='none',
                      muzzle='emitter', extras=['circuit', 'fragments'],
                      mats=dict(stock='archo_olive', receiver='archo_olive', upper='archo_sage', grip='archo_frame', mag='archo_frame',
                                handguard='archo_olive', barrel='archo_frame', sight='archo_frame', muzzle='archo_frame', energy='archo_yellow')),
    'imperial': dict(stock='sleek', receiver='sleek', grip='angled', mag='cell', handguard='sleek', sight='scope',
                     muzzle='emitter', extras=['edge_line', 'gold_trim'],
                     mats=dict(stock='armor_white', receiver='armor_white', upper='graphite', grip='imperial_purple', mag='graphite',
                               handguard='armor_white', barrel='graphite', sight='imperial_gold', muzzle='imperial_gold',
                               energy='mono_cyan', trim='imperial_gold')),
    'mechanoid': dict(stock='none', receiver='wedge', grip='none', mag='none', handguard='shroud', sight='none',
                      muzzle='none', extras=['conduit', 'vents'],
                      mats=dict(stock='mech_taupe', receiver='mech_taupe', upper='mech_pale', grip='undersuit', mag='mech_taupe',
                                handguard='mech_taupe', barrel='undersuit', sight='mech_taupe', muzzle='undersuit', energy='mech_red')),
    'anomaly': dict(stock='wood', receiver='ak', grip='angled', mag='curved', handguard='round', sight='iron',
                    muzzle='spikes', extras=['ichor'],
                    mats=dict(stock='bioferrite', receiver='void_black', upper='bioferrite', grip='flesh', mag='void_black',
                              handguard='bioferrite', barrel='void_black', sight='void_black', muzzle='void_black', energy='glow_red')),
    'dms': dict(stock='skeletal', receiver='block', grip='angled', mag='box', handguard='rail', sight='scope',
                muzzle='brake', extras=['vents', 'rivets', 'bipod'],
                mats=dict(stock='dms_gunmetal', receiver='dms_gunmetal', upper='dms_steel', grip='polymer', mag='dms_olive',
                          handguard='dms_olive', barrel='dms_gunmetal', sight='dms_gunmetal', muzzle='dms_gunmetal', ammo='brass')),
    'vanilla_expanded': dict(stock='fixed', receiver='ar', grip='angled', mag='straight', handguard='rail', sight='dot',
                             muzzle='flash', extras=[],
                             mats=dict(stock='tan', receiver='tan', upper='gunmetal', grip='polymer', mag='polymer',
                                       handguard='tan', barrel='gunmetal', sight='polymer', muzzle='gunmetal')),
}
RIFLE_STYLE['medieval'] = RIFLE_STYLE['industrial']
RIFLE_STYLE['neolithic'] = RIFLE_STYLE['industrial']
RIFLE_STYLE['bionic'] = RIFLE_STYLE['spacer']


def _sb(st, k):
    return [st.bevel(k), Split(at=0.62, tone='shade')] if st.wants_split() else [st.bevel(k)]


@register('rifle')
def rifle(style='industrial', size: int = 128, seed: int = 0, name: str = 'rifle', *,
          stock: Optional[str] = None, receiver: Optional[str] = None, grip: Optional[str] = None,
          mag: Optional[str] = None, handguard: Optional[str] = None, sight: Optional[str] = None,
          muzzle: Optional[str] = None, extras: Optional[list] = None, mats: Optional[dict] = None,
          length: float = 1.0, bore_y: float = 63.5, x_muzzle: float = 124.0, mask_parts=(),
          outline: Optional[float] = None, **_ignored) -> Scene:
    st = get_style(style)
    d = dict(RIFLE_STYLE.get(st.key, RIFLE_STYLE['industrial']))
    dm = dict(d['mats'])
    dm.update(mats or {})
    stock = stock or d['stock']
    receiver = receiver or d['receiver']
    grip = grip or d['grip']
    mag = mag or d['mag']
    handguard = handguard or d['handguard']
    sight = sight or d['sight']
    muzzle = muzzle or d['muzzle']
    ex = list(d['extras'] if extras is None else extras)
    k = size / 128.0
    yb = bore_y * k
    s = Scene(size, name=name, outline=outline)
    c = st.corner_px * k
    sb = _sb(st, k)
    X = lambda v: v * k  # noqa: E731
    xm = x_muzzle * k
    emat = dm.get('energy') or st.materials.get('energy')

    def add(nm, rings, mrole, z, shading=None, **kw):
        mname = dm.get(mrole, mrole)
        mk = 'r' if (nm in mask_parts or mrole in mask_parts) else None
        p = Part(nm, rings, mname, z=z, shading=sb if shading is None else shading,
                 mask=mk if mk else 'material', **kw)
        if mk is None and getmat(mname).mask:
            p.mask = None  # only mask what the spec asks for
        s.add(p)
        return p

    # ---------------------------------------------------------------- stock
    if stock == 'fixed':
        r = C.corner_shape([(X(5), yb - X(2)), (X(35), yb - X(2)), (X(35), yb + X(7)), (X(5), yb + X(17))], st, c, k=k)
        p = add('stock', r, 'stock', 2)
        p.fill(G.rect(X(4), yb - X(3), X(8), yb + X(18)), 'shade')
    elif stock == 'skeletal':
        outer = G.chamfer(G.poly([(X(5), yb - X(3)), (X(36), yb - X(3)), (X(36), yb + X(5)), (X(9), yb + X(16)), (X(5), yb + X(16))]), X(2))
        hole = G.chamfer(G.poly([(X(11), yb + X(1.2)), (X(31), yb + X(1.2)), (X(12), yb + X(10.5))]), X(1))
        p = add('stock', [outer, hole], 'stock', 2)
        p.fill(G.rect(X(4), yb - X(4), X(8), yb + X(17)), 'deep')
    elif stock == 'wood':
        r = G.Path().move(X(5), yb - X(2)).line(X(36), yb - X(2)).line(X(36), yb + X(5)) \
            .quad(X(20), yb + X(9), X(6), yb + X(17)).line(X(5), yb + X(17)).close().ring
        p = add('stock', r, 'stock', 2)
        p.detail(*C.grain(X(8), X(33), yb + X(5), X(4), 3, k, seed))
    elif stock == 'block':
        r = G.chamfer(G.poly([(X(12), yb - X(2.5)), (X(38), yb - X(5)), (X(38), yb + X(10)), (X(20), yb + X(18)), (X(12), yb + X(18))]), c)
        p = add('stock', r, 'stock', 2)
        p.fill(G.chamfer(G.rect(X(15), yb + X(2), X(30), yb + X(6)), X(1)), 'deep')
    elif stock == 'sleek':
        r = G.Path().move(X(8), yb - X(3)).quad(X(22), yb - X(5), X(38), yb - X(4)).line(X(38), yb + X(7)) \
            .quad(X(22), yb + X(8), X(12), yb + X(16)).quad(X(6), yb + X(17), X(6), yb + X(10)).close().ring
        hole = G.rounded(G.poly([(X(16), yb + X(2)), (X(30), yb + X(1)), (X(30), yb + X(4.5)), (X(18), yb + X(8.5))]), X(2))
        add('stock', [r, hole], 'stock', 2)
    elif stock == 'stepped':
        r = G.poly([(X(8), yb - X(4)), (X(22), yb - X(4)), (X(22), yb - X(6)), (X(38), yb - X(6)), (X(38), yb + X(8)),
                    (X(22), yb + X(8)), (X(22), yb + X(14)), (X(8), yb + X(14))])
        add('stock', r, 'stock', 2, shading=[Bevel(X(1), X(1))])
    # ---------------------------------------------------------------- receiver
    rx0, rx1 = X(33), X(70)
    if receiver in ('ar', 'ak'):
        lower = C.corner_shape([(rx0, yb - X(2)), (rx1, yb - X(2)), (rx1, yb + X(6)), (X(52), yb + X(8.5)), (rx0, yb + X(8.5))], st, c, k=k)
        upper = C.corner_shape([(rx0 + X(2), yb - X(8)), (rx1 + X(1), yb - X(8)), (rx1 + X(1), yb - X(0.5)), (rx0 + X(2), yb - X(0.5))], st, c * 0.7, k=k)
        add('lower', lower, 'receiver', 4)
        up = add('upper', upper, 'upper', 5)
        up.fill(G.rect(X(50), yb - X(6), X(60), yb - X(2.5)), 'deep')               # ejection port
        up.line([(X(38), yb - X(5)), (X(46), yb - X(5))], X(1), 'light')              # charging handle line
        if receiver == 'ak':
            up.fill(G.rect(X(42), yb - X(9.5), X(66), yb - X(7.5)), 'shade')
    elif receiver == 'block':
        r = G.chamfer(G.poly([(rx0, yb - X(9)), (X(54), yb - X(13)), (X(76), yb - X(10)), (X(76), yb + X(6)), (X(58), yb + X(10)), (rx0, yb + X(10))]), c)
        p = add('receiver', r, 'receiver', 4)
        p.fill(G.chamfer(G.rect(X(40), yb - X(7), X(70), yb - X(3)), X(1)), 'upper.base' if False else 'light')
        if 'vents' in ex:
            p.detail(*C.vent_slots(X(56), yb + X(1), X(72), yb + X(4.5), 4, k))
        if 'rivets' in ex:
            p.detail(*C.rivets([(X(38), yb + X(6)), (X(48), yb + X(6))], X(1.0), 'deep', 'light'))
    elif receiver == 'sleek':
        r = G.Path().move(rx0, yb - X(6)).quad(X(52), yb - X(12), X(76), yb - X(8)).line(X(78), yb + X(4)) \
            .quad(X(60), yb + X(9), rx0, yb + X(8)).close().ring
        p = add('receiver', r, 'receiver', 4, shading=[Bevel(X(1.0), X(1.4)), Split(at=0.6, tone='shade')])
        p.line([(X(38), yb - X(2)), (X(74), yb - X(3))], X(0.9), 'shade')
    elif receiver == 'stepped':
        r = G.poly([(rx0, yb - X(8)), (X(48), yb - X(8)), (X(48), yb - X(11)), (X(70), yb - X(11)), (X(70), yb - X(7)), (X(78), yb - X(7)),
                    (X(78), yb + X(6)), (X(60), yb + X(6)), (X(60), yb + X(10)), (rx0, yb + X(10))])
        p = add('receiver', r, 'receiver', 4, shading=[Bevel(X(1), X(1))])
        p.fill(G.rect(X(50), yb - X(9), X(68), yb - X(4)), 'archo_sage.base')
        if 'circuit' in ex:
            p.detail(*C.circuit(X(36), X(74), yb - X(3), yb + X(8), k, seed=seed, n=2))
    elif receiver == 'wedge':  # mechanoid carapace
        r = G.chamfer(G.poly([(X(16), yb - X(5)), (X(40), yb - X(15)), (X(80), yb - X(9)), (X(80), yb + X(9)), (X(40), yb + X(15)), (X(16), yb + X(5))]), X(3))
        p = add('receiver', r, 'receiver', 4, shading=[st.bevel(k), Split(at=0.5, tone='shade')])
        p.line([(X(22), yb), (X(76), yb)], X(1.4), 'deep')
        if 'conduit' in ex:
            p.line([(X(26), yb - X(0.4)), (X(74), yb - X(0.4))], X(1.0), 'mech_conduit.base', mask=None)
        if 'vents' in ex:
            p.detail(*C.vent_slots(X(30), yb - X(10), X(50), yb - X(6.5), 4, k))
            p.detail(*C.vent_slots(X(30), yb + X(6.5), X(50), yb + X(10), 4, k))
    # ---------------------------------------------------------------- grip + trigger guard
    if grip == 'angled':
        gp = C.corner_shape([(X(38), yb + X(6)), (X(47), yb + X(6)), (X(43), yb + X(24)), (X(34), yb + X(23))], st, X(1.5), k=k)
        g = add('grip', gp, 'grip', 3)
        if st.key in ('industrial', 'vanilla_expanded', 'dms'):
            g.detail(*C.ring_lines(X(36), X(44), yb + X(15), X(6), 2, X(0.7), 'light'))
        tg = [G.rounded(G.poly([(X(46), yb + X(7)), (X(56), yb + X(7)), (X(56), yb + X(14)), (X(46), yb + X(14))]), X(2.5)),
              G.rounded(G.poly([(X(47.5), yb + X(8)), (X(54.5), yb + X(8)), (X(54.5), yb + X(12.2)), (X(47.5), yb + X(12.2))]), X(1.6))]
        add('trigger_guard', tg, 'receiver', 3.5, shading=[Bevel(X(0.8), X(0.8))])
    # ---------------------------------------------------------------- magazine
    if mag == 'curved':
        r = G.Path().move(X(55), yb + X(6)).line(X(65), yb + X(6)).quad(X(66), yb + X(20), X(70), yb + X(31)) \
            .line(X(61), yb + X(33)).quad(X(56), yb + X(21), X(55), yb + X(6)).close().ring
        p = add('mag', r, 'mag', 3.4)
        p.detail(*C.ring_lines(X(57), X(67), yb + X(22), X(2.5), 2, X(0.7), 'deep'))
    elif mag == 'straight':
        add('mag', C.corner_shape([(X(55), yb + X(6)), (X(64), yb + X(6)), (X(64), yb + X(28)), (X(55), yb + X(28))], st, X(1.2), k=k), 'mag', 3.4)
    elif mag == 'box':
        p = add('mag', G.chamfer(G.rect(X(53), yb + X(6), X(69), yb + X(22)), X(2)), 'mag', 3.4)
        p.fill(G.rect(X(55), yb + X(9), X(67), yb + X(11)), 'deep')
        if dm.get('ammo'):
            s.add(Part('ammo', G.poly([(X(66), yb + X(6)), (X(71), yb + X(4)), (X(74), yb + X(8)), (X(69), yb + X(10))]), dm['ammo'], z=3.3,
                       shading=[Bevel(X(0.8), X(0.8))]))
    elif mag in ('cell', 'cells'):
        n = 2 if mag == 'cells' else 1
        cy0 = yb + (X(8) if receiver in ('block', 'wedge', 'stepped') else X(4))
        for i in range(n):
            x0 = X(55) + i * X(10)
            p = add(f'cell{i}', G.chamfer(G.rect(x0, cy0, x0 + X(8.5), cy0 + X(11)), X(1.5)), 'mag', 3.4)
            if emat and mag == 'cell':
                p.line([(x0 + X(2), cy0 + X(5.5)), (x0 + X(6.5), cy0 + X(5.5))], X(1.8), f'{emat}.base', mask=None)
    elif mag == 'drum':
        add('mag', G.circle(X(60), yb + X(15), X(9)), 'mag', 3.4)
    # ---------------------------------------------------------------- handguard
    hx0, hx1 = X(68), X(104) * length
    if handguard == 'round':
        p = add('handguard', C.corner_shape([(hx0, yb - X(5)), (hx1, yb - X(5)), (hx1, yb + X(5.5)), (hx0, yb + X(6))], st, X(2), k=k), 'handguard', 3.6)
        p.detail(*C.ring_lines(hx0 + X(2), hx1 - X(2), yb, X(4), 3, X(0.8), 'light'))
    elif handguard == 'rail':
        p = add('handguard', G.chamfer(G.rect(hx0, yb - X(5), hx1, yb + X(5)), X(1.5)), 'handguard', 3.6)
        p.detail(*C.vent_slots(hx0 + X(3), yb - X(1.5), hx1 - X(3), yb + X(1.5), 5, k, vertical=True, tone='deep'))
        p.fill(G.rect(hx0, yb - X(6.5), hx1, yb - X(5)), 'deep')
    elif handguard == 'shroud':
        hx1 = X(118) * length
        r = G.chamfer(G.poly([(X(70), yb - X(8)), (hx1, yb - X(5)), (hx1, yb + X(5)), (X(70), yb + X(8))]), X(2.5))
        p = add('handguard', r, 'handguard', 3.6, shading=[st.bevel(k)])
        p.detail(*C.vent_slots(X(76), yb - X(3), hx1 - X(6), yb + X(2.5), 5, k, tone='black'))
    elif handguard == 'sleek':
        hx1 = X(112) * length
        r = G.Path().move(X(70), yb - X(7)).quad(X(92), yb - X(7), hx1, yb - X(3)).line(hx1, yb + X(3)) \
            .quad(X(92), yb + X(7), X(70), yb + X(7)).close().ring
        p = add('handguard', r, 'handguard', 3.6, shading=[Bevel(X(1.0), X(1.4)), Split(at=0.62, tone='shade')])
        if 'edge_line' in ex and emat:
            p.line([(X(74), yb - X(1)), (hx1 - X(4), yb - X(0.5))], X(1.6), f'{emat}.base', mask=None)
            p.fill(G.circle(X(74), yb - X(1), X(1.8)), f'{emat}.shade', mask=None)
        if 'gold_trim' in ex:
            p.line([(X(71), yb + X(5.4)), (X(100), yb + X(4.2))], X(1.4), 'imperial_gold.base', mask=None)
    elif handguard == 'stepped':
        hx1 = X(116) * length
        r = G.poly([(X(76), yb - X(6)), (X(96), yb - X(6)), (X(96), yb - X(4)), (hx1, yb - X(4)), (hx1, yb + X(4)), (X(96), yb + X(4)),
                    (X(96), yb + X(6)), (X(76), yb + X(6))])
        p = add('handguard', r, 'handguard', 3.6, shading=[Bevel(X(1), X(1))])
        if 'circuit' in ex:
            p.line([(X(80), yb), (X(110), yb)], X(1), 'archo_yellow.base', mask=None)
            p.fill(G.circle(X(110), yb, X(1.4)), 'archo_yellow.light', mask=None)
    # ---------------------------------------------------------------- barrel, sight, muzzle
    if handguard not in ('shroud', 'stepped') or muzzle not in ('none',):
        bx0 = hx1 - X(1)
        add('barrel', G.rect(bx0, yb - X(1.6), xm - X(2), yb + X(1.6)), 'barrel', 3.0, shading=[Bevel(X(0.6), X(0.6))])
    if sight == 'carry':
        r = C.corner_shape([(X(40), yb - X(13)), (X(64), yb - X(13)), (X(64), yb - X(8)), (X(40), yb - X(8))], st, X(1.2), k=k)
        p = add('carry', r, 'sight', 6)
        p.fill(G.rect(X(46), yb - X(11.5), X(60), yb - X(9.5)), 'deep')
        add('front_sight', G.poly([(X(105), yb - X(1)), (X(105), yb - X(10)), (X(108), yb - X(10)), (X(110), yb - X(1))]), 'sight', 2.9)
    elif sight == 'iron':
        add('rear_sight', G.rect(X(40), yb - X(11), X(44), yb - X(7.5)), 'sight', 6)
        add('front_sight', G.poly([(X(104), yb - X(1)), (X(105), yb - X(8)), (X(107), yb - X(8)), (X(108), yb - X(1))]), 'sight', 2.9)
    elif sight == 'dot':
        p = add('optic', G.chamfer(G.rect(X(44), yb - X(14), X(58), yb - X(8)), X(1.5)), 'sight', 6)
        p.fill(G.rect(X(56), yb - X(12.5), X(58.5), yb - X(9.5)), 'lens_teal.light', mask=None)
        add('mount', G.rect(X(47), yb - X(9), X(55), yb - X(7)), 'sight', 5.9)
    elif sight == 'scope':
        tube = G.capsule(X(38), yb - X(13), X(66), yb - X(13), X(3))
        add('scope', tube, 'sight', 6)
        add('scope_bell', G.chamfer(G.rect(X(62), yb - X(17), X(70), yb - X(9)), X(1.5)), 'sight', 6.1)
        add('mount', G.rect(X(46), yb - X(10.5), X(58), yb - X(8)), 'sight', 5.9)
    if muzzle == 'flash':
        p = add('muzzle', G.rect(xm - X(6), yb - X(2.6), xm, yb + X(2.6)), 'muzzle', 3.1, shading=[Bevel(X(0.7), X(0.7))])
        p.detail(*C.ring_lines(xm - X(6), xm, yb, X(2.2), 2, X(0.7), 'deep'))
    elif muzzle == 'brake':
        p = add('muzzle', G.chamfer(G.rect(xm - X(8), yb - X(3.5), xm, yb + X(3.5)), X(1)), 'muzzle', 3.1)
        p.detail(*C.vent_slots(xm - X(7), yb - X(2.5), xm - X(1), yb + X(2.5), 2, k))
    elif muzzle == 'emitter':
        p = add('muzzle', G.rounded(G.rect(xm - X(7), yb - X(3.4), xm, yb + X(3.4)), X(1.8)), 'muzzle', 3.1,
                shading=[Bevel(X(0.8), X(0.8))])
        if emat:
            p.fill(G.rounded(G.rect(xm - X(2.5), yb - X(2.2), xm - X(0.5), yb + X(2.2)), X(0.8)), f'{emat}.light', mask=None)
    elif muzzle == 'spikes':
        add('muzzle', G.poly([(xm - X(7), yb - X(2)), (xm - X(2), yb - X(6)), (xm - X(3), yb - X(1.5)), (xm, yb), (xm - X(3), yb + X(1.5)),
                              (xm - X(2), yb + X(6)), (xm - X(7), yb + X(2))]), 'muzzle', 3.1)
    # ---------------------------------------------------------------- extras
    if 'bipod' in ex:
        for i, dx in enumerate((0, X(4))):
            add(f'bipod{i}', G.poly([(X(92) + dx, yb + X(5)), (X(94.5) + dx, yb + X(5)), (X(90) + dx, yb + X(22)), (X(87.5) + dx, yb + X(22))]),
                'barrel', 2.5 + i * 0.01, shading=[Bevel(X(0.6), X(0.6))])
    if 'ichor' in ex and emat:
        rp = s.get('upper') if any(p.name == 'upper' for p in s.parts) else s.parts[-1]
        rp.line([(X(36), yb - X(4)), (X(48), yb - X(3.2)), (X(56), yb - X(4.4)), (X(66), yb - X(3.5))], X(1.2), f'{emat}.base', mask=None)
    if 'fragments' in ex:
        s.add(Part('fragment', G.rect(X(100), yb - X(12), X(105), yb - X(8)), dm['receiver'], z=7, shading=[Bevel(X(0.8), X(0.8))]))
        s.add(Part('fragment2', G.rect(X(108), yb + X(7), X(112), yb + X(10)), dm['receiver'], z=7, shading=[Bevel(X(0.8), X(0.8))]))
    if st.glow == 'halo' and emat:
        mz = [p for p in s.parts if p.name == 'muzzle']
        if mz:
            mz[0].glow = Glow(getmat(emat).tone('glow'), X(2.5), 0.45, 'halo')
    s.meta.update(dict(archetype='rifle', style=st.key, kind='ranged', stock=stock, receiver=receiver, mag=mag,
                       handguard=handguard, sight=sight, muzzle=muzzle))
    return s
