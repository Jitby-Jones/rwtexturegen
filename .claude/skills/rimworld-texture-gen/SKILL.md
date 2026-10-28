---
name: rimworld-texture-gen
description: Generate RimWorld-style mod textures (melee and ranged weapons, body armor, helmets, bionic part icons) as 128px PNGs with masks, SVGs, previews and XML, in any tech-level or mod house style (neolithic to archotech, DMS, Vanilla Expanded, Bionic Icons). Use when the user asks for a RimWorld texture, a weapon or apparel sprite, an art variant, or how something should look in a given tech level.
---

# RimWorld texture generation

The generator is the `rwtex` package in this repo. It turns vector shapes into a raster paint
pass that copies vanilla RimWorld art.

## 1. Pin down the request

- **Function**: the archetype. Choose from `sword`, `polearm`, `rifle`, `bow`, `armor`, `helmet`
  or `bionic_part`. If none fits, write a Python spec.
- **Style**: the tech level or house style. Run `python -m rwtex styles <key>` to read its rules.
  The aliases work too, e.g. "ultra" → ultratech, "glitterworld" → spacer, "DMS" → dms, "VE" → vanilla_expanded.
- **What is unique about it**: one or two signature features. Keep the rest vanilla.
- **Recreation or variant**: to recreate a vanilla item, start from the archetype's style defaults.
  The `ultratech` sword *is* the monosword. For a variant, swap modules (blade, guard, grip,
  pommel or motif; stock, handguard, sight or muzzle).
- **Colourability**: decide whether it should take stuff or ideology colour. If so, use a mask and
  paint those parts white. Persona weapons use the whole-texture `tint: persona` instead.

If you are unsure what a style looks like, render the matrix before designing:
`python -m rwtex matrix <archetype> --out /tmp/m.png`, then Read the PNG.

## 2. Write the spec

```bash
python -m rwtex new <archetype> --name <TextureName> --style <style> --out specs/<file>.yaml
```

Fill in `params` from `docs/ARCHETYPES.md`. Copy the closest example in `specs/`:

| example | spec |
|---|---|
| monosword recreation | `persona_monosword.yaml` |
| persona variant | `persona_monosword_tidewarden.yaml` |
| custom ultratech polearm | `arc_glaive_halcyon.py` |
| industrial assault rifle with an Odyssey-style unique variant | `assault_rifle_ironclad.yaml` |
| spacer charge rifle | `charge_assault_rifle.yaml` |
| bionic armor and helmet | `bionic_assault_armor.yaml` |

## 3. Build and look

```bash
python -m rwtex build specs/<file>.yaml
```

Read the `_preview.png` (weapons) or the `_worn_preview.png` and `_tint_*.png` (apparel) image
files, then do the passes in `docs/WORKFLOW.md`:

1. **Silhouette**:
   - Is the item readable at 1×?
   - Does the orientation follow vanilla?
   - Is the outline thick and black?
   - For apparel, does the footprint match the vanilla extents in `docs/STYLE_GUIDE.md` §6?
2. **Values**:
   - Does each material use 2–4 flat tones with light from the top?
   - For apparel, are fronts bright, with sides, backs and undersides darker?
   - Is there one accent colour, and is the palette from the style?
3. **Details**: are they sparse, following the form and using the style's motifs? Is the lint
   clean? Read `lint.txt`.
4. **Continuity**: compare against vanilla or the user's other items with `python -m rwtex compare`
   or `sheet`. Check every body type, especially Hulk and Fat.

Iterate on the parameters until every pass holds. Never hand-edit the PNGs.

## 4. Deliver

- Give the output folder path and the key PNGs. Show the preview.
- Paste the XML snippet from `<Name>.xml.txt`. It contains `graphicData`, `CutoutComplex` when
  masked, the persona `color`, `equippedAngleOffset`, `wornGraphicPath` and `useWornGraphicMask`.
- Name the install locations:
  - `Textures/<tex_path>.png`
  - `Textures/Things/Pawn/Humanlike/Apparel/<Name>/` for apparel
- List any lint warnings and say whether they matter. Edge contact is normal for Hulk armor and
  full-width rifles.

## Guardrails

- Don't copy vanilla or mod pixels into the repo. Measured numbers are fine.
- Bionics follow the Bionic Icons language. EPOE colours come from EPOE-Forked.
- Keep it simple. Vanilla items are simple: big flat shapes, few details and a thick outline.
  When a design looks busy, remove things before adding any.
