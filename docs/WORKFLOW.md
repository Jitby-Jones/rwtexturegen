# Workflow: idea → texture in game

## 0. Decide what the thing *is*

- **Function**: sword, polearm, rifle, bow, body armor, helmet or bionic part. If nothing fits,
  write a Python spec.
- **Style**: the tech level or house style. Read `docs/STYLE_LEXICON.md`, and run
  `python -m rwtex matrix <archetype>` to see the function in every style side by side.
- **What makes it unique**: one or two signature features, for example a notch in the spine, a
  crescent guard, a glowing slot or a charge cell. Everything else stays vanilla. RimWorld items
  read best when they are simple.

## 1. Write a spec

```bash
python -m rwtex new sword --name MyBlade --style ultratech --out specs/my_blade.yaml
```

Edit `params` using the parameter tables in `docs/ARCHETYPES.md`, then build it:

```bash
python -m rwtex build specs/my_blade.yaml
```

The output folder then contains:

- `MyBlade.png` (128 px) and `MyBlade_m.png` if anything is masked
- `svg/MyBlade.svg`
- `MyBlade_preview.png`, with 4×, 2× and 1× views on the dirt colour plus tint swatches
- `MyBlade.xml.txt`, a `graphicData` snippet
- `lint.txt`

For apparel, every body type and direction is written, along with `_worn_preview.png` (pawns in all
body types and directions) and `_tint_<name>.png`.

## 2. The multi-pass review

Look at the preview after every pass. Use the Read tool on the PNG, which shows the image.

1. **Silhouette pass.** Read the 1× view and imagine it filled black.
   - Is the item recognisable at 64 px?
   - Is the outline thick, closed and pure black?
   - Does the orientation follow vanilla: melee tip right, ranged muzzle right with the bore at
     y ≈ 63.5, bows upright?
   - For apparel, compare the footprint with the vanilla extents table in `docs/STYLE_GUIDE.md` §6.
     Pads should extend about 8 px past the body, and the armor should start around y39 on a Male.
2. **Value and material pass.**
   - Does each material use 2–4 flat tones with no noise?
   - Is the light coming from the top?
   - For apparel, are front planes bright, sides and backs a step darker, and undersides dark?
   - Are colourable regions painted white or light grey and masked red?
   - Is there only **one** accent colour, and does the palette match the style's lexicon entry?
3. **Detail and outline pass.**
   - Are details sparse, following the form and clipped inside their parts?
   - Do inner lines separate the parts?
   - Do motifs come from the style (vents for spacer and DMS, circuits for archotech, seams and a
     node for ultratech)?
   - Is the lint clean? Edge warnings are acceptable when vanilla does the same, as with Hulk armor
     and full-width rifles.
4. **Continuity and in-context pass.** Compare against vanilla and the rest of your mod:

   ```bash
   python -m rwtex compare output/weapons/MyBlade/MyBlade.png path/to/vanilla/Monosword.png --zoom 4
   python -m rwtex sheet output/weapons/*/*.png --out sheet.png --title "my mod"
   ```

   Check that the outline weight, ramp brightness, scale and detail density match the neighbours.
   Run `python -m rwtex matrix <archetype> --styles a,b,c` to confirm a family of items reads as one
   tech level.

Fix by changing parameters. Don't edit the PNG. The PNG is a build output that should always be
reproducible from the spec.

## 3. Install in the mod

1. Copy the PNGs to `YourMod/Textures/<tex_path>`. For apparel, copy them to
   `YourMod/Textures/Things/Pawn/Humanlike/Apparel/<Name>/`.
2. Paste the XML snippet into the def. It contains:
   - `graphicData`, with `CutoutComplex` when masked and a `color` for persona tints
   - `equippedAngleOffset` for melee weapons
   - `wornGraphicPath` and `useWornGraphicMask` for apparel
3. Check in game:
   - the item on the ground, on several floor colours
   - the item equipped, in all four directions (west is mirrored east)
   - at least one stuff tint, if the item is masked

## Tips

- Persona weapons use the normal texture plus `xml.tint: persona`. Don't bake the pink in.
- For a unique variant of a vanilla weapon, start from the recreation's parameters and swap one or
  two modules. That is how VE and Odyssey unique weapons work.
- Keep specs in your mod repo, next to the defs, so textures can be rebuilt after a style change.
- `--no-preview` and `--no-svg` make batch builds faster.
