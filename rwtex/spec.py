"""Spec files: describe a texture (or a set) declaratively and render everything it needs.

YAML spec::

    name: PersonaMonosword            # output base name (RimWorld texture name)
    archetype: sword                  # sword|polearm|rifle|bow|armor|helmet|bionic_part
    style: ultratech                  # any lexicon key / alias
    size: 128
    seed: 0
    params: {blade: flared, motif: line}          # archetype keyword arguments
    output: {dir: output/weapons/PersonaMonosword, tex_path: Things/Item/Equipment/WeaponMelee/PersonaMonosword}
    preview: {tints: {persona: persona}, stuff: [Steel, Plasteel]}
    xml: {def_name: MeleeWeapon_PersonaMonosword, melee: true, tint: persona}
    items: [...]                      # optional extra items (same keys) rendered into the same folder

Python spec (``.py``): define ``SPEC`` (same keys, minus archetype) and ``build(spec) ->
Scene | ApparelSet | list[Scene | ApparelSet]`` for fully custom compositions.

``python -m rwtex build spec.yaml --mod path/to/MyMod`` also copies the game textures into
``MyMod/Textures/<tex_path>`` (weapons/items) or ``MyMod/Textures/<tex_root>/<Name>/`` (apparel).
"""
from __future__ import annotations

import importlib.util
import json
import os
from typing import Any, Dict, List, Optional

from . import preview as PV
from .archetypes import build as build_archetype
from .archetypes.apparel import ApparelSet
from .export import save_apparel, save_scene, xml_apparel, xml_weapon
from .lint import lint_png, lint_set
from .materials import STUFF, TINTS
from .render import Scene

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path: str) -> Dict[str, Any]:
    if path.endswith(('.yaml', '.yml')):
        import yaml
        with open(path, 'r', encoding='utf-8') as f:
            spec = yaml.safe_load(f)
    elif path.endswith('.json'):
        with open(path, 'r', encoding='utf-8') as f:
            spec = json.load(f)
    elif path.endswith('.py'):
        mod_name = 'rwtex_spec_' + os.path.splitext(os.path.basename(path))[0]
        sp = importlib.util.spec_from_file_location(mod_name, path)
        mod = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(mod)  # type: ignore[union-attr]
        spec = dict(getattr(mod, 'SPEC', {}))
        spec['_build'] = mod.build
    else:
        raise ValueError(f'unsupported spec type: {path}')
    spec['_path'] = path
    return spec


def _tint_value(v):
    if isinstance(v, str):
        if v in TINTS:
            return TINTS[v]
        if v in STUFF:
            return STUFF[v]
    return v


def build_objects(spec: Dict[str, Any]) -> List[Any]:
    if '_build' in spec:
        res = spec['_build'](spec)
        return res if isinstance(res, list) else [res]
    kw = dict(spec.get('params') or {})
    for key in ('style', 'size', 'seed'):
        if key in spec:
            kw[key] = spec[key]
    kw['name'] = spec['name']
    return [build_archetype(spec['archetype'], **kw)]


_DEFAULT_TEX_ROOT = {'melee': 'Things/Item/Equipment/WeaponMelee', 'ranged': 'Things/Item/Equipment/WeaponRanged'}
APPAREL_TEX_ROOT = 'Things/Pawn/Humanlike/Apparel'


def _entries(spec: Dict[str, Any]) -> List[tuple]:
    """(sub-spec, object) pairs: the spec's own objects, then those of each ``items`` entry (an
    item may carry its own ``xml`` and ``output.tex_path`` / ``output.tex_root``)."""
    out = [(spec, o) for o in build_objects(spec)]
    for extra in spec.get('items', []) or []:
        e = dict(extra)
        e.setdefault('style', spec.get('style'))
        e.setdefault('size', spec.get('size', 128))
        out += [(e, o) for o in build_objects(e)]
    return out


def _install(src: str, dst: str, manifest: Dict[str, Any]) -> None:
    import shutil
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    manifest['installed'].append(dst)


