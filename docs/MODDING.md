# Using generated textures in a mod

This guide covers getting from a spec to an item in the game: the folder layout, the def XML,
how colouring works, where vanilla reference art comes from, and testing.

## Folder layout

```
MyMod/
  About/About.xml
  Defs/ThingDefs/Weapons_MyMod.xml           your defs
  Source/TextureSpecs/ChargeCarbine.yaml     your specs (RimWorld ignores Source/)
  Textures/Things/Item/Equipment/WeaponRanged/ChargeCarbine.png
  Textures/Things/Pawn/Humanlike/Apparel/ScoutArmor/ScoutArmor.png
  Textures/Things/Pawn/Humanlike/Apparel/ScoutArmor/ScoutArmor_Male_south.png   (and so on)
```

`rwtex build MyMod/Source/TextureSpecs/ --out <scratch> --mod MyMod` fills `Textures/` for you.
It copies only the game textures; previews, lint reports and XML snippets stay in `--out`.

Keep the specs in the mod repo. That way the textures can be rebuilt whenever you change a
design or update the generator.

## The graphic block

Every build writes `<Name>.xml.txt` with the graphic part of the def. Paste it into the
ThingDef.

**Weapon or item** (`Graphic_Single`; the texture lives at `Textures/<texPath>.png`):

```xml
<graphicData>
  <texPath>Things/Item/Equipment/WeaponRanged/ChargeCarbine</texPath>
  <graphicClass>Graphic_Single</graphicClass>
  <shaderType>CutoutComplex</shaderType>    <!-- only when the build wrote a _m mask -->
  <color>(0.97,0.78,0.79)</color>           <!-- only for a whole-texture tint, e.g. persona weapons -->
</graphicData>
<equippedAngleOffset>-65</equippedAngleOffset>   <!-- melee weapons; it sits at ThingDef level -->
```

**Apparel**:

- `texPath` is the ground icon.
- `wornGraphicPath` is the worn texture set. The game appends `_<BodyType>_<dir>` for body
  apparel and `_<dir>` for headgear.
- Masks add the `m` suffix (`_southm`), and they need `useWornGraphicMask`.

```xml
<graphicData>
  <texPath>Things/Pawn/Humanlike/Apparel/ScoutArmor/ScoutArmor</texPath>
  <graphicClass>Graphic_Single</graphicClass>
  <shaderType>CutoutComplex</shaderType>
</graphicData>
<apparel>
  <wornGraphicPath>Things/Pawn/Humanlike/Apparel/ScoutArmor/ScoutArmor</wornGraphicPath>
  <useWornGraphicMask>true</useWornGraphicMask>
  <!-- bodyPartGroups, layers, tags... come from the vanilla parent you copy -->
</apparel>
```

## Scaffolding a def

Do not guess parent def names, recipes or research. They change between versions and DLCs.
Instead, find the vanilla item you are riffing on in **your** install and copy its structure:

```bash
grep -rl "<defName>Gun_ChargeRifle</defName>" "<RimWorld>/Data"/*/Defs
```

Use the matching defName for other items, e.g. `Gun_AssaultRifle`, `MeleeWeapon_LongSword`,
`Apparel_PowerArmor` or `Apparel_PowerArmorHelmet`. `<RimWorld>` is the game folder, e.g.
`steamapps/common/RimWorld`. DLC defs live in `Data/Royalty`, `Data/Ideology` and so on.

Copy these from the vanilla def:

- `ParentName`
- the weapon `verbs`/`tools` or the `apparel` block
- `recipeMaker` / research
- the tags

Then change `defName`, `label`, `description`, the graphic block and the stats. Treat every stat
you write as a placeholder for the user to balance.

## Colour: masks, stuff, dye and ideology

| texture | how the game colours it |
|---|---|
| **No mask** (Cutout shader) | The whole texture is multiplied by the item's colour: stuff colour for stuff-made items, dye or ideology colour for apparel. Vanilla marine and recon armor work this way; they ship without masks. Only the white shell visibly changes, because everything else is near-black. |
| **Mask** (CutoutComplex) | Red pixels take the item's colour (`colorOne`: stuff, dye or ideology colour). Green takes `colorTwo`. Black stays as painted. Vanilla's prestige armors ship masks (`…_southm.png`). |
| **Fixed tint** (`graphicData <color>`) | The whole texture always gets one colour, e.g. the persona weapons' dark pink. |

- **Generator default**: armor shells and other colourable parts are masked red, so bionic parts,
  lenses and glow strips keep their own colours.
- **Vanilla-style unmasked textures**: set `output: {mask: false}` in the spec.
- **Masked weapons**: set `mask_parts` (rifle) or materials with a mask (sword `trim_mask`, the
  `tint_white` / `ceramic` / `armor_white` materials).
- **Dyeable, ideology-coloured or stuff-made**: this is decided by the def, not the texture.
  Inherit it from the vanilla parent you copied, or add `stuffCategories` and `costStuffCount`
  for stuff.

## Vanilla reference art

Vanilla textures don't ship as loose PNGs in the game folder. Ludeon publishes the original art
source; the RimWorld wiki page *Modding Tutorials/Textures* links it.

- Use those files **locally** to check your work:

  ```bash
  rwtex compare mine.png vanilla.png --zoom 4
  ```

- Never commit them to a repo. This repo only stores numbers measured from them: the
  `STYLE_GUIDE.md` tables and `rwtex/data/*.json`.

## Testing in game

1. Restart RimWorld after adding or replacing textures; they load at startup.
2. Turn on development mode. Spawn the item from the debug actions menu (spawn thing), or have a
   colonist wear or equip it.
3. Check it on the ground on light and dark floors.
4. Check all four directions; west is the mirrored east texture.
5. Check apparel on a Hulk, a Fat and a Thin pawn.
6. For colourable items, try a couple of stuffs or dyes.
7. Red error text about missing textures usually means a wrong `texPath` or folder. Compare it with
   the paths `rwtex build --mod` printed.
