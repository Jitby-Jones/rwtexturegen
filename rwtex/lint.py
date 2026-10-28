"""Texture QA against vanilla conventions (works on any PNG, generated or hand-made)."""
from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from PIL import Image


@dataclass
class Report:
    path: str
    ok: List[str] = field(default_factory=list)
    warn: List[str] = field(default_factory=list)
    err: List[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def text(self) -> str:
        lines = [f'== {self.path}']
        lines += [f'  ERROR {m}' for m in self.err]
        lines += [f'  warn  {m}' for m in self.warn]
        lines += [f'  ok    {m}' for m in self.ok]
        if self.stats:
            lines.append('  stats ' + ', '.join(f'{k}={v}' for k, v in self.stats.items()))
        return '\n'.join(lines)

    @property
    def passed(self) -> bool:
        return not self.err


def _kind_from_name(path: str) -> str:
    n = os.path.basename(path)
    if re.search(r'_(south|east|north|west)m?\.png$', n):
        return 'apparel'
    if n.endswith('_m.png'):
        return 'mask'
    return 'item'


def outline_stats(rgba: np.ndarray) -> dict:
    a = rgba[..., 3] > 127
    lum = rgba[..., :3].astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    pad = np.pad(a, 1)
    neigh_out = ~pad[:-2, 1:-1] | ~pad[2:, 1:-1] | ~pad[1:-1, :-2] | ~pad[1:-1, 2:]
    boundary = a & neigh_out
    if boundary.sum() == 0:
        return {'boundary': 0, 'dark_frac': 0.0, 'thickness': 0.0}
    dark = lum < 40
    dark_frac = float((dark & boundary).sum() / boundary.sum())
    # thickness: run length of dark pixels inward from boundary along rows/cols
    runs = []
    H, W = a.shape
    for y in range(0, H, 2):
        row_a, row_d = a[y], dark[y]
        xs = np.nonzero(row_a)[0]
        if len(xs) == 0:
            continue
        for start, step in ((xs[0], 1), (xs[-1], -1)):
            n = 0
            x = start
            while 0 <= x < W and row_a[x] and row_d[x]:
                n += 1
                x += step
            if 0 < n < 16:
                runs.append(n)
    th = float(np.median(runs)) if runs else 0.0
    return {'boundary': int(boundary.sum()), 'dark_frac': round(dark_frac, 3), 'thickness': th}


def lint_png(path: str, kind: Optional[str] = None) -> Report:
    r = Report(path)
    try:
        im = Image.open(path)
    except Exception as e:  # pragma: no cover
        r.err.append(f'cannot open: {e}')
        return r
    kind = kind or _kind_from_name(path)
    W, H = im.size
    r.stats['size'] = f'{W}x{H}'
    if W % 4 or H % 4:
        r.err.append('dimensions must be multiples of 4 (GPU/DXT compression)')
    elif W & (W - 1) or H & (H - 1):
        r.warn.append('not a power of two (allowed, but 64/128/256 is the convention)')
    else:
        r.ok.append('power-of-two size')
    if max(W, H) > 512 and kind != 'mask':
        r.warn.append('larger than 512px: excessive for RimWorld (VRAM); 128 ppt is the modern baseline')
    if kind == 'mask' or path.endswith('m.png') and kind == 'apparel':
        rgb = np.asarray(im.convert('RGB'), dtype=np.int32)
        if rgb[..., 2].max() > 8:
            r.warn.append('mask uses the blue channel (RimWorld masks use red=primary, green=secondary)')
        used = rgb[..., 0].max() > 0 or rgb[..., 1].max() > 0
        (r.ok if used else r.warn).append('mask has coloured region' if used else 'mask is fully black')
        base = re.sub(r'(_m|m)\.png$', '.png', path)
        if os.path.exists(base) and base != path:
            b = Image.open(base)
            if b.size != im.size:
                r.err.append(f'mask size {im.size} != base size {b.size}')
            else:
                ba = np.asarray(b.convert('RGBA'))[..., 3]
                spill = ((rgb[..., 0] + rgb[..., 1]) > 30) & (ba < 8)
                if spill.mean() > 0.002:
                    r.warn.append('mask colours pixels that are transparent in the base texture')
                else:
                    r.ok.append('mask aligned with base alpha')
        return r
    rgba = np.asarray(im.convert('RGBA'))
    a = rgba[..., 3]
    if a.min() == 255:
        r.err.append('no transparency - RimWorld things need a transparent background')
        return r
    opaque = a > 127
    cover = float(opaque.mean())
    r.stats['coverage'] = round(cover, 3)
    if opaque.sum() == 0:
        r.err.append('fully transparent')
        return r
    ys, xs = np.nonzero(opaque)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    r.stats['bbox'] = f'x{x0}-{x1} y{y0}-{y1}'
    if x0 == 0 or y0 == 0 or x1 == W - 1 or y1 == H - 1:
        r.warn.append('art touches the canvas edge (outline may be clipped)')
    clear = (a == 0)
    if clear.any():
        leak = rgba[..., :3][clear].max()
        if leak > 16:
            r.warn.append('transparent pixels carry colour - set them to black to avoid white halos after compression')
        else:
            r.ok.append('transparent pixels are black')
    o = outline_stats(rgba)
    r.stats.update({'outline_dark_frac': o['dark_frac'], 'outline_px': o['thickness']})
    exp = max(W, H) / 128 * 3.0
    if o['dark_frac'] < 0.8:
        r.warn.append(f'only {o["dark_frac"]:.0%} of the silhouette edge is dark - vanilla uses a continuous black outline')
    else:
        r.ok.append('continuous dark outline')
    if o['thickness'] and not (exp * 0.45 <= o['thickness'] <= exp * 1.9):
        r.warn.append(f'outline ~{o["thickness"]:.1f}px; expected ~{exp:.1f}px at this size (2px per 64ppt rule)')
    px = rgba[..., :3][opaque & (rgba[..., :3].max(axis=2) > 45)]
    if len(px):
        q = (px // 8).astype(np.int32)
        ncol = len(np.unique(q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2]))
        r.stats['colours'] = ncol
        if ncol > 900 * (W * H) / (128 * 128):
            r.warn.append('very many distinct colours - vanilla art is flat (few tones per material)')
        lum = (px.astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722])) / 255
        r.stats['mean_luma'] = round(float(lum.mean()), 3)
    if kind == 'item' and W == H:
        bw, bh = x1 - x0, y1 - y0
        r.stats['aspect'] = round(bw / max(bh, 1), 2)
    return r


