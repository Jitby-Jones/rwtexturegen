# Workflow: idea → texture in game

## 0. Decide what the thing *is*

- **Function**: sword, polearm, rifle, bow, body armor, helmet or bionic part. If nothing fits,
  write a Python spec.
- **Style**: the tech level or house style. Read `docs/STYLE_LEXICON.md`, and run
  `rwtex matrix <archetype>` to see the function in every style side by side.
- **What makes it unique**: one or two signature features, for example a notch in the spine, a
  crescent guard, a glowing slot or a charge cell. Everything else stays vanilla. RimWorld items
  read best when they are simple.

## 1. Write a spec (in your mod)

Install the tool once, so the `rwtex` command works from any folder:

```bash
pip install -e /path/to/rwtexturegen
```

Keep your specs in the mod, e.g. `MyMod/Source/TextureSpecs/`; RimWorld ignores `Source/`. This
repo's `specs/` folder is only the example gallery.

```bash
cd MyMod/Source/TextureSpecs
rwtex new sword --name MyBlade --style ultratech
```

The starter spec lists the style's defaults as commented `key: value` lines; uncomment and edit
them. Every knob is described in `docs/ARCHETYPES.md`. Then build it, install the textures into
the mod, and send the previews to a scratch folder:

```bash
rwtex build MyBlade.yaml --out /tmp/rwtex-build --mod ../..
```

- The **mod** gets the game textures only:
  - `Textures/<tex_path>.png`, plus `_m.png` if anything is masked;
  - for apparel, `Textures/<tex_root>/<Name>/` with all 15 worn textures, their `…m` masks and the
    ground icon.
- The **build folder** gets the files to review:
  - `MyBlade_preview.png`, with 4×, 2× and 1× views on the dirt colour plus tint swatches (apparel
    gets `_worn_preview.png` and `_tint_<name>.png` instead);
  - `MyBlade.xml.txt`, the `graphicData` snippet;
  - `lint.txt`;
  - `svg/` sources.

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
   rwtex compare output/weapons/MyBlade/MyBlade.png path/to/vanilla/Monosword.png --zoom 4
   rwtex sheet output/weapons/*/*.png --out sheet.png --title "my mod"
   ```

   Check that the outline weight, ramp brightness, scale and detail density match the neighbours.
   Run `rwtex matrix <archetype> --styles a,b,c` to confirm a family of items reads as one
   tech level.

Fix by changing parameters. Don't edit the PNG. The PNG is a build output that should always be
reproducible from the spec.

## 3. Finish the def

1. `--mod` has already put the textures in place. Without it, copy the PNGs and masks yourself:
   - weapons and items go to `Textures/<tex_path>`;
   - apparel goes to `Textures/Things/Pawn/Humanlike/Apparel/<Name>/`.
2. Paste the snippet from `<Name>.xml.txt` into the ThingDef. It contains:
   - `graphicData`, with `CutoutComplex` when masked and a `color` for persona tints;
   - `equippedAngleOffset` for melee weapons;
   - `wornGraphicPath` and `useWornGraphicMask` for apparel.

   For a new item, scaffold the def from the vanilla item it riffs on (see `docs/MODDING.md`).
3. Check in game (`docs/MODDING.md` has a checklist):
   - the item on the ground, on several floor colours;
   - the item equipped, in all four directions (west is mirrored east);
   - at least one stuff or dye colour, if the item is masked.

## Tips

- Persona weapons use the normal texture plus `xml.tint: persona`. Don't bake the pink in.
- For a unique variant of a vanilla weapon, start from the recreation's parameters and swap one or
  two modules. That is how VE and Odyssey unique weapons work.
- Keep specs in your mod repo, next to the defs, so textures can be rebuilt after a style change.
- A misspelled knob prints a warning; read the build output.
- `--no-preview` and `--no-svg` make batch builds faster.
