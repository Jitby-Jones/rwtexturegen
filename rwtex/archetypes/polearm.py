"""Hafted weapons: spear, glaive, axe, hammer.  Horizontal, head RIGHT (vanilla spear/ikwa/zeushammer)."""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np

from .. import geom as G
from ..materials import get as getmat
from ..parts import common as C
from ..parts import melee as ML
from ..render import Bevel, Fill, Glow, Line, Part, Rim, Scene, Split
from ..styles import get as get_style
from . import register

POLE_STYLE: Dict[str, dict] = {
    'neolithic': dict(head='spear', butt='none', bands=2, mats=dict(head='tint_white', haft='wood', band='sinew', socket='sinew', butt='wood')),
    'medieval': dict(head='axe', butt='cap', bands=1, mats=dict(head='blade_white', haft='wood', band='iron_dark', socket='iron_dark', butt='iron_dark')),
    'industrial': dict(head='axe', butt='cap', bands=1, mats=dict(head='blade_white', haft='polymer', band='gunmetal', socket='gunmetal', butt='gunmetal')),
    'spacer': dict(head='hammer', butt='cap', bands=2, mats=dict(head='spacer_grey', haft='gunmetal', band='polymer', socket='polymer', butt='polymer', accent='charge_cell')),
    'ultratech': dict(head='hammer', butt='cap', bands=1, mats=dict(head='graphite', haft='steel_bright', band='graphite', socket='graphite', butt='graphite', accent='teal_steel', energy='mono_cyan')),
    'archotech': dict(head='glaive', butt='cube', bands=3, mats=dict(head='archo_olive', haft='archo_frame', band='archo_olive', socket='archo_frame', butt='archo_olive', energy='archo_yellow')),
    'imperial': dict(head='glaive', butt='cap', bands=2, mats=dict(head='mono_blade', haft='graphite', band='imperial_gold', socket='imperial_gold', butt='imperial_gold', energy='mono_edge')),
    'mechanoid': dict(head='glaive', butt='spike', bands=1, mats=dict(head='mech_pale', haft='mech_taupe', band='undersuit', socket='mech_taupe', butt='mech_taupe', energy='mech_red')),
    'anomaly': dict(head='axe', butt='spike', bands=2, mats=dict(head='bioferrite', haft='void_black', band='flesh', socket='void_black', butt='void_black', energy='glow_red')),
    'dms': dict(head='axe', butt='cap', bands=2, mats=dict(head='dms_steel', haft='dms_gunmetal', band='olive_drab', socket='dms_gunmetal', butt='dms_gunmetal')),
}
WHITE = {'blade_white', 'mono_blade', 'tint_white', 'ceramic', 'plasteel'}


def haft_part(x0, x1, yc, h, mat, st, k, name='haft', z=1) -> Part:
    p = Part(name, G.rounded(G.rect(x0, yc - h / 2, x1, yc + h / 2), [h * 0.45, 0, 0, h * 0.45]), mat, z=z)
    p.shade(Bevel(0.9 * k, 1.1 * k, angle=-90))
    return p


