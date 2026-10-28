"""Style matrices: one functional archetype rendered in every style (visual continuity check)."""
from __future__ import annotations

from typing import List, Optional, Sequence

from PIL import Image

from . import preview as PV
from .archetypes import build
from .styles import all_styles

DEFAULT = {
    'sword': ['neolithic', 'medieval', 'industrial', 'spacer', 'ultratech', 'archotech', 'imperial', 'mechanoid', 'anomaly', 'dms'],
    'polearm': ['neolithic', 'medieval', 'industrial', 'spacer', 'ultratech', 'archotech', 'imperial', 'mechanoid', 'anomaly', 'dms'],
    'rifle': ['industrial', 'vanilla_expanded', 'spacer', 'ultratech', 'archotech', 'imperial', 'mechanoid', 'anomaly', 'dms'],
    'ranged': ['neolithic', 'medieval', 'industrial', 'spacer', 'ultratech', 'archotech', 'imperial', 'mechanoid', 'anomaly', 'dms'],
    'armor': ['neolithic', 'medieval', 'industrial', 'spacer', 'ultratech', 'archotech', 'imperial', 'dms', 'bionic'],
    'helmet': ['neolithic', 'medieval', 'industrial', 'spacer', 'ultratech', 'archotech', 'imperial', 'dms', 'bionic'],
    'bionic_part': ['prosthetic', 'prosthetic_advanced', 'bionic', 'bionic_advanced', 'archotech', 'archotech_module',
                    'ultratech', 'synthetic', 'surrogate', 'organic'],
}


def _weapon_tile(scene, label: str, scale: int) -> Image.Image:
    return PV.label(PV.on_bg(scene.render(), scale=scale), label)


def matrix(archetype: str, styles: Optional[Sequence[str]] = None, scale: int = 2, cols: int = 5) -> Image.Image:
    styles = list(styles or DEFAULT.get(archetype, list(all_styles())))
    tiles: List[Image.Image] = []
    if archetype in ('sword', 'polearm', 'rifle'):
        for s in styles:
            tiles.append(_weapon_tile(build(archetype, style=s, seed=3), s, scale))
    elif archetype == 'ranged':
        for s in styles:
            arch = 'bow' if s in ('neolithic', 'medieval') else 'rifle'
            tiles.append(_weapon_tile(build(arch, style=s, seed=3), f'{s} ({arch})', scale))
    elif archetype == 'bionic_part':
        parts = ['hand', 'leg', 'arm', 'arm', 'eye', 'brain', 'heart', 'kidney', 'liver', 'lung']
        for i, t in enumerate(styles):
            tiles.append(PV.label(PV.on_bg(build('bionic_part', tier=t, part=parts[i % len(parts)]).render(), scale=scale * 2), t))
    elif archetype in ('armor', 'helmet'):
        cols = 3
        for s in styles:
            a = build('armor', style=s, name='A', body_types=['Male'], ground=False)
            h = build('helmet', style=s, name='H', ground=False)
            row = []
            for d in ('south', 'east', 'north'):
                pawn = PV.worn(PV.body_scene('Male', d).render(), a.scenes[f'Male_{d}'].render(), PV.head_scene(d).render(),
                               h.scenes[d].render(), d)
                row.append(PV.on_bg(pawn, scale=scale))
            w = sum(r.width for r in row) + 8 * (len(row) - 1)
            strip = Image.new('RGBA', (w, row[0].height), PV.BG_GROUND)
            x = 0
            for r in row:
                strip.alpha_composite(r, (x, 0))
                x += r.width + 8
            tiles.append(PV.label(strip, s))
    else:
        raise ValueError(archetype)
    return PV.grid(tiles, cols=cols, bg=PV.BG_DARK, title=f'{archetype}: same function, different tech level / faction style')
