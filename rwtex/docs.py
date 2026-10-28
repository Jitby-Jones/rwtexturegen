"""Generate docs/STYLE_LEXICON.md from rwtex/data/lexicon.yaml (single source of truth)."""
from __future__ import annotations

from .materials import M
from .color import to_hex
from .styles import all_styles, lexicon
from .archetypes.sword import SWORD_STYLE
from .archetypes.rifle import RIFLE_STYLE
from .archetypes.apparel import ARMOR_STYLE, HELMET_STYLE
from .archetypes.polearm import POLE_STYLE


def _mat(name):
    if not name:
        return '-'
    m = M.get(name)
    if m is None:
        return name
    return f'`{name}` {to_hex(m.base)}'


def lexicon_markdown() -> str:
    lex = lexicon()
    st = all_styles()
    out = ['# Style lexicon', '',
           '> Generated from `rwtex/data/lexicon.yaml` by `python -m rwtex styles --markdown docs/STYLE_LEXICON.md`.',
           '> Edit the YAML, not this file.', '',
           'A **style** is a reusable visual language: a shape grammar (corners, irregularity, bulk, taper, ornament),',
           'material roles mapped to calibrated palettes, decoration motifs and do/don\'t rules. Every archetype',
           '(`sword`, `polearm`, `rifle`, `bow`, `armor`, `helmet`, `bionic_part`) reads the style, so the *same',
           'functional design* can be rendered at any tech level: `python -m rwtex matrix sword`.', '',
           '## Quick reference', '',
           '| style | tech level | one-line read | corners | key materials | signature motifs |',
           '|---|---|---|---|---|---|']
    for k, s in st.items():
        mats = ', '.join(f'{r}:{s.materials[r]}' for r in ('primary', 'accent', 'energy') if s.materials.get(r))
        out.append(f'| **{k}** | {s.tech_level} | {s.summary.split(".")[0]}. | {s.corners} | {mats} | {", ".join(s.motifs[:4])} |')
    out += ['', '## Same function, different tech level', '',
            'How each archetype changes per style (defaults; every knob can be overridden in a spec).', '',
            '| style | sword (blade / guard / grip / pommel / motif) | ranged | polearm head | armor design | helmet design |',
            '|---|---|---|---|---|---|']
    for k in st:
        sw = SWORD_STYLE.get(k, {})
        rf = RIFLE_STYLE.get(k, {})
        ranged = 'bow' if k == 'neolithic' else 'crossbow' if k == 'medieval' else \
            (f'{rf.get("stock")} stock, {rf.get("receiver")} receiver, {rf.get("mag")} mag, {rf.get("handguard")} handguard' if rf else '-')
        out.append(f'| {k} | {sw.get("blade", "-")} / {sw.get("guard", "-")} / {sw.get("grip", "-")} / {sw.get("pommel", "-")} / {sw.get("motif", "-")} '
                   f'| {ranged} | {POLE_STYLE.get(k, {}).get("head", "-")} | {ARMOR_STYLE.get(k, {}).get("design", "-")} '
                   f'| {HELMET_STYLE.get(k, {}).get("design", "-")} |')
    out += ['', '## Material roles', '']
    for r, d in lex.get('roles', {}).items():
        out.append(f'- **{r}** - {d}')
    for k, s in st.items():
        d = s.data
        out += ['', f'## {s.label} (`{k}`)', '', f'*Tech level:* {s.tech_level} &nbsp; *Aliases:* {", ".join(s.aka) or "-"}', '',
                s.summary, '', '**Shape grammar**', '', '| knob | value |', '|---|---|']
        for kk, vv in s.shape.items():
            out.append(f'| {kk} | {vv} |')
        out += ['', '**Materials**', '', '| role | material |', '|---|---|']
        for r, mname in s.materials.items():
            out.append(f'| {r} | {_mat(mname)} |')
        out += ['', f'**Motifs:** {", ".join(s.motifs)} &nbsp; **Glow:** {s.glow}', '']
        if d.get('palette_notes'):
            out += [f'**Palette notes:** {d["palette_notes"]}', '']
        if d.get('do'):
            out += ['**Do**', ''] + [f'- {x}' for x in d['do']] + ['']
        if d.get('dont'):
            out += ["**Don't**", ''] + [f'- {x}' for x in d['dont']] + ['']
        if d.get('tiers'):
            out += ['**Tiers**', '', '| tier | case | strip |', '|---|---|---|']
            for t, tv in d['tiers'].items():
                out.append(f'| {t} | {_mat(tv.get("case"))} | {_mat(tv.get("strip"))} |')
            out.append('')
        if d.get('vanilla_refs'):
            out.append(f'**Vanilla references:** {", ".join(d["vanilla_refs"])}')
        if d.get('mod_refs'):
            out.append(f'**Mod references:** {", ".join(d["mod_refs"])}')
    out += ['', '## Materials catalogue', '', '| material | base | light | shade | deep | notes |', '|---|---|---|---|---|---|']
    for k, m in sorted(M.items()):
        out.append(f'| `{k}` | {to_hex(m.base)} | {to_hex(m.light)} | {to_hex(m.shade)} | {to_hex(m.deep)} | {m.note} |')
    return '\n'.join(out) + '\n'
