# RimWorld texture style guide (measured)

These are the vanilla conventions the generator copies. The numbers were measured from the
official art source and the in-game textures (RimWorld 1.5 and 1.6, all DLCs). Pixel values
assume a **128 px** texture unless stated otherwise.

## 1. Canvas and scale

| item | convention |
|---|---|
| resolution | Core-era art is 64 px per tile, while DLC art and modern mods use **128 px**; some Royalty art-source files are 256 px. The generator defaults to 128 and scales every measurement by `k = size / 128`. |
| dimensions | Power of two, or at least a multiple of 4, so DXT compression works. |
| humanlike pawn | The body mesh is 1.5 tiles, so a 128 px body or apparel texture works out to 85.3 px per tile. The Male `headOffset` of (0.04, 0.34) tiles comes to (+3.4, -29) px; the east view shifts the head forward. |
| transparency | Fully transparent pixels must keep **black RGB**. A white RGB under alpha 0 bleeds a white halo after mipmapping and compression. |

## 2. Outline

- The outline is pure black `#000000`, a hard edge with anti-aliasing only, never coloured.
- Weapons and items have an outer outline of **~3 px** at 128, or ~1.5 px at 64. Bright, stuff-coloured
  blades sometimes drop to 2 px.
- Apparel and pawns have an outer outline of **~3.5–4 px** at 128.
- Inner part lines are thinner black lines (~1.4 px on weapons, ~2 px on apparel) where one part
  overlaps another. They separate the parts without covering them in outlines.
- Most of the "RimWorld look" comes from this thick outline wrapped around flat, simple fills.

## 3. Light and shading

- **Items**: light comes from the top, slightly left. Each material uses 2–4 *quantised* tones: a
  flat base, a light band on the top edge and a shade band on the bottom. There are no textures,
  noise or soft airbrushing. Blades are two-tone with a bright upper facet and a darker lower facet
  split along the edge.
- **Apparel**: light is **pawn-relative**, so a plane that faces the pawn's front is the brightest
  in every view.
  - South view: the front shell is white, the sides fall off to light grey, and the undersides
    (pad bottoms, tasset hems) are darker.
  - East view: the front of the torso (screen right) is bright, the side plane is mid grey, and the
    back edge is darker.
  - North view: the back is uniformly a step darker than the front.

  Plates read as a **few crisp facets** wrapped around a rounded body:
  - Horizontal bands (belt, plate edges) bow downward in the middle because the camera looks down.
  - The neck hole is a foreshortened ellipse.
  - Side planes are narrow.
  - Parts that face away disappear.

  The generator models this with 3D proxies; see `rwtex/form.py`.
- Gradients are rare. When they appear, they are subtle radial lifts on round forms such as
  helmets and shoulder domes.

## 4. Palettes

| family | swatches | notes |
|---|---|---|
| Firearm grey ramp | `#111` `#1a1a1a` `#222` polymer · `#333` `#444` · `#4d4d4d` shade · `#666` steel · `#757575` · `#919191` highlight | Assault rifle furniture is `#222` with `#333`/`#444` highlights; receivers are `#666`/`#919191`/`#4d4d4d`. |
| Colourable (tint) white | `#ffffff` `#f2f2f2` `#cccccc` | Odyssey unique-weapon parts; mask is pure red `#ff0000`. |
| Charge tech | olive `#738542` with highlight `#9dad5a` | Charge rifle and charge lance cells. |
| Melee blades | `#ffffff` top facet, `#dddddd` lower facet | Longsword, monosword (`#dedfde`) and other stuff-coloured blades. |
| Monosword | grip `#636563` / top `#313431`; guard `#949294` / `#898789` / `#4a4d4a`; mono-edge cyan `#2986a5` (bulb `#318ea5`, glint `#c0dae3`) | Measured from the 128 px in-game texture. |
| Marine / recon / cataphract | shells `#fcfcfc` / `#cccccc` / `#a3a3a3`, undersuit `#303030`, neck hole dark with a light rim | The base suits ship **without** masks: dye or ideology colour multiplies the whole texture, and only the white shell visibly changes. The prestige versions ship `…_southm` masks. |
| Prestige trim | gold `#b4983c` | |
| Mechanoid | taupe `#8c7868` (`#9c8c84` / `#706458`), pale shells `#a9ad9c`, conduit `#a4b4bc`, red lights `#fc4838` | Charge blaster, inferno cannon, lancer, diabolus. |
| Archotech | olive-khaki blocks `#8a8e6a`..`#a9ac86`, frame `#444`, yellow traces `#e6d53a` with via dots, eye glow `#dedf42` | |
| Bionic health items | prosthetic (154,124,104), bionic (189,169,118), archotech (155,165,148) | These are vanilla `HealthItem` colours. |
| Bionic eye overlay | plate `#a0a0a0`/`#e8e8e8`, black ring, lens `#303a3d` | |

**Stuff colours** (from the wiki):

