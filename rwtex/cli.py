"""Command line: ``python -m rwtex <command>`` (run ``python -m rwtex -h``)."""
from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import List

from PIL import Image


def _expand(paths: List[str]) -> List[str]:
    out: List[str] = []
    for p in paths:
        if os.path.isdir(p):
            out += sorted(glob.glob(os.path.join(p, '**', '*.png'), recursive=True))
        else:
            out += sorted(glob.glob(p)) or [p]
    return out


def cmd_build(a):
    from . import spec as S
    paths = _expand_specs(a.specs)
    if not paths:
        raise SystemExit(f'no spec files found in: {" ".join(a.specs)}')
    if a.mod and not os.path.isdir(a.mod):
        raise SystemExit(f'--mod: {a.mod} is not a folder (expected a RimWorld mod folder containing About/)')
    if a.mod and not os.path.isdir(os.path.join(a.mod, 'About')):
        print(f'note: {a.mod} has no About/ folder - is it really a mod folder?')
    for p in paths:
        S.run(S.load(p), out_root=a.out, svg=False if a.no_svg else None, previews=not a.no_preview, mod=a.mod)


def _expand_specs(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            for ext in ('*.yaml', '*.yml', '*.py', '*.json'):
                out += sorted(glob.glob(os.path.join(p, ext)))
        else:
            out += sorted(glob.glob(p)) or [p]
    return out


def cmd_matrix(a):
    from .matrix import matrix
    img = matrix(a.archetype, a.styles.split(',') if a.styles != 'all' else None, scale=a.scale)
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    img.convert('RGB').save(a.out)
    print('wrote', a.out)


def cmd_styles(a):
    from .styles import all_styles
    from .docs import lexicon_markdown
    if a.markdown:
        md = lexicon_markdown()
        with open(a.markdown, 'w', encoding='utf-8') as f:
            f.write(md)
        print('wrote', a.markdown)
        return
    for k, s in all_styles().items():
        if a.style and k != a.style:
            continue
        print(f'{k:17s} [{s.tech_level}] {s.summary}')
        if a.style:
            print('  shape    ', s.shape)
            print('  materials', s.materials)
            print('  motifs   ', s.motifs)
            for d in s.data.get('do', []):
                print('  DO  ', d)
            for d in s.data.get('dont', []):
                print('  DONT', d)


def cmd_lint(a):
    from .lint import lint_png, lint_set
    files = _expand(a.paths)
    bad = 0
    for f in files:
        r = lint_png(f, a.kind)
        bad += 0 if r.passed else 1
        print(r.text())
    for p in a.paths:
        if os.path.isdir(p):
            for m in lint_set(p):
                print('  set  ', m)
    sys.exit(1 if bad else 0)


def cmd_sheet(a):
    from .preview import contact_sheet
    files = _expand(a.paths)
    img = contact_sheet(files, cell=a.cell, cols=a.cols, title=a.title)
    img.convert('RGB').save(a.out)
    print('wrote', a.out, img.size)


def cmd_compare(a):
    """Side-by-side generated vs reference at zoom, with lint stats for each."""
    from .lint import lint_png
    from .preview import grid, label, on_bg
    ims = []
    for p in a.paths:
        im = Image.open(p).convert('RGBA')
        if im.size != (a.size, a.size):
            im = im.resize((a.size, a.size), Image.LANCZOS)
        r = lint_png(p)
        st = r.stats
        ims.append(label(on_bg(im, scale=a.zoom), f'{os.path.basename(p)}  outline={st.get("outline_px")} luma={st.get("mean_luma")} cols={st.get("colours")}'))
    img = grid(ims, cols=len(ims))
    img.convert('RGB').save(a.out)
    print('wrote', a.out)


def cmd_list(a):
    from .archetypes import REGISTRY
    from .materials import M, STUFF, TINTS
    from .styles import all_styles
    from .archetypes.bionic import PICTOGRAMS
    what = a.what
    if what in ('all', 'archetypes'):
        print('archetypes:', ', '.join(sorted(REGISTRY)))
    if what in ('all', 'styles'):
        print('styles:    ', ', '.join(all_styles()))
    if what in ('all', 'materials'):
        for k, m in sorted(M.items()):
            print(f'  {k:18s} {m.describe()}  {m.note}')
    if what in ('all', 'stuff'):
        print('stuff tints:', ', '.join(STUFF), '| special tints:', ', '.join(TINTS))
    if what in ('all', 'pictograms'):
        print('pictograms:', ', '.join(PICTOGRAMS))


_WEAPON_ROOT = {'sword': 'Things/Item/Equipment/WeaponMelee', 'polearm': 'Things/Item/Equipment/WeaponMelee',
                'rifle': 'Things/Item/Equipment/WeaponRanged', 'bow': 'Things/Item/Equipment/WeaponRanged',
                'bionic_part': 'Things/Item/BodyPart'}
_DEF_PREFIX = {'sword': 'MeleeWeapon_', 'polearm': 'MeleeWeapon_', 'rifle': 'Gun_', 'bow': 'Bow_', 'armor': 'Apparel_',
               'helmet': 'Apparel_', 'bionic_part': ''}


def _knob_hints(arch: str, style: str) -> list:
    """Commented ``key: value`` lines with the style's defaults for an archetype - uncomment and
    edit to override."""
    import inspect
    from .archetypes import APPAREL_OPTIONS, REGISTRY
    from .archetypes import apparel as AP, bow as BW, polearm as PL, rifle as RF, sword as SW
    from .styles import get as get_style
    key = get_style(style).key
    table = {'sword': SW.SWORD_STYLE, 'polearm': PL.POLE_STYLE, 'rifle': RF.RIFLE_STYLE, 'bow': BW.BOW_STYLE,
             'armor': AP.ARMOR_STYLE, 'helmet': AP.HELMET_STYLE}.get(arch, {})
    d = dict(table.get(key) or {})
    mats = d.pop('mats', None)
    lines = [f'# {key} defaults - uncomment a line to change it (every knob: docs/ARCHETYPES.md)']
    if arch == 'armor':
        lines.append(f'# design: {d.pop("design", "marine")}      # marine | recon | cataphract | bionic | plate | tribal | flak | monolith | exo')
    elif arch == 'helmet':
        lines.append(f'# design: {d.pop("design", "marine")}      # marine | recon | cataphract | bionic | helm | ballistic | mask | gasmask | monolith')
    lines += [f'# {k}: {v}' for k, v in d.items()]
    if mats:
        lines.append('# mats: {' + ', '.join(f'{k}: {v}' for k, v in mats.items()) + '}')
    named = [n for n, p in inspect.signature(REGISTRY[arch]).parameters.items()
             if p.kind == p.KEYWORD_ONLY and n not in d and n not in ('mats', 'design', 'design_fn')]
    if arch in ('armor', 'helmet'):
        named += sorted(APPAREL_OPTIONS - {'mask_roles'} - set(named))
    lines.append('# other knobs: ' + ', '.join(named))
    return lines


def cmd_new(a):
    from .archetypes import REGISTRY
    if a.archetype not in REGISTRY:
        raise SystemExit(f'unknown archetype {a.archetype!r}; known: {", ".join(sorted(REGISTRY))}')
    apparel = a.archetype in ('armor', 'helmet')
    size = 64 if a.archetype == 'bionic_part' else 128
    path = a.out or f'{a.name}.yaml'
    if os.path.exists(path) and not a.force:
        raise SystemExit(f'{path} exists (use --force to overwrite)')
    folder = 'apparel' if apparel else ('items' if a.archetype == 'bionic_part' else 'weapons')
    lines = [f'# Generated by `rwtex new` - edit params, then: rwtex build {path} --mod <your mod folder>',
             f'name: {a.name}', f'archetype: {a.archetype}', f'style: {a.style}', f'size: {size}', 'seed: 0',
             'params:']
    lines += ['  ' + h for h in _knob_hints(a.archetype, a.style)] if a.archetype != 'bionic_part' else \
        ['  tier: bionic        # prosthetic | prosthetic_advanced | bionic | bionic_advanced | archotech | archotech_module | ultratech | synthetic | surrogate | organic',
         '  part: arm           # arm | shoulder | leg | hand | eye | heart | lung | spine | kidney | liver | stomach | jaw | brain | ear | generic',
         '  # mask: true        # neutral case + CutoutComplex mask so the game tints it per tier']
    lines += ['output:', f'  dir: output/{folder}/{a.name}']
    if apparel:
        lines += [f'  tex_root: Things/Pawn/Humanlike/Apparel     # textures go to <tex_root>/{a.name}/']
    else:
        lines += [f'  tex_path: {_WEAPON_ROOT[a.archetype]}/{a.name}']
    lines += ['preview:', '  tints: {}          # e.g. {persona: persona} or {olive: [0.55, 0.62, 0.42]}',
              '  stuff: []          # e.g. [Steel, Plasteel] - shown when the texture has a mask',
              'xml:', f'  def_name: {_DEF_PREFIX[a.archetype]}{a.name}']
    if a.archetype in ('sword', 'polearm'):
        lines += ['  melee: true']
    if apparel:
        lines += [f'# items: [{{name: {a.name}Helmet, archetype: helmet, style: {a.style}}}]   # matching helmet in the same build']
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('wrote', path)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='rwtex', description='RimWorld-style vector texture generator')
    sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build', help='render spec files (yaml/py/json) or folders of specs')
    b.add_argument('specs', nargs='+')
    b.add_argument('--out', help='put each spec\'s output folder under this folder (keeps the folder name)')
    b.add_argument('--mod', help='RimWorld mod folder: also copy the game textures (PNG + masks) into MOD/Textures/...')
    b.add_argument('--no-svg', action='store_true')
    b.add_argument('--no-preview', action='store_true')
    b.set_defaults(fn=cmd_build)
    m = sub.add_parser('matrix', help='same archetype rendered across styles/tech levels')
    m.add_argument('archetype', choices=['sword', 'polearm', 'rifle', 'ranged', 'armor', 'helmet', 'bionic_part'])
    m.add_argument('--styles', default='all')
    m.add_argument('--scale', type=int, default=2)
    m.add_argument('--out', default='output/style_matrix/matrix.png')
    m.set_defaults(fn=cmd_matrix)
    s = sub.add_parser('styles', help='print the style lexicon (or --markdown FILE)')
    s.add_argument('style', nargs='?')
    s.add_argument('--markdown')
    s.set_defaults(fn=cmd_styles)
    lt = sub.add_parser('lint', help='QA PNGs against vanilla conventions')
    lt.add_argument('paths', nargs='+')
    lt.add_argument('--kind', choices=['item', 'apparel', 'mask'])
    lt.set_defaults(fn=cmd_lint)
    sh = sub.add_parser('sheet', help='contact sheet of PNGs')
    sh.add_argument('paths', nargs='+')
    sh.add_argument('--out', default='sheet.png')
    sh.add_argument('--cols', type=int, default=6)
    sh.add_argument('--cell', type=int, default=192)
    sh.add_argument('--title')
    sh.set_defaults(fn=cmd_sheet)
    c = sub.add_parser('compare', help='side-by-side zoom comparison (e.g. generated vs vanilla reference)')
    c.add_argument('paths', nargs='+')
    c.add_argument('--out', default='compare.png')
    c.add_argument('--size', type=int, default=128)
    c.add_argument('--zoom', type=int, default=4)
    c.set_defaults(fn=cmd_compare)
    li = sub.add_parser('list', help='list archetypes/styles/materials/stuff/pictograms')
    li.add_argument('what', nargs='?', default='all', choices=['all', 'archetypes', 'styles', 'materials', 'stuff', 'pictograms'])
    li.set_defaults(fn=cmd_list)
    n = sub.add_parser('new', help='write a starter spec')
    n.add_argument('archetype')
    n.add_argument('--name', required=True)
    n.add_argument('--style', default='industrial')
    n.add_argument('--out', help='spec path to write (default: ./<name>.yaml)')
    n.add_argument('--force', action='store_true', help='overwrite an existing spec')
    n.set_defaults(fn=cmd_new)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == '__main__':
    main()