def run(spec: Dict[str, Any], out_root: Optional[str] = None, svg: Optional[bool] = None,
        previews: bool = True, quiet: bool = False, mod: Optional[str] = None) -> Dict[str, Any]:
    """Build + save everything a spec asks for.  Returns a manifest dict.

    ``out_root`` replaces the parent of ``output.dir`` (each spec keeps its own folder name).
    ``mod`` is a RimWorld mod folder: the game textures (PNGs + masks, no previews/SVG/notes)
    are also copied to ``<mod>/Textures/<texture path>``, each apparel set into its own folder."""
    out_cfg = dict(spec.get('output', {}))
    out_dir = out_cfg.get('dir') or os.path.join('output', spec['name'])
    if out_root:
        out_dir = os.path.join(out_root, os.path.basename(out_dir.rstrip('/')))
    os.makedirs(out_dir, exist_ok=True)
    want_svg = out_cfg.get('svg', True) if svg is None else svg
    manifest: Dict[str, Any] = {'name': spec['name'], 'dir': out_dir, 'files': [], 'previews': [], 'lint': [], 'installed': [],
                                'xml': os.path.join(out_dir, f'{spec["name"]}.xml.txt')}
    entries = _entries(spec)
    pv = spec.get('preview', {}) or {}
    tints = {k: _tint_value(v) for k, v in (pv.get('tints') or {}).items()}
    stuff = {s_: STUFF[s_] for s_ in (pv.get('stuff', []) or [])}   # only meaningful where a mask exists
    xml_parts: List[str] = []
    helmets = [o for _, o in entries if isinstance(o, ApparelSet) and o.kind == 'head']
    bodies = [o for _, o in entries if isinstance(o, ApparelSet) and o.kind == 'body']
    for sub, obj in entries:
        sub_out = dict(sub.get('output', {}) or {})
        x = dict(sub.get('xml', {}) or {}) if sub is not spec or obj.name == spec['name'] else {}
        if isinstance(obj, ApparelSet):
            res = save_apparel(obj, out_dir, mask=out_cfg.get('mask', 'auto'), svg=want_svg and out_cfg.get('svg_apparel', False))
            for r in res.values():
                manifest['files'] += list(r.values())
            base = sub_out.get('tex_root') or out_cfg.get('tex_root') or APPAREL_TEX_ROOT
            masked = any('mask' in r for r in res.values())
            xml_parts.append(xml_apparel(x.get('def_name', obj.name), f'{base}/{obj.name}/{obj.name}', f'{base}/{obj.name}/{obj.name}',
                                         head=obj.kind == 'head', masked=masked))
            if mod:
                for r in res.values():
                    for kind in ('png', 'mask'):
                        if kind in r:
                            _install(r[kind], os.path.join(mod, 'Textures', base, obj.name, os.path.basename(r[kind])), manifest)
        elif isinstance(obj, Scene):
            res = save_scene(obj, out_dir, obj.name, mask=out_cfg.get('mask', 'auto'), svg=want_svg)
            manifest['files'] += list(res.values())
            kind = obj.meta.get('kind')
            tex = sub_out.get('tex_path') if obj.name == sub.get('name') else None
            root = sub_out.get('tex_root') or out_cfg.get('tex_root') or _DEFAULT_TEX_ROOT.get(kind, 'Things/Item')
            tex = tex or f'{root}/{obj.name}'
            melee = kind == 'melee' if 'melee' not in x else x['melee']
            tint = _tint_value(x['tint']) if x.get('tint') else None
            xml_parts.append(xml_weapon(x.get('def_name', obj.name), tex, melee=melee, masked='mask' in res, tint=tint,
                                        angle=x.get('angle')))
            if mod:
                _install(res['png'], os.path.join(mod, 'Textures', tex + '.png'), manifest)
                if 'mask' in res:
                    _install(res['mask'], os.path.join(mod, 'Textures', tex + '_m.png'), manifest)
            if previews and kind in ('melee', 'ranged', 'item', None):
                mask_img = obj.render_mask() if 'mask' in res else None
                tt = dict(tints)
                if mask_img is not None:
                    tt.update(stuff)
                sheet = PV.weapon_sheet(obj, mask_img, tt, title=f'{obj.name} ({obj.meta.get("style", "")})')
                sp = os.path.join(out_dir, f'{obj.name}_preview.png')
                sheet.convert('RGB').save(sp)
                manifest['previews'].append(sp)
    if previews and (bodies or helmets):
        a = bodies[0] if bodies else None
        h = helmets[0] if helmets else None
        sheet = PV.apparel_sheet(a, h, title=f'{spec["name"]} worn preview')
        sp = os.path.join(out_dir, f'{spec["name"]}_worn_preview.png')
        sheet.convert('RGB').save(sp)
        manifest['previews'].append(sp)
        for name, col in {**tints, **stuff}.items():
            sheet = PV.apparel_sheet(a, h, body_types=('Male', 'Hulk'), tint_color=col, title=f'{spec["name"]} tinted: {name}')
            sp = os.path.join(out_dir, f'{spec["name"]}_tint_{name}.png')
            sheet.convert('RGB').save(sp)
            manifest['previews'].append(sp)
    with open(manifest['xml'], 'w', encoding='utf-8') as f:
        f.write('\n'.join(xml_parts))
    reports = [lint_png(p) for p in manifest['files'] if p.endswith('.png')]
    lines = [r.text() for r in reports] + lint_set(out_dir)
    with open(os.path.join(out_dir, 'lint.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    manifest['lint'] = [(r.path, len(r.err), len(r.warn)) for r in reports]
    set_warn = [ln for ln in lines if ln.startswith('warn')]
    if not quiet:
        n_err = sum(len(r.err) for r in reports)
        n_warn = sum(len(r.warn) for r in reports) + len(set_warn)
        print(f'[{spec["name"]}] {len([f for f in manifest["files"] if f.endswith(".png")])} png -> {out_dir}  '
              f'(lint: {n_err} errors, {n_warn} warnings; previews: {len(manifest["previews"])})')
        if mod:
            roots = sorted({os.path.dirname(p) for p in manifest['installed']})
            print(f'    installed {len(manifest["installed"])} textures into ' + ', '.join(roots))
        print(f'    XML: {manifest["xml"]}')
    return manifest
