# CLAUDE.md

This repo is a RimWorld texture generator and reference library. The user makes RimWorld mods and
uses it to produce textures in the vanilla style, or in a mod house style such as DMS, Vanilla
Expanded or Bionic Icons.

## When the user asks for a texture

1. Follow `.claude/skills/rimworld-texture-gen/SKILL.md`. It covers choosing the archetype and
   style, writing the spec, building, the review passes and delivery.
2. **The user's specs live in their mod**, e.g. `<Mod>/Source/TextureSpecs/`. Build them with
   `rwtex build <spec> --out <scratch> --mod <Mod>`, which installs the textures into
   `<Mod>/Textures/`.
   - This repo's `specs/` is the example gallery. Add to it only when extending the gallery.
   - Use a Python spec (see `specs/arc_glaive_halcyon.py`) when no archetype fits.
   - Change the generator only when the feature should be reusable.
3. **Always look at the result.** Read the `_preview.png` or `_worn_preview.png` image and do the
   review passes in `docs/WORKFLOW.md`. Compare with vanilla where you can. At minimum, compare
   with the extents tables in `docs/STYLE_GUIDE.md`.
4. Report the installed paths, the XML snippet from `<name>.xml.txt` and any lint warnings.
   `docs/MODDING.md` covers scaffolding a def; copy its parent from the vanilla item in the user's
   install rather than guessing.

## Commands

```bash
pip install -e .                                  # pillow, numpy, pyyaml + the `rwtex` command
rwtex build path/to/spec.yaml --out /tmp/b --mod path/to/MyMod   # build + install into a mod
rwtex new rifle --name X --style spacer           # starter spec in the current folder
python -m rwtex build specs/                      # all examples -> output/
python -m rwtex build specs/x.yaml                # one spec
python -m rwtex matrix sword|polearm|ranged|armor|helmet|bionic_part --out m.png
python -m rwtex styles [key] | --markdown docs/STYLE_LEXICON.md
python -m rwtex list materials|stuff|styles|archetypes|pictograms
python -m rwtex lint path/*.png ; python -m rwtex compare a.png b.png --zoom 4
python -m pytest -q                               # smoke tests (~1 min)
```

## Where things are

- `rwtex/render.py` has the scene graph, rasteriser, shading ops, SVG export and CutoutComplex
  mask pass.
- `rwtex/materials.py` has the calibrated palettes, with a vanilla source note on each.
  `STUFF` and `TINTS` (persona pink) are there too.
- `rwtex/data/lexicon.yaml` is the style vocabulary. `docs/STYLE_LEXICON.md` is generated from it,
  so edit the YAML and then regenerate.
- `rwtex/archetypes/` holds `sword`, `polearm`, `rifle`, `bow`, `apparel` (armor and helmet entry
  points plus the older 2D designs), `armor3d` (the perspective-correct marine, recon, cataphract
  and bionic designs) and `bionic` (Bionic Icons items).
- `rwtex/form.py` holds the 3D torso and head proxies used by apparel.
  `rwtex/data/armor_fit.json` holds silhouette offsets and plate heights per body type, measured on
  vanilla marine armor (and on recon armor, under `variants`).
- New armor or helmet designs should build on `marine_kit`, `vplate`, `hshell` and `hplate` in
  `armor3d.py`, not on hand-placed 2D shapes. Those helpers are what keep every body type and
  view consistent with vanilla.
- `docs/` holds `STYLE_GUIDE.md` (measurements), `MOD_STYLES.md`, `ARCHETYPES.md` (every
  parameter), `WORKFLOW.md` and `MODDING.md` (defs, colouring, testing in game).

## Rules

- Never commit Ludeon or mod art, including textures, crops and traced outlines. Measurements and
  colour values are fine and should be cited.
- The style rules in `docs/STYLE_GUIDE.md` must hold:
  - black outlines of ~3 px on items and ~3.5–4 px on apparel
  - 2–4 flat tones per material
  - melee tip right, ranged muzzle right
  - transparent pixels black
- Bionic art follows **Bionic Icons**, not the old EPOE boxes. EPOE colours come from
  **EPOE-Forked**.
- Apparel must cover all 5 body types × 3 directions, with a ground icon and masks. Check the worn
  preview for every body type, because Hulk and Fat break designs that look fine on Male.
- After generator changes, rebuild `output/` and the matrices so the gallery stays current:
  `python -m rwtex build specs/` and
  `for a in sword ranged polearm armor helmet bionic_part; do python -m rwtex matrix $a --out output/style_matrix/$a.png; done`.
