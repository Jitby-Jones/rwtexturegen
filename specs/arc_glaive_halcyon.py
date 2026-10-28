"""Unique ultratech melee weapon: the 'Halcyon' arc glaive.

A fully custom composition (Python spec) built from the same parts API the archetypes use,
so it inherits the ultratech lexicon: white ceramic + graphite, ONE luminous accent (cyan),
long uninterrupted surfaces, thin seams, node dots.  Drawn horizontally with the head to the
right (vanilla spear/ikwa convention; held with equippedAngleOffset -65).

Signature features (what makes it 'unique' rather than a re-skinned spear):
  * naginata-style blade that sweeps upward, cutting edge on the convex underside
  * a glowing field slot cut THROUGH the blade (reads as an energy channel)
  * back hook + twin emitter fins around a cyan socket node
  * ceramic counterweight pommel balancing the long head
"""
from rwtex import geom as G
from rwtex.parts import common as C
from rwtex.render import Bevel, Dome, Facets, Fill, Line, Part, Scene, Split

SPEC = {
    'name': 'ArcGlaive_Halcyon',
    'style': 'ultratech',
    'size': 128,
    'output': {'dir': 'output/weapons/ArcGlaive_Halcyon', 'tex_path': 'Things/Item/Equipment/WeaponMelee/ArcGlaive_Halcyon',
               'mask': False},
    'preview': {'tints': {}},
    'xml': {'def_name': 'MeleeWeapon_ArcGlaive_Halcyon', 'melee': True},
}

FACETS = Facets(1.4, ('light', 'base', 'shade', 'deep'), (0.5, 0.0, -0.75))


def build(spec):
    size = spec.get('size', 128)
    k = size / 128.0

    def X(v):
        return v * k

    def P(*pts):
        return G.poly([(X(x), X(y)) for x, y in pts])

    s = Scene(size, name=spec['name'])
    yc = X(64)
    fac = Facets(X(1.4), FACETS.tones, FACETS.thresholds)

    # haft: graphite core, segmented grip zone, two ceramic sleeves ------------------------
    haft = s.add('haft', G.rounded(G.rect(X(14), yc - X(2.4), X(90), yc + X(2.4)), X(1.6)), 'graphite', z=1,
                 shading=[Bevel(X(0.9), X(1.1), angle=-90)])
    haft.detail(*C.ring_lines(X(24), X(45), yc, X(2.2), 6, X(0.8), 'light'))
    for i, (x0, x1) in enumerate(((46, 55), (72, 81))):
        sl = s.add(f'sleeve{i}', G.chamfer(G.rect(X(x0), yc - X(3.6), X(x1), yc + X(3.6)), X(1.4)), 'ceramic', z=2,
                   shading=[fac, Split(at=0.62, tone='shade')])
        sl.line([(X(x0 + 1.5), yc - X(0.6)), (X(x1 - 1.5), yc - X(0.6))], X(0.8), 'shade')

    # counterweight pommel -------------------------------------------------------------------
    pom = G.Path().move(X(17), yc - X(4.2)).quad(X(8.5), yc - X(5.2), X(5.5), yc).quad(X(8.5), yc + X(5.2), X(17), yc + X(4.2)).close().ring
    pp = s.add('pommel', pom, 'ceramic', z=2, shading=[Dome(('light', 'base', 'shade'), (-0.3, -0.5), 1.2), fac])
    pp.detail(Fill([G.circle(X(11), yc, X(1.5))], 'mono_cyan.base', mask=None),
              Fill([G.circle(X(10.6), yc - X(0.4), X(0.6))], 'mono_cyan.light', mask=None))
    s.add('pommel_cap', G.chamfer(G.rect(X(15.5), yc - X(3.4), X(19), yc + X(3.4)), X(0.8)), 'graphite', z=2.5,
          shading=[Bevel(X(0.8), X(0.8), angle=-90)])

    # emitter fins + socket ---------------------------------------------------------------------
    fin_t = P((86.5, 60.6), (83.5, 55.2), (87.5, 55.6), (94.5, 60.6))
    fin_b = G.mirror_y(fin_t, yc)
    for nm, r in (('fin_top', fin_t), ('fin_bottom', fin_b)):
        s.add(nm, G.chamfer(r, X(0.8)), 'ceramic', z=3, shading=[fac])
    sock = s.add('socket', G.chamfer(G.rect(X(84.5), yc - X(4.6), X(98), yc + X(4.6)), X(1.6)), 'graphite', z=4,
                 shading=[Facets(X(1.2), ('light', 'base', 'shade', 'deep'), (0.5, 0.0, -0.75)), Split(at=0.6, tone='shade')])
    sock.detail(Fill([G.circle(X(91.5), yc, X(2.5))], 'black', mask=None),
                Fill([G.circle(X(91.5), yc, X(1.8))], 'mono_cyan.base', mask=None),
                Fill([G.circle(X(90.9), yc - X(0.6), X(0.7))], 'mono_cyan.light', mask=None))

    # blade -----------------------------------------------------------------------------------
    blade = G.Path().move(X(96.5), yc - X(4.6)).line(X(107.5), yc - X(6.2)).quad(X(117), yc - X(8.2), X(121.5), yc - X(25)) \
        .quad(X(120.8), yc + X(3.4), X(108.5), yc + X(7.6)).quad(X(102), yc + X(9.0), X(96.5), yc + X(4.6)).close().ring
    hook = P((99.5, 59.8), (101.8, 51.2), (104.4, 51.6), (104.4, 59.2))
    s.add('hook', G.chamfer(hook, X(0.6)), 'ceramic', z=4.5, shading=[fac])
    bp = s.add('blade', blade, 'ceramic', z=5, shading=[Bevel(X(1.0), X(1.0), light_tone='#aaaaaa', shade_tone='deep', angle=-90)])
    # lower (edge) facet following the curve
    mid = G.qbezier((X(96.5), yc + X(2.6)), (X(114), yc + X(3.0)), (X(121.5), yc - X(25)))
    edge = G.qbezier((X(121.5), yc - X(25)), (X(120.8), yc + X(3.4)), (X(108.5), yc + X(7.6)))
    edge2 = G.qbezier((X(108.5), yc + X(7.6)), (X(102), yc + X(9.0)), (X(96.5), yc + X(4.6)))
    import numpy as np
    bp.fill(np.vstack([mid, edge[1:], edge2[1:]]), 'shade')
    bp.line(mid[:-6], X(1.0), 'line')
    # mono-edge along the cutting edge
    mono = G.qbezier((X(99.5), yc + X(6.0)), (X(114.5), yc + X(5.0)), (X(119.6), yc - X(17)))
    bp.detail(Line(mono, X(1.6), 'mono_cyan.base', mask=None))
    # field slot cut through the blade, glowing
    slot = G.capsule(X(101.5), yc - X(1.6), X(111.5), yc - X(3.2), X(1.25))
    bp.detail(Fill([slot], 'mono_cyan.base', mask=None, outline=X(0.9), outline_tone='black'),
              Line(G.poly([(X(102.2), yc - X(2.0)), (X(110.8), yc - X(3.4))]), X(0.7), 'mono_cyan.light', mask=None))
    s.meta.update(dict(archetype='custom', style='ultratech', kind='melee'))
    return s