@register('polearm')
def polearm(style='ultratech', size: int = 128, seed: int = 0, name: str = 'polearm', *,
            head: Optional[str] = None, butt: Optional[str] = None, bands: Optional[int] = None,
            mats: Optional[dict] = None, haft_h: float = 4.5, x_start: float = 6.0, head_x: float = 86.0,
            x_tip: float = 123.0, head_h: Optional[float] = None, motif: Optional[str] = None,
            glow: Optional[str] = None, outline: Optional[float] = None, **_ignored) -> Scene:
    st = get_style(style)
    d = dict(POLE_STYLE.get(st.key, POLE_STYLE['ultratech']))
    dm = dict(d['mats'])
    dm.update(mats or {})
    head = head or d['head']
    butt = butt or d['butt']
    nb = d['bands'] if bands is None else bands
    k = size / 128.0
    yc = 64 * k
    s = Scene(size, name=name, outline=outline)
    hx = head_x * k
    xt = x_tip * k
    hh = haft_h * k
    # haft -------------------------------------------------------------------------------
    s.add(haft_part(x_start * k, hx + 4 * k, yc, hh, getmat(dm['haft']), st, k))
    for i in range(nb):
        bx = x_start * k + 10 * k + i * 9 * k
        s.add(Part(f'band{i}', C.box(bx, yc - hh * 0.75, bx + 3.2 * k, yc + hh * 0.75, st, c=0.8 * k, k=k, seed=seed + i),
                   dm['band'], z=2, shading=[Bevel(0.8 * k, 0.8 * k, angle=-90)]))
    if butt == 'cap':
        s.add(Part('butt', C.box(x_start * k - 1 * k, yc - hh * 0.8, x_start * k + 5 * k, yc + hh * 0.8, st, c=1.0 * k, k=k), dm['butt'], z=2,
                   shading=[st.bevel(k)]))
    elif butt == 'spike':
        s.add(Part('butt', G.poly([(x_start * k + 5 * k, yc - hh * 0.7), (x_start * k - 3 * k, yc), (x_start * k + 5 * k, yc + hh * 0.7)]),
                   dm['butt'], z=2, shading=[st.bevel(k)]))
    elif butt == 'cube':
        s.add(Part('butt', G.rect(x_start * k - 2 * k, yc - hh, x_start * k + 4 * k, yc + hh), dm['butt'], z=2,
                   shading=[Bevel(0.8 * k, 0.8 * k)]))
    # socket ------------------------------------------------------------------------------
    sock = C.box(hx - 6 * k, yc - hh * 0.95, hx + 3 * k, yc + hh * 0.95, st, c=1.2 * k, k=k)
    s.add(Part('socket', sock, dm['socket'], z=3, shading=[st.bevel(k), Split(at=0.6, tone='shade')]))
    hm = getmat(dm['head'])
    emat = dm.get('energy')
    # heads -------------------------------------------------------------------------------
    if head == 'spear':
        bg = ML.blade_geom('leaf', hx, xt, yc, (head_h or 10) * k, k, tip_len=12 * k)
        if st.key == 'neolithic':
            bg = ML.blade_geom('knapped', hx, xt, yc, (head_h or 11) * k, k, tip_len=10 * k, seed=seed)
        s.add(ML.blade_part(bg, hm, st, k, white=hm.name in WHITE, z=4))
    elif head == 'glaive':
        hh2 = (head_h or 13) * k
        r = G.Path().move(hx, yc - hh * 0.6).line(hx + 10 * k, yc - hh2 * 0.55).quad(xt - 10 * k, yc - hh2 * 1.0, xt, yc - hh2 * 1.25) \
            .quad(xt - 4 * k, yc - hh2 * 0.2, xt - 16 * k, yc + hh2 * 0.35).line(hx + 9 * k, yc + hh2 * 0.35) \
            .line(hx + 6 * k, yc + hh2 * 0.7).line(hx, yc + hh * 0.6).close().ring
        p = Part('head', r, hm, z=4)
        if hm.name in WHITE:
            p.shade(Bevel(1.0 * k, 1.0 * k, light_tone='#aaaaaa', shade_tone='deep', angle=-90))
            edge = G.qbezier((hx + 10 * k, yc - hh2 * 0.55), (xt - 10 * k, yc - hh2 * 1.0), (xt, yc - hh2 * 1.25))
            lower = np.vstack([G.poly([(hx + 4 * k, yc + hh2 * 0.05)]), G.qbezier((hx + 10 * k, yc - hh2 * 0.1), (xt - 12 * k, yc - hh2 * 0.5), (xt - 1 * k, yc - hh2 * 1.0)),
                               G.poly([(xt - 16 * k, yc + hh2 * 0.4), (hx + 4 * k, yc + hh2 * 0.4)])])
            p.fill(lower, 'shade')
        else:
            p.shade(st.bevel(k), Split(at=0.6, tone='shade'))
        if emat:
            edge = G.qbezier((hx + 12 * k, yc - hh2 * 0.42), (xt - 11 * k, yc - hh2 * 0.86), (xt - 3 * k, yc - hh2 * 1.05))
            p.detail(Line(edge, 1.6 * k, f'{emat}.base', mask=None))
            p.detail(Fill([G.circle(hx + 9 * k, yc + hh2 * 0.05, 2.0 * k)], f'{emat}.base', mask=None))
        s.add(p)
    elif head == 'axe':
        hh2 = (head_h or 22) * k
        ax = hx + 4 * k
        r = G.Path().move(ax - 3 * k, yc - hh * 1.1).line(ax + 8 * k, yc - hh * 1.4).quad(ax + 12 * k, yc - hh2 * 0.3, ax + 17 * k, yc - hh2 * 0.62) \
            .quad(ax + 24 * k, yc, ax + 17 * k, yc + hh2 * 0.62).quad(ax + 12 * k, yc + hh2 * 0.3, ax + 8 * k, yc + hh * 1.4).line(ax - 3 * k, yc + hh * 1.1).close().ring
        if st.key == 'anomaly':
            r = G.wobble(r, 0.9 * k, 3 * k, seed)
        p = Part('head', r, hm, z=4)
        if hm.name in WHITE:
            p.shade(Bevel(1.0 * k, 1.0 * k, light_tone='#aaaaaa', shade_tone='deep', angle=-90), Split(at=0.55, tone='shade'))
        else:
            p.shade(st.bevel(k), Split(at=0.55, tone='shade'))
        if st.key == 'dms':
            p.detail(*C.hazard_stripes(ax + 2 * k, yc - 2 * k, ax + 10 * k, yc + 2 * k, 4, k))
        s.add(p)
        # spike on top of the haft tip
        s.add(Part('spike', G.poly([(hx + 2 * k, yc - hh * 0.6), (xt - 6 * k, yc), (hx + 2 * k, yc + hh * 0.6)]), dm['socket'], z=3.5,
                   shading=[st.bevel(k)]))
    elif head == 'hammer':  # zeushammer-like block head
        hw2 = 14 * k
        hh2 = (head_h or 40) * k
        cx = xt - hw2 / 2 - 1 * k
        body = G.chamfer(G.rect(cx - hw2 / 2, yc - hh2 / 2, cx + hw2 / 2, yc + hh2 / 2), [4 * k] * 4)
        p = Part('head', body, hm, z=4).shade(st.bevel(k), Split(at=0.55, tone='shade'))
        acc = dm.get('accent', 'teal_steel')
        for sgn in (-1, 1):
            y0 = yc + sgn * hh2 * 0.18
            y1 = yc + sgn * hh2 * 0.42
            p.fill(G.chamfer(G.rect(cx - hw2 * 0.38, min(y0, y1), cx + hw2 * 0.38, max(y0, y1)), [1.5 * k] * 4), f'{acc}.base',
                   shading=[Bevel(0.8 * k, 0.8 * k)])
        core = G.circle(cx, yc, hw2 * 0.42)
        s.add(p)
        cp = Part('core', core, dm['socket'], z=5).shade(Bevel(1 * k, 1 * k))
        if emat:
            cp.detail(*C.led(cx, yc, 2.0 * k, f'{emat}.base', f'{emat}.light'))
        s.add(cp)
    else:
        raise ValueError(f'unknown polearm head {head!r}')
    g = glow or (st.glow if st.glow == 'halo' else None)
    if g == 'halo' and emat:
        s.get('head').glow = Glow(getmat(emat).tone('glow'), 2.5 * k, 0.4, 'halo')
    s.meta.update(dict(archetype='polearm', style=st.key, kind='melee', head=head))
    return s
