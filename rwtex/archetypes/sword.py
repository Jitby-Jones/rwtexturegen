"""Sword archetype (one-handed blade, horizontal, tip right).

The ``ultratech`` defaults reproduce the vanilla monosword geometry measured from the
in-game 128px texture (grip x7-37, guard x38-43.5 / y55-73, blade y57-71, flare at x110,
point at x122.5, cyan line y62-66 from a bulb at x48).
"""
from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

from .. import geom as G
from ..materials import get as getmat
from ..parts import common as C
from ..parts import melee as ML
from ..render import Bevel, Fill, Glow, Line, Part, Scene, Split
from ..styles import get as get_style
from . import register

# per-style sword grammar ------------------------------------------------------------------
SWORD_STYLE: Dict[str, dict] = {
    'neolithic': dict(blade='knapped', guard='none', grip='lashed', pommel='knob', motif='none',
                      blade_h=15, grip_len=31, pommel_s=9, x_tip=118,
                      mats=dict(blade='tint_white', guard='bone', grip='wood', wrap='sinew', pommel='wood')),
    'medieval': dict(blade='straight', guard='cross', grip='wrapped', pommel='round', motif='fuller',
                     blade_h=13, grip_len=23, guard_w=5, guard_h=28, pommel_s=10, tip_len=15, taper=0.2,
                     mats=dict(blade='blade_white', guard='iron_dark', grip='leather', wrap='leather', pommel='iron_dark')),
    'industrial': dict(blade='clip', guard='finger', grip='riveted', pommel='cap', motif='none',
                       blade_h=15, grip_len=30, guard_w=4, guard_h=17, pommel_s=8, tip_len=13,
                       mats=dict(blade='blade_white', guard='gunmetal', grip='polymer', pommel='gunmetal')),
    'spacer': dict(blade='tanto', guard='block', grip='segmented', pommel='cap', motif='none', led=True,
                   blade_h=15, grip_len=29, guard_w=7, guard_h=21, pommel_s=9, tip_len=15,
                   mats=dict(blade='plasteel', guard='gunmetal', grip='polymer', pommel='gunmetal')),
    'ultratech': dict(blade='flared', guard='block', grip='plain', pommel='butt', motif='line',
                      blade_h=14, grip_len=30, guard_w=5.5, guard_h=18, pommel_s=8, facet=0.43,
                      mats=dict(blade='mono_blade', guard='mono_guard', grip='mono_grip', pommel='mono_grip', energy='mono_edge')),
    'archotech': dict(blade='stepped', guard='nested', grip='frame', pommel='cube', motif='circuit', glow='halo',
                      blade_h=15, grip_len=28, guard_w=8, guard_h=22, pommel_s=9, tip_len=14,
                      mats=dict(blade='archo_olive', guard='archo_frame', grip='archo_frame', pommel='archo_olive', energy='archo_yellow')),
    'imperial': dict(blade='flared', guard='wing', grip='wrapped', pommel='diamond', motif='line',
                     blade_h=14, grip_len=28, guard_w=6, guard_h=24, pommel_s=9, facet=0.43,
                     mats=dict(blade='mono_blade', guard='imperial_gold', grip='imperial_purple', wrap='imperial_gold',
                               pommel='imperial_gold', energy='mono_edge')),
    'mechanoid': dict(blade='scythe', guard='carapace', grip='plain', pommel='spike', motif='conduit',
                      blade_h=16, grip_len=26, guard_w=10, guard_h=22, pommel_s=9, curve=2,
                      mats=dict(blade='mech_pale', guard='mech_taupe', grip='undersuit', pommel='mech_taupe', energy='mech_red')),
    'anomaly': dict(blade='jagged', guard='claw', grip='twisted', pommel='spike', motif='ichor',
                    blade_h=14, grip_len=28, guard_w=6, guard_h=22, pommel_s=9, tip_len=16, teeth=6,
                    mats=dict(blade='bioferrite', guard='void_black', grip='flesh', pommel='void_black', energy='glow_red')),
    'dms': dict(blade='cleaver', guard='block', grip='ribbed', pommel='cap', motif='hazard',
                blade_h=16, grip_len=29, guard_w=6, guard_h=20, pommel_s=9,
                mats=dict(blade='dms_steel', guard='dms_gunmetal', grip='polymer', pommel='dms_gunmetal')),
}
SWORD_STYLE['vanilla_expanded'] = dict(SWORD_STYLE['ultratech'])
SWORD_STYLE['bionic'] = dict(SWORD_STYLE['spacer'])

