# Mod house styles

These are the mod art families the generator can match, with what makes each one recognisable.
Each one has a style in the lexicon (`dms`, `bionic`, `vanilla_expanded`) or is covered by
materials and parameters. All references are cited for style only; no mod art is included.

## Dead Man's Switch (DMS)

*AOBA. Steam Workshop 3121742525. DMS 2 is 3819799478 and needs Fortified Features Framework
(3498575851).*

**Theme**: the ancient colonial army of the "Nara Interstellar" colonisation forces, in a
1990s-cyberpunk, military-industrial look. Mechs are walkers and automatroids rather than insectoid
mechanoids.

| aspect | DMS read |
|---|---|
| silhouette | Chunky rectangular masses. **Every corner has a 45° chamfer.** The outline is thick and black. |
| surface | Recessed **slot vents** (3–6 horizontal slots), rivet dots, panel seams and small diagonal scratch highlights. |
| palette | Gunmetal greys `#5c5c5c` / `#7a7a7a` / `#474747`, steel `#8a8a8a`, olive drab `#5e6444`, cargo khaki `#a89466`, **hazard yellow** `#d4a22a` (construction mechs, chevrons). Brass ammo is the only warm accent. |
| weapons | Long, detailed real-world heavy weapons (GAU, M2, Barrett style) that stay flat grey. They have boxy receivers, skeletal stocks, box magazines, bipods and muzzle brakes. |
| bionic suit | A black **artificial-muscle fibre** suit (`#3a3a3a`) with abdominal and pectoral segmentation and a segmented spine on the back. The head is a white, featureless mask. |
| don't | Glossy ultratech curves, large glows. Lamps are tiny and orange. |

In the generator: `style: dms`, with materials `dms_gunmetal`, `dms_steel`, `dms_olive`,
`hazard_yellow`, `brass` and `muscle_fiber`; motifs `vent_slots`, `rivets`, `chevron`,
`hazard_stripes` and `scratches`; and the `fibers` option on the 3D armor designs.

## EPOE-Forked (Expanded Prosthetics and Organ Engineering, forked)

*Aurani/EPOE-Forked v4.3.5. Steam Workshop 1949064302.* This is the **current** version of EPOE.
The original EPOE art is outdated, so do not match it.

The item art is a 384 px tier box, an isometric crate with a coloured band. Tier colours:

| tier | colour |
|---|---|
| SimplePart (vanilla prosthetic) | `#3f6182` |
| BionicPart (vanilla bionic) | `#68648b` |
| BasicProsthesis | `#855714` |
| AdvancedPart | `#1f8e00` |
| SyntheticPart | `#8500ab` |
| SurrogatePart | `#cb6a2e` |
| GlitterworldPart | `#cd704b`, with gold token `#f0f008` |
| box greys | `#bdbdbd` / `#aeaeae` / `#9e9c9d` |

Use these colours when an item has to sit in an EPOE-Forked tier. For the item **icons**
themselves, follow Bionic Icons, described next.

## Bionic Icons

*AUTOMATIC1111/BionicIcons, MIT licence. Steam Workshop 1677616980.* **This is the reference for
all bionic art in this repo.**

- **Case**: a 64 px rounded case seen from the front. A darker lid band runs along the bottom, and
  the tier strip glows inside it.
- **Pictogram**: one solid silhouette per part (arm, leg, hand, eye, heart, lung, kidney, liver,
  stomach, spine, jaw, ear, brain), engraved darker into the case face.
- **Mask**: CutoutComplex with R = case and G = pictogram. `colorIcon` defaults to
  (0.25, 0.25, 0.25), so the pictogram is multiplied dark.
- **Tiers** are shown by case colour and strip colour, never by the pictogram:

  | tier | case | strip |
  |---|---|---|
  | Prosthetic | mauve-brown (154,124,104) | none |
  | Prosthetic advanced | mauve-brown | green |
  | Bionic | khaki (189,169,118) | none |
  | Bionic advanced | khaki | green |
  | Archotech | sage (155,165,148) | mint |
  | Archotech module | sage | yellow, plus yellow circuit traces |
  | Ultratech | light grey | cyan |
  | Synthetic | light grey | purple |
  | Surrogate | light grey | orange |
  | Organic | light grey | red |
  | Cosmetic | pink | |
  | Medieval | wood crate | |

- **On the pawn**, bionics are clean light-grey metal. The vanilla bionic eye overlay is a plate
  in `#a0a0a0` / `#e8e8e8` with a black ring and a `#303a3d` lens. The archotech eye is sage
  `#525c4f` / `#737963` with a glowing yellow `#dedf42` swirl.

In the generator: `archetype: bionic_part` with `tier` and `part`. Add `mask: true` for the
CutoutComplex version. `python -m rwtex matrix bionic_part` shows every tier and pictogram. The
bionic armor's eye and joint caps use the same palette.

## Vanilla Expanded (VE)

*Oskar Potocki and team: VWE, VAE, VFE, VPWE.*

- **House rule**: stay deliberately vanilla. Use the same outline weight, grey ramps and
  proportions at 128 px. VE content has to sit next to vanilla unnoticed.
- **Weapons (VWE)**: there are many more real-world references (battle rifle, service rifle,
  carbine, HMG). Variety comes from **swapping modules** (stock, handguard, optic), not new
  rendering. Common colours are tan/FDE `#cdb27c` and olive drab `#6b7347`.
- **Armour (VAE)**: the light and heavy marine armors follow the vanilla marine grammar exactly,
  with white masked shells, dark undersuit gaps and few facets.
- **Persona weapons (VPWE)**: these are modular. The persona monosword is assembled from
  Blade / Guard / Grip / Detail layers (×15 each, with separate `_Outline` layers, at 256 px). The
  persona tint is a dark pink, "just like vanilla persona weapons". Detail cyan is about
  `#2a8fa8` on white blades.

In the generator: `style: vanilla_expanded`, or vanilla-faithful parameters on any archetype. The
sword archetype is modular in the same way (`blade`, `guard`, `grip`, `pommel` and `motif` are
independent), which is how the Tidewarden persona variant was built.
