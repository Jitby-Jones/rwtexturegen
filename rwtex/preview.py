"""Preview helpers: ground view, worn-on-pawn composites, tint previews and contact sheets.

Pawn bodies/heads used here are *synthetic* (drawn from the measured silhouette templates),
so no vanilla art is redistributed.
"""
from __future__ import annotations

import os
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import geom as G
from .color import cutout_complex, rgb, to255
from .render import Bevel, Fill, Part, Scene, Split

BG_GROUND = (107, 100, 87, 255)   # soil-ish mid tone close to RimWorld dirt
BG_DARK = (40, 42, 44, 255)
SKIN = '#e9c7a7'
HEAD_OFFSET = {'south': (0.0, -29.0), 'north': (0.0, -29.0), 'east': (3.4, -29.0)}  # px at 128, BodyTypeDef headOffset (x, 0.34 tile)


def _font(size: int = 11):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf',
              'C:/Windows/Fonts/arial.ttf', '/System/Library/Fonts/Supplemental/Arial.ttf'):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def body_scene(bt: str, dir: str, size: int = 128, skin=SKIN) -> Scene:
    from .archetypes.apparel import body_frame
    k = size / 128
    s = Scene(size, outline=0)
    f = body_frame(bt, dir, k)
    s.add(Part('skin', f.silhouette(-3.4), skin, outline=3.4 * k, shading=[Bevel(0, 2.5 * k, shade_tone='shade')]))
    return s


def head_scene(dir: str, size: int = 128, skin=SKIN) -> Scene:
    from .archetypes.apparel import head_frame
    k = size / 128
    s = Scene(size, outline=0)
    f = head_frame(dir, k)
    p = s.add(Part('head', f.silhouette(-3.4), skin, outline=3.4 * k, shading=[Bevel(0, 2.5 * k, shade_tone='shade')]))
    if dir == 'south':
        for u in (-0.32, 0.32):
            p.fill(f.ellipse(u, 0.52, 0.07, 0.035), '#222222')
    elif dir == 'east':
        p.fill(f.ellipse(0.55, 0.52, 0.07, 0.035), '#222222')
    return s


def _img(x) -> Image.Image:
    if isinstance(x, Image.Image):
        return x.convert('RGBA')
    if isinstance(x, Scene):
        return x.render()
    return Image.open(x).convert('RGBA')


def on_bg(img: Image.Image, bg=BG_GROUND, scale: int = 1) -> Image.Image:
    b = Image.new('RGBA', img.size, bg)
    b.alpha_composite(img)
    if scale != 1:
        b = b.resize((img.width * scale, img.height * scale), Image.NEAREST)
    return b


def worn(body_img: Image.Image, apparel: Optional[Image.Image], head_img: Optional[Image.Image],
         helmet: Optional[Image.Image], dir: str, size: int = 128) -> Image.Image:
    """Composite one pawn: body, body apparel, head, headgear (head offset per vanilla)."""
    k = size / 128
    canvas = Image.new('RGBA', (size, int(size * 1.3)), (0, 0, 0, 0))
    oy = int(size * 0.3)
    canvas.alpha_composite(body_img, (0, oy))
    if apparel is not None:
        canvas.alpha_composite(apparel, (0, oy))
    dx, dy = HEAD_OFFSET[dir]
    hx, hy = int(round(dx * k)), int(round(oy + dy * k))
    if head_img is not None:
        canvas.alpha_composite(head_img, (hx, hy))
    if helmet is not None:
        canvas.alpha_composite(helmet, (hx, hy))
    return canvas


def label(img: Image.Image, text: str, color=(235, 235, 235, 255)) -> Image.Image:
    out = Image.new('RGBA', (img.width, img.height + 16), (0, 0, 0, 0))
    out.alpha_composite(img)
    ImageDraw.Draw(out).text((3, img.height + 1), text, fill=color, font=_font(11))
    return out


