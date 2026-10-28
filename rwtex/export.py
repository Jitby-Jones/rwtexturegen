"""Writing textures with RimWorld naming conventions + XML snippets.

* Graphic_Single (weapons, items, apparel ground texture): ``Name.png`` + mask ``Name_m.png``
* Graphic_Multi worn body apparel: ``Name_<BodyType>_<dir>.png`` + mask ``Name_<BodyType>_<dir>m.png``
* Graphic_Multi headgear: ``Name_<dir>.png`` + mask ``Name_<dir>m.png``
  (west is optional; RimWorld mirrors east when ``_west`` is missing)
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Union

from PIL import Image

from .render import Scene


def _ensure(d: str) -> None:
    os.makedirs(d, exist_ok=True)


def save_scene(scene: Scene, out_dir: str, name: Optional[str] = None, *, mask: Union[str, bool] = 'auto',
               svg: bool = True, multi_mask_suffix: bool = False) -> Dict[str, str]:
    """Render + save one texture.  Returns {'png':..., 'mask':..., 'svg':...}."""
    _ensure(out_dir)
    name = name or scene.name
    out: Dict[str, str] = {}
    img = scene.render()
    p = os.path.join(out_dir, f'{name}.png')
    img.save(p)
    out['png'] = p
    want_mask = scene.has_mask() if mask == 'auto' else bool(mask)
    if want_mask:
        m = scene.render_mask()
        suffix = 'm' if multi_mask_suffix else '_m'
        mp = os.path.join(out_dir, f'{name}{suffix}.png')
        m.save(mp)
        out['mask'] = mp
    if svg:
        sd = os.path.join(out_dir, 'svg')
        _ensure(sd)
        sp = os.path.join(sd, f'{name}.svg')
        with open(sp, 'w', encoding='utf-8') as f:
            f.write(scene.to_svg())
        out['svg'] = sp
    return out


def save_apparel(aset, out_dir: str, *, mask: Union[str, bool] = 'auto', svg: bool = False) -> Dict[str, Dict[str, str]]:
    """Save every direction/body type + ground with the correct RimWorld file names."""
    _ensure(out_dir)
    res: Dict[str, Dict[str, str]] = {}
    for key, sc in aset.scenes.items():
        if key == 'ground':
            res[key] = save_scene(sc, out_dir, aset.name, mask=mask, svg=svg, multi_mask_suffix=False)
        else:
            res[key] = save_scene(sc, out_dir, f'{aset.name}_{key}', mask=mask, svg=svg, multi_mask_suffix=True)
    return res


def xml_weapon(def_name: str, tex_path: str, *, melee: bool = True, masked: bool = False, tint: Optional[tuple] = None,
               angle: Optional[float] = None) -> str:
    shader = '\n    <shaderType>CutoutComplex</shaderType>' if masked else ''
    color = f'\n    <color>({tint[0]:.2f},{tint[1]:.2f},{tint[2]:.2f})</color>' if tint else ''
    ang = angle if angle is not None else (-65 if melee else None)
    eq = f'\n  <equippedAngleOffset>{ang:g}</equippedAngleOffset>' if ang is not None else ''
    return (f'<!-- graphic block for {def_name} (texture: Textures/{tex_path}.png) -->\n'
            f'<graphicData>\n    <texPath>{tex_path}</texPath>\n    <graphicClass>Graphic_Single</graphicClass>{shader}{color}\n'
            f'</graphicData>{eq}\n')


def xml_apparel(def_name: str, ground_tex: str, worn_path: str, *, head: bool = False, masked: bool = False) -> str:
    shader = '\n    <shaderType>CutoutComplex</shaderType>' if masked else ''
    mask = '\n    <useWornGraphicMask>true</useWornGraphicMask>' if masked else ''
    note = ('headgear: worn textures are <path>_south/_east/_north' if head else
            'body apparel: worn textures are <path>_<BodyType>_south/_east/_north for Male/Female/Thin/Hulk/Fat')
    return (f'<!-- {def_name}: {note}; masks use the "m" suffix (e.g. _southm) -->\n'
            f'<graphicData>\n    <texPath>{ground_tex}</texPath>\n    <graphicClass>Graphic_Single</graphicClass>{shader}\n</graphicData>\n'
            f'<apparel>\n    <wornGraphicPath>{worn_path}</wornGraphicPath>{mask}\n</apparel>\n')