WHITE_BLADES = {'blade_white', 'mono_blade', 'tint_white', 'ceramic', 'plasteel', 'armor_white'}


@register('sword')
def sword(style='ultratech', size: int = 128, seed: int = 0, name: str = 'sword', *,
          blade: Optional[str] = None, guard: Optional[str] = None, grip: Optional[str] = None,
          pommel: Optional[str] = None, motif: Optional[str] = None, mats: Optional[dict] = None,
          blade_h: Optional[float] = None, grip_len: Optional[float] = None, guard_w: Optional[float] = None,
          guard_h: Optional[float] = None, pommel_s: Optional[float] = None, x_start: float = 7.0,
          x_tip: Optional[float] = None, curve: Optional[float] = None, flare: float = 2.0,
          taper: Optional[float] = None, tip_len: Optional[float] = None, teeth: Optional[int] = None,
          waves: int = 3, notches: Sequence[Tuple[float, float, float]] = (), facet: Optional[float] = None,
          motif_t: Tuple[float, float] = (0.023, 0.535), motif_width: float = 4.0, motif_offset: float = 0.0,
          motif_mat: Optional[str] = None, glow: Optional[str] = None, led: Optional[bool] = None,
          trim: Optional[str] = None, trim_mask: Optional[str] = None, outline: Optional[float] = None,
          **_ignored) -> Scene:
    st = get_style(style)
    d = dict(SWORD_STYLE.get(st.key, SWORD_STYLE['ultratech']))
    dm = dict(d.get('mats', {}))
    dm.update(mats or {})

    def pick(v, key, default=None):
        return v if v is not None else d.get(key, default)

    k = size / 128.0
    blade = pick(blade, 'blade')
    guard = pick(guard, 'guard')
    grip = pick(grip, 'grip')
    pommel = pick(pommel, 'pommel')
    motif = pick(motif, 'motif', 'none')
    bh = pick(blade_h, 'blade_h', 14) * k
    gl = pick(grip_len, 'grip_len', 30) * k
    gw = pick(guard_w, 'guard_w', 6) * k
    gh = pick(guard_h, 'guard_h', 18) * k
    ps = pick(pommel_s, 'pommel_s', 8) * k
    xt = pick(x_tip, 'x_tip', 122.5) * k
    curve = pick(curve, 'curve', 0.0) * k
    taper_v = pick(taper, 'taper', 0.15)
    tl = pick(tip_len, 'tip_len', None)
    tl = tl * k if tl is not None else None
    teeth_v = pick(teeth, 'teeth', 6)
    facet_v = pick(facet, 'facet', 0.5)
    glow_mode = pick(glow, 'glow', st.glow if st.glow == 'halo' else None)
    led_v = pick(led, 'led', False)

    s = Scene(size, name=name, outline=outline)
    yc = 64.0 * k
    x0 = x_start * k
    # pommel / butt ----------------------------------------------------------------------
    pm = getmat(dm.get('pommel', 'mono_grip'))
    gm = getmat(dm.get('grip', 'mono_grip'))
    grip_h = 6.5 * k if pommel == 'butt' else min(gh * 0.42, 9 * k) if gh > 0 else 7 * k
    if pommel == 'butt':
        butt = G.rounded(G.rect(x0, yc - 4 * k, x0 + 12 * k, yc + 4 * k), [3.5 * k, 0, 0, 3.5 * k])
        bp = Part('pommel', butt, pm, z=2)
        bp.shade(Bevel(1.0 * k, 1.4 * k, light_tone='deep', shade_tone='#1e1e1e', angle=-90))
        bp.fill(G.circle(x0 + 4 * k, yc - 1.8 * k, 1.3 * k), 'light')
        bp.line([(x0 + 8.5 * k, yc - 3.2 * k), (x0 + 12.5 * k, yc + 2.5 * k)], 1.1 * k, 'deep')
        s.add(bp)
        gx0 = x0 + 10 * k
    else:
        gx0 = x0 + (ps * 0.6 if pommel not in ('none',) else 0)
    gx1 = gx0 + gl
    grip_p = ML.grip_part(grip, gx0, gx1, yc - 0.5 * k, grip_h, gm, st, k, seed=seed,
                          wrap_mat=dm.get('wrap'), z=1)
    if pommel == 'butt':
        grip_p.rings = [G.rect(gx0, yc - 3.3 * k, gx1, yc + 3.0 * k)]
        grip_p.shading = [Bevel(1.0 * k, 1.8 * k, light_tone='deep', shade_tone='#1e1e1e', angle=-90)]
    s.add(grip_p)
    if pommel not in ('butt', 'none'):
        pp = ML.pommel_part(pommel, gx0 + 0.8 * k, yc - 0.5 * k, ps, pm, st, k, seed=seed)
        if pp is not None:
            s.add(pp)
    # guard ----------------------------------------------------------------------------------
    gxc = gx1 + gw / 2 - 1 * k if gw > 0 else gx1
    if guard != 'none' and gw > 0:
        for gp in ML.guard_part(guard, gxc, yc, gw, gh, getmat(dm.get('guard', 'mono_guard')), st, k, seed=seed):
            s.add(gp)
    # blade ----------------------------------------------------------------------------------
    bx0 = gxc + (gw / 2 - 0.5 * k if gw > 0 else 0)
    if blade == 'scythe':
        bx0 = gxc
    bg = ML.blade_geom(blade, bx0, xt, yc, bh, k, curve=curve, taper=taper_v, flare=flare, tip_len=tl,
                       teeth=teeth_v, waves=waves, seed=seed)
    bg = ML.apply_notches(bg, notches, k)
    bm = getmat(dm.get('blade', 'mono_blade'))
    bp = ML.blade_part(bg, bm, st, k, white=bm.name in WHITE_BLADES, facet=facet_v, z=3)
    # the blade sits *under* the guard (vanilla): draw guard after blade
    for p in s.parts:
        if p.name.startswith('guard'):
            p.z = 4 + (p.z - 4)
    s.add(bp)
    # motifs ----------------------------------------------------------------------------------
    emat = motif_mat or dm.get('energy') or (st.materials.get('energy') or 'mono_edge')
    if motif == 'hazard':
        xa, xb = bx0 + (xt - bx0) * 0.12, bx0 + (xt - bx0) * 0.42
        top = bg.mid_at(xa) - bg.hh_at(xa)
        bp.detail(*C.hazard_stripes(xa, top + 1.2 * k, xb, top + 4.4 * k, 7, k))
        bp.detail(*C.rivets([(bx0 + 4 * k, yc + 3 * k), (bx0 + 9 * k, yc + 3 * k)], 1.1 * k, 'dms_steel.deep', 'dms_steel.light'))
        bp.detail(*C.scratches(bx0 + 30 * k, yc - 2 * k, xt - 10 * k, yc + 5 * k, 4, k, seed))
    elif motif != 'none':
        mt0, mt1 = motif_t
        if blade != 'flared' and motif_t == (0.023, 0.535):
            mt0, mt1 = 0.06, 0.6
        bp.detail(*ML.edge_motif(motif, bg, k, mat=emat, t0=mt0, t1=mt1, width=motif_width, offset=motif_offset, seed=seed))
    if st.key == 'neolithic':
        bp.detail(*C.knap_facets(bx0, xt - 8 * k, yc, bh, 6, k, seed))
    if st.key == 'archotech' and blade == 'stepped':
        # floating fragments beside the tip
        s.add(Part('fragment', G.rect(xt - 6 * k, yc - bh * 0.95, xt - 2.5 * k, yc - bh * 0.62), 'archo_olive', z=5,
                   shading=[Bevel(0.8 * k, 0.8 * k)]))
    if led_v:
        g = s.get('guard') if any(p.name == 'guard' for p in s.parts) else None
        if g is not None:
            g.detail(*C.led(gxc, yc + gh * 0.25, 1.4 * k))
    if trim:
        # thin colourable trim stripe along the spine (unique-variant hook, Odyssey-style mask)
        xa, xb = bx0 + 2 * k, bx0 + (xt - bx0) * 0.7
        pts = [(x, bg.mid_at(x) - bg.hh_at(x) + 1.6 * k) for x in (xa, xb)]
        bp.detail(Line(G.poly(pts), 1.6 * k, trim, mask=trim_mask))
    if glow_mode == 'halo':
        bp.glow = Glow(getmat(emat).tone('glow'), radius=2.5 * k, strength=0.45, mode='halo')
    s.meta.update(dict(archetype='sword', style=st.key, kind='melee', blade=blade, guard=guard, grip=grip,
                       pommel=pommel, motif=motif))
    return s