def grid(images: Sequence[Image.Image], cols: int, bg=BG_GROUND, pad: int = 6, title: Optional[str] = None) -> Image.Image:
    if not images:
        return Image.new('RGBA', (16, 16), bg)
    w = max(i.width for i in images)
    h = max(i.height for i in images)
    rows = (len(images) + cols - 1) // cols
    th = 22 if title else 0
    sheet = Image.new('RGBA', (cols * (w + pad) + pad, rows * (h + pad) + pad + th), bg)
    if title:
        ImageDraw.Draw(sheet).text((pad, 4), title, fill=(255, 255, 255, 255), font=_font(14))
    for i, im in enumerate(images):
        x = pad + (i % cols) * (w + pad) + (w - im.width) // 2
        y = th + pad + (i // cols) * (h + pad) + (h - im.height) // 2
        sheet.alpha_composite(im, (x, y))
    return sheet


def tint(img: Image.Image, color, mask: Optional[Image.Image] = None, color_two=(1, 1, 1)) -> Image.Image:
    """Preview how RimWorld colours a texture: whole-texture multiply (Cutout + graphicData
    colour, e.g. persona pink) when ``mask`` is None, CutoutComplex when a mask is given."""
    a = np.asarray(img.convert('RGBA'), dtype=np.float32) / 255.0
    rgb_ = a[..., :3]
    if mask is None:
        out = rgb_ * np.array(rgb(color), dtype=np.float32)
    else:
        m = np.asarray(mask.convert('RGB'), dtype=np.float32) / 255.0
        out = cutout_complex(rgb_, m, color, color_two)
    o = np.concatenate([np.clip(out, 0, 1), a[..., 3:4]], axis=2)
    return Image.fromarray((o * 255 + 0.5).astype(np.uint8), 'RGBA')


def weapon_sheet(scene_or_img, mask: Optional[Image.Image] = None, tints: Optional[Dict[str, tuple]] = None,
                 title: str = '') -> Image.Image:
    """Ground view at 1x/2x/4x + optional tint swatches."""
    img = _img(scene_or_img)
    small = [label(on_bg(img, scale=2), '2x'), label(on_bg(img, scale=1), '1x')]
    for name, col in (tints or {}).items():
        small.append(label(on_bg(tint(img, col, mask), scale=2), name))
    right = grid(small, cols=2, bg=BG_DARK, pad=6)
    big = label(on_bg(img, scale=4), '4x')
    W = big.width + right.width + 18
    H = max(big.height, right.height) + 28
    out = Image.new('RGBA', (W, H), BG_DARK)
    ImageDraw.Draw(out).text((6, 4), title, fill=(255, 255, 255, 255), font=_font(14))
    out.alpha_composite(big, (6, 24))
    out.alpha_composite(right, (big.width + 12, 18))
    return out


def apparel_sheet(armor_set=None, helmet_set=None, body_types: Sequence[str] = ('Male', 'Female', 'Thin', 'Hulk', 'Fat'),
                  dirs: Sequence[str] = ('south', 'east', 'north'), scale: int = 2, tint_color=None, title: str = '',
                  rendered: Optional[Dict[str, Image.Image]] = None, masks: Optional[Dict[str, Image.Image]] = None) -> Image.Image:
    """Grid of pawns wearing the apparel: rows = body types, columns = directions; plus ground icons."""
    size = 128
    rendered = rendered or {}
    masks = masks or {}

    def get(setobj, key):
        if setobj is None:
            return None
        if (setobj.name, key) in rendered:
            im = rendered[(setobj.name, key)]
        else:
            sc = setobj.scenes.get(key)
            if sc is None:
                return None
            im = sc.render()
        if tint_color is not None:
            m = masks.get((setobj.name, key))
            if m is None and setobj.scenes.get(key) is not None and setobj.scenes[key].has_mask():
                m = setobj.scenes[key].render_mask()
            if m is not None:
                im = tint(im, tint_color, m)
        return im

    gr = []
    if armor_set is not None and 'ground' in armor_set.scenes:
        gr.append(label(on_bg(get(armor_set, 'ground'), scale=scale), 'ground (body)'))
    if helmet_set is not None and 'ground' in helmet_set.scenes:
        gr.append(label(on_bg(get(helmet_set, 'ground'), scale=scale), 'ground (helmet)'))
    blank = Image.new('RGBA', (8, 8), (0, 0, 0, 0))
    tiles = []
    bts = list(body_types) if armor_set is not None else ['Male']
    for i, bt in enumerate(bts):
        for dr in dirs:
            body = body_scene(bt, dr).render()
            head = head_scene(dr).render()
            ap = get(armor_set, f'{bt}_{dr}')
            hm = get(helmet_set, dr)
            pawn = worn(body, ap, head, hm, dr)
            tiles.append(label(on_bg(pawn, scale=scale), f'{bt} {dr}'))
        if gr:
            tiles.append(gr[i] if i < len(gr) else blank)
    for j in range(len(bts), len(gr)):  # more ground icons than rows
        tiles += [blank] * len(dirs) + [gr[j]]
    return grid(tiles, cols=len(dirs) + (1 if gr else 0), bg=BG_DARK, title=title)


def contact_sheet(paths_or_imgs: Sequence[Union[str, Image.Image]], labels: Optional[Sequence[str]] = None,
                  cell: int = 192, cols: int = 6, bg=BG_GROUND, title: Optional[str] = None) -> Image.Image:
    tiles = []
    for i, p in enumerate(paths_or_imgs):
        im = _img(p)
        s = min(cell / im.width, cell / im.height)
        im2 = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.NEAREST if s >= 1 else Image.LANCZOS)
        t = Image.new('RGBA', (cell, cell), bg)
        t.alpha_composite(im2, ((cell - im2.width) // 2, (cell - im2.height) // 2))
        tiles.append(label(t, labels[i] if labels else (os.path.basename(p) if isinstance(p, str) else '')))
    return grid(tiles, cols, bg=BG_DARK, title=title)