def lint_set(directory: str) -> List[str]:
    """Check apparel sets for missing body types/directions and masks."""
    msgs = []
    files = [os.path.basename(f) for f in glob.glob(os.path.join(directory, '*.png'))]
    bases = set()
    for f in files:
        m = re.match(r'(.+)_(Male|Female|Thin|Hulk|Fat)_(south|east|north)\.png$', f)
        if m:
            bases.add(m.group(1))
    for b in sorted(bases):
        missing = [f'{b}_{bt}_{d}.png' for bt in ('Male', 'Female', 'Thin', 'Hulk', 'Fat') for d in ('south', 'east', 'north')
                   if f'{b}_{bt}_{d}.png' not in files]
        if missing:
            msgs.append(f'{b}: missing {len(missing)} worn textures: {", ".join(missing[:5])}...')
        else:
            msgs.append(f'{b}: all 15 worn textures present')
        if f'{b}.png' not in files:
            msgs.append(f'{b}: missing ground texture {b}.png')
        has_masks = any(f.startswith(b) and f.endswith('m.png') for f in files)
        if has_masks:
            mm = [f'{b}_{bt}_{d}m.png' for bt in ('Male', 'Female', 'Thin', 'Hulk', 'Fat') for d in ('south', 'east', 'north')
                  if f'{b}_{bt}_{d}m.png' not in files]
            msgs.append(f'{b}: masks ' + ('complete' if not mm else f'missing {len(mm)}'))
    return msgs
