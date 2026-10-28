"""Smoke tests: every archetype renders in every style, specs build, outputs follow the vanilla
conventions checked by rwtex.lint.  Run with ``python -m pytest -q`` (or ``python -m unittest``)."""
import glob
import os
import tempfile
import unittest
import warnings

import numpy as np

from rwtex.archetypes import build
from rwtex.archetypes.apparel import BODY_TYPES, DIRS
from rwtex.docs import lexicon_markdown
from rwtex.lint import lint_png, mask_slivers
from rwtex.spec import load, run
from rwtex.styles import all_styles

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STYLES = list(all_styles())


def _check_rgba(test, img, size=128):
    test.assertEqual(img.size, (size, size))
    a = np.asarray(img)
    alpha = a[..., 3]
    test.assertTrue((alpha > 0).any(), 'empty texture')
    test.assertTrue((a[alpha == 0][:, :3] == 0).all(), 'transparent pixels must keep black RGB')


class WeaponArchetypes(unittest.TestCase):
    def test_weapons_render_in_every_style(self):
        for arch in ('sword', 'polearm', 'rifle'):
            for st in STYLES:
                with self.subTest(arch=arch, style=st):
                    _check_rgba(self, build(arch, style=st).render())

    def test_bows(self):
        for kind in ('short', 'recurve', 'long', 'crossbow', 'compound'):
            with self.subTest(kind=kind):
                _check_rgba(self, build('bow', kind=kind).render())

    def test_bionic_parts(self):
        sc = build('bionic_part', tier='archotech_module', part='heart', mask=True)
        _check_rgba(self, sc.render(), 64)
        m = np.asarray(sc.render_mask())
        self.assertTrue((m[..., 0] > 200).any() and (m[..., 1] > 200).any(), 'mask needs R case + G pictogram')

    def test_monosword_lints_clean(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'Monosword.png')
            build('sword', style='ultratech').render().save(p)
            r = lint_png(p, 'item')
            self.assertEqual(r.err, [], r.text())


class Apparel(unittest.TestCase):
    def test_armor_designs_cover_all_body_types(self):
        for design in ('marine', 'recon', 'cataphract', 'bionic'):
            with self.subTest(design=design):
                aset = build('armor', style='spacer', design=design, name='T')
                keys = set(aset.scenes)
                for bt in BODY_TYPES:
                    for d in DIRS:
                        self.assertIn(f'{bt}_{d}', keys)
                self.assertIn('ground', keys)
                _check_rgba(self, aset.scenes['Hulk_east'].render())
                self.assertTrue(aset.scenes['Male_south'].has_mask())

    def test_helmets(self):
        for design in ('marine', 'recon', 'cataphract', 'bionic', 'helm', 'gasmask'):
            with self.subTest(design=design):
                aset = build('helmet', style='spacer', design=design, name='H')
                for d in DIRS:
                    _check_rgba(self, aset.scenes[d].render())


def _extent(img):
    al = np.asarray(img)[..., 3] > 128
    ys, xs = np.nonzero(al)
    return xs.min(), xs.max(), ys.min(), ys.max()


class Regressions(unittest.TestCase):
    def test_masks_have_no_untinted_slivers(self):
        """Part lines must be clipped in the mask exactly as in the texture (dyed armor used to
        show white seams)."""
        with tempfile.TemporaryDirectory() as d:
            for design in ('marine', 'recon', 'bionic'):
                aset = build('armor', style='bionic' if design == 'bionic' else 'spacer', design=design, name='A',
                             body_types=['Male', 'Female', 'Fat'], dirs=['south', 'east'], ground=False)
                for key, sc in aset.scenes.items():
                    tp, mp = os.path.join(d, f'{design}_{key}.png'), os.path.join(d, f'{design}_{key}m.png')
                    sc.render().save(tp)
                    sc.render_mask().save(mp)
                    with self.subTest(design=design, view=key):
                        self.assertEqual(mask_slivers(tp, mp), 0)

    def test_recon_matches_vanilla_footprint(self):
        """docs/STYLE_GUIDE.md: vanilla ReconArmor Male south x38-88, y42-109."""
        x0, x1, y0, y1 = _extent(build('armor', style='spacer', design='recon', name='A', body_types=['Male'],
                                       dirs=['south'], ground=False).scenes['Male_south'].render())
        for got, want in ((x0, 38), (x1, 88), (y0, 42), (y1, 109)):
            self.assertLessEqual(abs(int(got) - want), 3)

    def test_rifle_length_shortens_and_centres(self):
        full = _extent(build('rifle', style='industrial').render())
        short = _extent(build('rifle', style='industrial', length=0.8).render())
        self.assertLess(short[1] - short[0], (full[1] - full[0]) * 0.9)
        self.assertLessEqual(abs((short[0] + short[1]) / 2 - 63.5), 1.0)

    def test_unknown_parameter_warns(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            build('rifle', style='spacer', lenght=0.8)
        self.assertTrue(any('lenght' in str(x.message) for x in w))

    def test_new_and_build_install_into_a_mod(self):
        from rwtex.cli import main
        with tempfile.TemporaryDirectory() as d:
            mod = os.path.join(d, 'MyMod')
            os.makedirs(os.path.join(mod, 'About'))
            gun, suit = os.path.join(d, 'Gun.yaml'), os.path.join(d, 'Suit.yaml')
            main(['new', 'rifle', '--name', 'TestGun', '--style', 'spacer', '--out', gun])
            main(['new', 'helmet', '--name', 'TestHelm', '--style', 'spacer', '--out', suit])
            main(['build', gun, suit, '--out', os.path.join(d, 'build'), '--mod', mod, '--no-svg'])
            tex = os.path.join(mod, 'Textures')
            self.assertTrue(os.path.exists(os.path.join(tex, 'Things/Item/Equipment/WeaponRanged/TestGun.png')))
            helm = os.path.join(tex, 'Things/Pawn/Humanlike/Apparel/TestHelm')
            for f in ('TestHelm.png', 'TestHelm_south.png', 'TestHelm_east.png', 'TestHelm_north.png', 'TestHelm_southm.png'):
                self.assertTrue(os.path.exists(os.path.join(helm, f)), f)
            self.assertFalse(glob.glob(os.path.join(tex, '**', '*preview*'), recursive=True))


class Specs(unittest.TestCase):
    def test_example_specs_build(self):
        specs = sorted(glob.glob(os.path.join(ROOT, 'specs', '*.yaml')) + glob.glob(os.path.join(ROOT, 'specs', '*.py')))
        self.assertGreaterEqual(len(specs), 6)
        with tempfile.TemporaryDirectory() as d:
            for path in specs:
                with self.subTest(spec=os.path.basename(path)):
                    man = run(load(path), out_root=d, svg=False, previews=False, quiet=True)
                    self.assertTrue(any(f.endswith('.png') for f in man['files']))
                    errors = [(p, e) for p, e, _w in man['lint'] if e]
                    self.assertEqual(errors, [])


class Docs(unittest.TestCase):
    def test_style_lexicon_doc_is_current(self):
        with open(os.path.join(ROOT, 'docs', 'STYLE_LEXICON.md'), encoding='utf-8') as f:
            self.assertEqual(f.read().strip(), lexicon_markdown().strip(),
                             'regenerate with: python -m rwtex styles --markdown docs/STYLE_LEXICON.md')


if __name__ == '__main__':
    unittest.main()
