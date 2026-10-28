---
name: rimworld-texture-gen
description: Generate RimWorld-style mod textures (melee and ranged weapons, body armor, helmets, bionic part icons) as 128px PNGs with masks, previews and graphicData XML, in any tech-level or mod house style (neolithic to archotech, DMS, Vanilla Expanded, Bionic Icons), and install them into a mod's Textures folder. Use when the user asks for a RimWorld texture, a weapon or apparel sprite, an art variant, or how something should look in a given tech level.
---

# RimWorld texture generation

The generator is the `rwtex` Python package in the **rwtexturegen** repository: the folder that
contains `rwtex/`, three levels above this file (`<repo>/.claude/skills/rimworld-texture-gen/`).
It draws vector shapes, then paints them the way vanilla RimWorld art is painted. The user's
**mod is usually a different folder**, and often the session's working directory, so use paths
explicitly.

## 0. Set up (once per environment)

```bash
pip install -e <repo>        # pillow, numpy, pyyaml + the `rwtex` command, usable from any folder
rwtex --help
```

If `pip install` is not possible, run `PYTHONPATH=<repo> python -m rwtex ...` instead.

The reference docs are in `<repo>/docs/`:

| doc | contents |
|---|---|
| `ARCHETYPES.md` | every parameter |
| `STYLE_GUIDE.md` | vanilla measurements |
| `WORKFLOW.md` | the review passes |
| `MODDING.md` | ThingDef XML, colouring and testing in game |
| `STYLE_LEXICON.md` | the styles |

## 1. Pin down the request

- **Function**: pick the archetype. The options are `sword`, `polearm`, `rifle`, `bow`, `armor`,
  `helmet` and `bionic_part`. If none fits, write a Python spec; `<repo>/specs/arc_glaive_halcyon.py`
  is an example.
- **Style**: pick a tech level or house style. Run `rwtex styles <key>` to read its rules.
  Aliases work, e.g. "ultra" → ultratech, "glitterworld" → spacer, "DMS" → dms,
  "VE" → vanilla_expanded.
- **What is unique about it**: one or two signature features. Keep the rest vanilla.
- **Recreation or variant**: each style's defaults are a vanilla item.
  - The `ultratech` sword is the monosword.
  - The `spacer` rifle is the charge rifle.
  - The `industrial` rifle is the assault rifle.
  - Armor designs `marine` and `recon` are fitted to vanilla marine and recon armor; `cataphract`
    and `bionic` are built on them.

  For a variant, swap modules: blade, guard, grip, pommel or motif on melee weapons; stock,
  receiver, handguard, sight, muzzle, mag or `length` on rifles.
- **Colourability**: decide whether the item takes stuff, dye or ideology colour. If so, keep the
  white parts masked; the default armor shell is masked. A persona weapon is never masked: set
  `xml.tint: persona` instead. See `docs/MODDING.md`.

If you are unsure what a style looks like, render the matrix and Read the PNG:
`rwtex matrix <archetype> --out /tmp/m.png`.

## 2. Write the spec in the user's mod

**Keep specs in the mod, not in this repo.** This repo's `specs/` folder is the example gallery.
`<Mod>/Source/TextureSpecs/` is a good place: RimWorld ignores `Source/`.

```bash
cd <Mod>/Source/TextureSpecs
rwtex new rifle --name ChargeCarbine --style spacer
```

The new spec lists the style's defaults as commented `key: value` lines; uncomment and edit them.
It already has the right `tex_path`/`tex_root` and an `xml: def_name`. A misspelled knob prints a
warning instead of being silently ignored.

Copy ideas from the closest example in `<repo>/specs/`:

| example | spec |
|---|---|
| monosword recreation with persona tint | `persona_monosword.yaml` |
| persona monosword variant (module swap, masked) | `persona_monosword_tidewarden.yaml` |
| fully custom ultratech polearm | `arc_glaive_halcyon.py` |
| industrial assault rifle plus an Odyssey-style unique variant | `assault_rifle_ironclad.yaml` |
| charge assault rifle (spacer rifle, `length: 0.93`, red-dot sight) | `charge_assault_rifle.yaml` |
| bionic armor and matching helmet (`items:`) | `bionic_assault_armor.yaml` |

## 3. Build, install and look

```bash
rwtex build <Mod>/Source/TextureSpecs/ --out <scratch>/rwtex-build --mod <Mod>
```

- `--mod` copies only the game textures (PNGs plus `_m`/`…m` masks) into
  `<Mod>/Textures/<tex_path>.png`, and each apparel set into `<Mod>/Textures/<tex_root>/<Name>/`.
- `--out` collects previews, `lint.txt` and `<Name>.xml.txt`. Keep it out of the mod and out of
  this repo's `output/` folder.

Read the `_preview.png` (weapons) or the `_worn_preview.png` and `_tint_*.png` (apparel) images,
then do the passes in `docs/WORKFLOW.md`:

1. **Silhouette**:
   - Is the item readable at 1×?
   - Does the orientation follow vanilla (melee tip right, muzzle right, bows upright)?
   - Is the outline thick and black?
   - For apparel, does the footprint match the vanilla extents in `STYLE_GUIDE.md` §6?
2. **Values**:
   - Does each material use 2–4 flat tones, lit from above?
   - For apparel, are the fronts white and the sides, back and undersides darker?
   - Is there one accent colour?
3. **Details and lint**:
   - Are details sparse and do they use the style's motifs?
   - Is `lint.txt` clean? Edge contact is normal on Hulk armor and full-width rifles.
   - "untinted inside tinted plates" means a mask bug: report it, don't ship it.
4. **Continuity**: compare with the user's other items using `rwtex sheet`, and with vanilla using
   `rwtex compare` if the user has the art source (`MODDING.md` explains). Check every body type,
   especially Hulk and Fat.

Iterate on the parameters until every pass holds. Never hand-edit the PNGs; rebuild them from the
spec.

## 4. Deliver

- List the installed texture paths in the mod and show the preview image.
- Add the graphic block from `<Name>.xml.txt` to the ThingDef. If no def exists yet, scaffold one
  as `MODDING.md` describes:
  - copy the `ParentName` of the vanilla item it riffs on, verified against the user's install;
  - stats are placeholders for the user to balance.
- Report lint warnings and anything you guessed.

## Guardrails

- Never copy vanilla or mod pixels into either repo. Measured numbers are fine.
- Bionics follow the Bionic Icons language. EPOE colours come from EPOE-Forked.
- New armor or helmet designs build on `marine_kit`, `vplate`, `hshell` and `hplate` in
  `rwtex/archetypes/armor3d.py`. Those helpers keep all 5 body types × 3 directions consistent
  with vanilla.
- Keep it simple. Vanilla items are big flat shapes with few details and a thick outline. When a
  design looks busy, remove things before adding any.