| stuff | RGB |
|---|---|
| Plasteel | (160,178,181) |
| Steel | (102,102,105) |
| Uranium | (100,100,100) |
| Gold | (255,235,122) |
| Silver | (180,173,150) |
| Jade | (85,118,69) |
| Wood | (133,97,67) |
| Granite | (105,95,97) |
| Marble | (132,135,132) |
| Slate | (70,70,70) |
| Hyperweave | (0,106,126) |
| Devilstrand | (180,60,60) |
| Bioferrite | (100,80,80) |
| Obsidian | (50,50,50) |

All of these are in `rwtex/materials.py` (`M`, `STUFF`, `TINTS`); list them with
`python -m rwtex list materials`.

## 5. Orientation and layout

- **Melee** is drawn horizontally with the pommel on the left and the **tip on the right**. Use
  `equippedAngleOffset` -65 in the def.
  - Monosword (128): grip x7–37, guard x38–43.5 / y55–73, blade y57–71 flaring at x110 to a
    point at x122.5. The cyan line runs y62–66 from a bulb at x48 for about 60% of the blade.
  - Longsword: x2–122, y46–74.
  - Gladius: x15–120, y50–70.
- **Ranged** is drawn horizontally with the **muzzle on the right** and the bore centred
  vertically (y ≈ 63.5).
  - The vanilla assault rifle spans the whole width (x0–127, y49–97): stock x4–34 (a wedge with its
    top on the bore line), grip angled back under x34–46, magazine x52–66, handguard x68–104,
    front sight post at x≈107 and barrel to x≈124.
  - Charge rifle: x9–121, y49–88.
  - Weapons may touch the canvas edge; vanilla rifles do.
- **Bows** are upright, with the limbs vertical, the belly facing right and the string on the left.
  **Crossbows** are horizontal, like rifles.

## 6. Apparel

- **Body apparel:** `Name_<BodyType>_<dir>.png` for each body type (Male, Female, Thin, Hulk,
  Fat) and each direction (south, east, north). West is the mirrored east.
- **Headgear:** `Name_<dir>.png`.
- **Ground icon:** `Name.png`, either 64 px or 128 px. It shows the front torso enlarged, with the
  neck hole visible.

Measured silhouettes (`rwtex/data/templates.json`, row extents only):

| body | south / north bbox (x, y) | east bbox (x, y) |
|---|---|---|
| Male | x38–89, y44–106 | x43–86, y43–106 |
| Female | x40–88, y39–112 | x36–81, y39–112 |
| Thin | x51–77, y43–107 | x43–77, y45–106 |
| Hulk | x26–101, y32–125 | x27–95, y36–124 |
| Fat | x23–102, y38–112 | x23–99, y38–113 |
| Average head | x41–87, y39–88 (head texture space) | x39–89, y40–87 |

Vanilla armor footprints are the extent of opaque pixels:

| texture | south (x, y) | east (x, y) | north (x, y) |
|---|---|---|---|
| PowerArmor (marine) Male | x30–97, y39–111 | x35–89, y38–112 | x30–97, y39–109 |
| PowerArmor Female | x38–90, y40–110 | x36–81, y37–110 | x37–91, y40–110 |
| PowerArmor Thin | x38–89, y39–111 | x41–79, y40–112 | x38–89, y39–109 |
| PowerArmor Hulk | x21–105, y32–127 | x23–98, y33–126 | x21–105, y31–127 |
| PowerArmor Fat | x20–106, y35–120 | x21–104, y34–116 | x21–107, y35–116 |
| ReconArmor Male | x38–88, y42–109 | x41–85, y42–109 | x38–89, y40–107 |
| PlateArmor Male | x29–98, y42–109 | x37–91, y37–106 | x30–98, y43–108 |
| FlakVest Male | x41–85, y45–95 | x41–83, y46–94 | x41–85, y43–92 |
| PrestigeMarineArmor Male (256 → 128) | x24–103, y32–112 | x33–91, y38–113 | x24–103, y35–109 |

What this means in practice:

- Marine shoulder pads extend only **~8 px** past the body on each side.
- The armor's top edge sits only ~4 px above the body's top (y39 against y43), so pads never climb
  up beside the helmet.
- Recon armor stays inside the body silhouette.
- Hulk armor touches the bottom edge, so do the same there.

Helmet footprints (head texture space):

| helmet | south (x, y) | east (x, y) |
|---|---|---|
| PowerArmorHelmet | x38–89, y36–89 | x36–87, y36–88 |
| ReconHelmet | x34–92, y34–88 | x33–87, y32–89 |
| CataphractHelmet | x37–90, y33–92 | x33–94, y35–92 |
| AdvancedHelmet | x37–90, y35–75 | x34–94, y35–73 |
| SimpleHelmet | x35–93, y30–68 | x34–94, y31–69 |

**How vanilla marine armor is built** (measured row by row on PowerArmor and ReconArmor in all
5 body types; the generator's `marine_kit` follows it):

- **Shell.** One shell covers the upper torso and **hugs the body**. Its coloured edge stays
  within about -4 to +4 px of the naked silhouette, and the ~4 px outline does the rest. Its top
  follows the body's own rounded shoulders. It bulges slightly at the chest and pinches under it
  into the belt. The per-body offsets are in `rwtex/data/armor_fit.json`: the Thin shell adds
  bulk, the Hulk and Female shells sit slightly inside the body, and the Female torso is short,
  with a dark skirt below short tassets.
- **Neck.** The neck hole is large: about 0.33 × the shoulder half-width + 4 px wide and 0.115 ×
  the body height tall. It is near-black (#333), with a black ring and a light #ccc lip that is
  thickest at the front.
- **Chest plate.** The chest plate runs from the lip to the belt and is white. It has 5 px #ccc
  chamfer facets on its sides and a notch for the belt node. It is separated from the white flank
  strips by a black-dark-black seam (`#d#`).
- **Belt.** The belt is near-black with two dark segments and a round dark node in the centre. It
  sits **lower at the front than at the back**, which is what makes it a diagonal in the east
  view.
- **Tassets.** The centre tasset (about 0.35 × hip width, white, split at the top around the node)
  and the narrow #ccc side tassets at the silhouette edge are separated by wide near-black gaps.
- **East view.**
  - The shell's side face is #ccc and its front-top is cut on a diagonal, where the head sits.
  - A big pauldron covers the front half of the torso side, with a white front facet and a #ccc
    side facet.
  - Below are a #ccc thigh plate at the back and a narrow white front tasset.
- **North view.** Everything is a step darker. The #ccc shell is split by a narrow spine plate
  whose seams fan out toward the shoulders, the hip plates are #999, and the belt and gaps are
  dark.
- **Marine helmet.** The shell follows the head silhouette, inset about 1.5 px. It has a top slot,
  a brow V-crease down to the nose bridge, and a T-shaped visor. The visor is **transparent**,
  framed by the outline, and shows the pawn's eyes. In the east view, a diagonal seam splits the
  #999 side and back from a lighter front.

**Why marine, recon and cataphract read so well:**

- Shapes: a few large plates. There is a V or yoke chest plate, a foreshortened neck ring and a
  belt that bows with the body. Pads are flared. Tassets are split and splayed.
- Tones: the white shell is what takes the colour (vanilla multiplies the whole texture; prestige
  armor and this generator use a red mask). The dark undersuit shows only in the gaps
  (armpits, waist, between tassets). Each plate has 2–3 flat facet tones.
- Detail: panel lines are sparse and follow the form.
- Recon is slimmer with segmented abdomen plates. Cataphract is bulkier, with a raised pad line,
  heavier chest facets and a crested, slit-visored helmet.

## 7. Masks and shaders

- **CutoutComplex**: the mask's red channel takes `colorOne` (stuff, ideology or the primary
  colour) and the green channel takes `colorTwo`. Black leaves the texture unchanged. The maths is
  `out = lerp(lerp(tex, tex*colorOne, R), tex*colorTwo, G)`, which is implemented in
  `rwtex/color.py:cutout_complex`.
- Paint colourable regions **white or light grey** so the tint multiplies cleanly.
- **Mask names**:

  | graphic | texture | mask |
  |---|---|---|
  | `Graphic_Single` | `Name.png` | `Name_m.png` |
  | `Graphic_Multi` (apparel) | `Name_south.png` | `Name_southm.png` |
  | body apparel | `Name_Male_south.png` | `Name_Male_southm.png` |

- To mask apparel, add `<shaderType>CutoutComplex</shaderType>` to `graphicData` and
  `<useWornGraphicMask>true</useWornGraphicMask>` to `<apparel>`.
- **Persona weapons** (bladelink) are the normal texture multiplied by a whole-texture
  `graphicData` colour. The wiki image matches about (0.97, 0.78, 0.79), a dark pink. This is
  `TINTS['persona']`. Vanilla Expanded's persona weapons copy it.

## 8. QA checklist

`python -m rwtex lint` checks each of these.

- [ ] The size is a power of two, and the canvas is 128 unless the mod uses 64.
- [ ] The outer outline is pure black and about 3 px (items) or 3.5–4 px (apparel) thick.
- [ ] Transparent pixels have black RGB.
- [ ] Each material uses 2–4 flat tones, with no noise and no soft gradients on flat parts.
- [ ] Orientation: melee has the tip on the right, ranged has the muzzle on the right with the bore
      centred, and bows stand upright.
- [ ] Apparel exists for all 5 body types × 3 directions, plus a ground icon. The footprint
      matches the vanilla tables above.
- [ ] Masks are pure red or green on black, and the colourable regions are painted light.
- [ ] Check the item in context at 1×, on the dirt colour, next to a vanilla item. Its silhouette
      should be readable at 64 px.
