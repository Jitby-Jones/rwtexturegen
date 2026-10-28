# Style lexicon

> Generated from `rwtex/data/lexicon.yaml` by `python -m rwtex styles --markdown docs/STYLE_LEXICON.md`.
> Edit the YAML, not this file.

A **style** is a reusable visual language: a shape grammar (corners, irregularity, bulk, taper, ornament),
material roles mapped to calibrated palettes, decoration motifs and do/don't rules. Every archetype
(`sword`, `polearm`, `rifle`, `bow`, `armor`, `helmet`, `bionic_part`) reads the style, so the *same
functional design* can be rendered at any tech level: `python -m rwtex matrix sword`.

## Quick reference

| style | tech level | one-line read | corners | key materials | signature motifs |
|---|---|---|---|---|---|
| **neolithic** | Neolithic | Hand-made from wood, bone, stone and hide. | organic | primary:tint_white, accent:sinew | lashing, knap_facets, wood_grain, beads |
| **medieval** | Medieval | Forged steel shapes with clean geometric edges, leather-wrapped grips, crossguards and round pommels. | sharp | primary:blade_white, accent:brass | fuller, leather_wrap, rivets, crossguard |
| **industrial** | Industrial | Real-world-inspired machinery. | chamfered | primary:gunmetal, accent:wood | screws, rails, ejection_port, stencil |
| **spacer** | Spacer | Chunky manufactured sci-fi. | chamfered | primary:spacer_grey, accent:charge_cell, energy:led_cyan | vent_slots, charge_cells, panel_seams, status_led |
| **ultratech** | Ultra | Sleek, precise and minimal. | rounded | primary:ceramic, accent:teal_steel, energy:mono_cyan | edge_line, node_dots, seam_lines, emitter |
| **archotech** | Archotech | Impossible precision. | monolithic | primary:archo_olive, accent:archo_sage, energy:archo_yellow | nested_blocks, circuit_traces, vias, floating_fragments |
| **imperial** | Ultra | Ultratech or spacer gear dressed for the Empire. | rounded | primary:armor_white, accent:imperial_gold, energy:mono_cyan | gold_trim, crest, laurel_fan, plume |
| **mechanoid** | Spacer | Alien war machines. | faceted | primary:mech_taupe, accent:mech_conduit, energy:mech_red | carapace_plates, conduit_line, vent_slots, sensor_eye |
| **anomaly** | Industrial | Wrongness. | jagged | primary:bioferrite, accent:flesh, energy:glow_red | spikes, cracks, veins, ichor_line |
| **dms** | Industrial | Ancient colonial-army hardware. | chamfered | primary:dms_gunmetal, accent:brass, energy:glow_orange | vent_slots, rivets, chevrons, scratches |
| **bionic** | Spacer | Body-part items as tier-coloured rounded cases with an engraved organ pictogram and a glowing tier strip, following the Bionic Icons mod. | rounded | primary:bionic_khaki, accent:lens_teal, energy:glow_green | tier_strip, pictogram, lid_band |
| **vanilla_expanded** | any | House style that stays deliberately vanilla - same outline weight, gray ramps and proportions at 128px - but with more real-world references and modular variants (VE persona weapons are assembled from Blade/Guard/Grip/Detail layers). | chamfered | primary:gunmetal, accent:tan, energy:mono_cyan | screws, rails, modular_parts |

## Same function, different tech level

How each archetype changes per style (defaults; every knob can be overridden in a spec).

| style | sword (blade / guard / grip / pommel / motif) | ranged | polearm head | armor design | helmet design |
|---|---|---|---|---|---|
| neolithic | knapped / none / lashed / knob / none | bow | spear | tribal | mask |
| medieval | straight / cross / wrapped / round / fuller | crossbow | axe | plate | helm |
| industrial | clip / finger / riveted / cap / none | fixed stock, ar receiver, curved mag, round handguard | axe | flak | ballistic |
| spacer | tanto / block / segmented / cap / none | block stock, block receiver, cells mag, shroud handguard | hammer | marine | marine |
| ultratech | flared / block / plain / butt / line | sleek stock, sleek receiver, cell mag, sleek handguard | hammer | cataphract | cataphract |
| archotech | stepped / nested / frame / cube / circuit | stepped stock, stepped receiver, none mag, stepped handguard | glaive | monolith | monolith |
| imperial | flared / wing / wrapped / diamond / line | sleek stock, sleek receiver, cell mag, sleek handguard | glaive | cataphract | cataphract |
| mechanoid | scythe / carapace / plain / spike / conduit | none stock, wedge receiver, none mag, shroud handguard | glaive | marine | marine |
| anomaly | jagged / claw / twisted / spike / ichor | wood stock, ak receiver, curved mag, round handguard | axe | marine | helm |
| dms | cleaver / block / ribbed / cap / hazard | skeletal stock, block receiver, box mag, rail handguard | axe | exo | gasmask |
| bionic | tanto / block / segmented / cap / none | block stock, block receiver, cells mag, shroud handguard | - | bionic | bionic |
| vanilla_expanded | flared / block / plain / butt / line | fixed stock, ar receiver, straight mag, rail handguard | - | marine | marine |

## Material roles

- **primary** - Main mass - blade, shell plates, receiver body. Usually the stuff-tintable / colourable area.
- **secondary** - Structural frame - receiver, haft, chassis, guard.
- **grip** - Hand contact - grips, wraps, stocks, straps.
- **accent** - Small coloured functional parts - cells, caps, pads.
- **trim** - Decorative edging - gold, brass, filigree.
- **energy** - Emissive parts - mono-edges, cells, glow strips, sensor eyes.
- **dark** - Recesses, vents, undersuits, bores.
- **lens** - Optics, visors, sensor lenses.

## Neolithic (`neolithic`)

*Tech level:* Neolithic &nbsp; *Aliases:* tribal, primitive, stone age, animist

Hand-made from wood, bone, stone and hide. Lashed joins, uneven edges, earthy browns, stuff-tinted heads.

**Shape grammar**

| knob | value |
|---|---|
| corners | organic |
| corner_px | 2.5 |
| irregularity | 0.65 |
| bulk | 1.05 |
| taper | 0.55 |
| ornament | 0.25 |
| segmentation | 0.2 |

**Materials**

| role | material |
|---|---|
| primary | `tint_white` #f2f2f2 |
| secondary | `wood` #9c5c40 |
| grip | `hide` #a0764c |
| accent | `sinew` #c8b48a |
| trim | `feather_red` #b84a3a |
| energy | - |
| dark | `wood_dark` #7c4c38 |
| lens | - |

**Motifs:** lashing, knap_facets, wood_grain, beads &nbsp; **Glow:** none

**Palette notes:** Wood #9c5c40/#744430, hide #a0764c, sinew #c8b48a. Heads stay near-white so stuff colour (flint, jade, bone) tints them.

**Do**

- Wrap every join with 2-4 diagonal lashing bands in sinew/hide.
- Let silhouettes wobble - no perfectly parallel edges, chipped knapped facets on stone.
- Keep wood hafts slightly bent or knotted; one or two grain strokes are enough.

**Don't**

- No screws, rivets, perfect circles or symmetric machined bevels.
- No metal greys outside of stuff-tinted heads; no glow.

**Vanilla references:** Club, Spear, Ikwa, Short bow, Recurve bow, Great bow, Pilum, Tribalwear, War mask, Tribal headdress
**Mod references:** VWE Longbow, VWE Throwing rocks

## Medieval (`medieval`)

*Tech level:* Medieval &nbsp; *Aliases:* forged, smithed, plate, feudal

Forged steel shapes with clean geometric edges, leather-wrapped grips, crossguards and round pommels. Stuff-tinted metal.

**Shape grammar**

| knob | value |
|---|---|
| corners | sharp |
| corner_px | 1.0 |
| irregularity | 0.15 |
| bulk | 1.0 |
| taper | 0.6 |
| ornament | 0.3 |
| segmentation | 0.4 |

**Materials**

| role | material |
|---|---|
| primary | `blade_white` #ffffff |
| secondary | `iron_dark` #4a4a4a |
| grip | `leather` #6e4a32 |
| accent | `brass` #c49a3c |
| trim | `brass` #c49a3c |
| energy | - |
| dark | `iron_dark` #4a4a4a |
| lens | - |

**Motifs:** fuller, leather_wrap, rivets, crossguard &nbsp; **Glow:** none

**Palette notes:** Blades white/#ddd split facet (stuff tints them), iron hilts #4a4a4a, leather #6e4a32, brass #c49a3c fittings.

**Do**

- Use a white blade with a hard two-tone split (top light, bottom #ddd) and a thin fuller line.
- Crossguards and pommels are simple geometric solids (bar, disc, ball).
- Plate armor = overlapping lames with rivet dots and visible leather straps.

**Don't**

- No electronics, panel seams, glow or polymer black.

**Vanilla references:** Longsword, Gladius, Mace, Steel axe, Warhammer, Plate armor, Simple helmet
**Mod references:** VWE Poleaxe, VWE Battle axe, VAE Light plate armor, VAE Plate helmet

## Industrial (`industrial`)

*Tech level:* Industrial &nbsp; *Aliases:* modern, firearm, 20th century, colony tech

Real-world-inspired machinery. Gunmetal #666 receivers, polymer #222 furniture or wood stocks, screws, rails and stamped plates.

**Shape grammar**

| knob | value |
|---|---|
| corners | chamfered |
| corner_px | 1.5 |
| irregularity | 0.05 |
| bulk | 1.0 |
| taper | 0.2 |
| ornament | 0.05 |
| segmentation | 0.6 |

**Materials**

| role | material |
|---|---|
| primary | `gunmetal` #666666 |
| secondary | `polymer` #222222 |
| grip | `polymer` #222222 |
| accent | `wood` #9c5c40 |
| trim | `brass` #c49a3c |
| energy | - |
| dark | `polymer` #222222 |
| lens | `lens_teal` #303a3d |

**Motifs:** screws, rails, ejection_port, stencil, stitching, pouches &nbsp; **Glow:** none

**Palette notes:** Exact vanilla gun ramp: #222 furniture, #333/#444 highlights, #666 receiver, #919191 lit edge, #4d4d4d shade. Wood #9c5c40. Olive drab #6b7347 and tan #cdb27c for variants.

**Do**

- Read as a recognisable real firearm silhouette (AR, AK, bullpup, LMG) at 64px.
- Use small rectangular details - ejection port, charging handle, screw dots - in the deep tone.
- Flak/ballistic apparel = soft olive/khaki vests with pouches and stitching lines.

**Don't**

- No glowing parts, no seamless curves, no ornament.

**Vanilla references:** Assault rifle, Revolver, Autopistol, Pump shotgun, Bolt-action rifle, LMG, Heavy SMG, Sniper rifle, Minigun, Flak vest, Flak jacket, Simple helmet
**Mod references:** VWE Battle rifle, VWE Service rifle, VWE Carbine, VWE HMG, DMS heavy weapons

## Spacer (`spacer`)

*Tech level:* Spacer &nbsp; *Aliases:* glitterworld, plasteel, charge, power armor, marine

Chunky manufactured sci-fi. Chamfered grey bodies with olive charge cells, black vent slots, white tintable power-armor shells over dark undersuits.

**Shape grammar**

| knob | value |
|---|---|
| corners | chamfered |
| corner_px | 3.0 |
| irregularity | 0.0 |
| bulk | 1.1 |
| taper | 0.25 |
| ornament | 0.1 |
| segmentation | 0.7 |

**Materials**

| role | material |
|---|---|
| primary | `spacer_grey` #7a7a7a |
| secondary | `gunmetal` #666666 |
| grip | `polymer` #222222 |
| accent | `charge_cell` #738542 |
| trim | `steel_bright` #9a9a9a |
| energy | `led_cyan` #59a2b9 |
| dark | `undersuit` #303030 |
| lens | `visor_dark` #2c2c2c |

**Motifs:** vent_slots, charge_cells, panel_seams, status_led &nbsp; **Glow:** inline

**Palette notes:** Charge rifle: #666 body, #919191 lit facets, olive cells #738542/#9dad5a, black slots. Armor: #fcfcfc shells, #cccccc facets, #303030 undersuit, black T-visor.

**Do**

- Big chamfered (45 deg) corners and stacked rectangular volumes.
- Rows of black rounded vent slots; 1-3 olive charge cells.
- Power armor = broad yoke over the shoulders, chest plate, segmented abdomen, thigh plates, dark joints.

**Don't**

- No wood, no rivets, no ornate trim. Keep glow tiny (status LEDs) - charge weapons do not glow.

**Vanilla references:** Charge rifle, Charge lance, Marine armor, Marine helmet, Recon armor, Recon helmet, Advanced helmet
**Mod references:** VWE Charge LMG, VWE Charge sniper, VAE Light marine armor, VAE Trooper armor

## Ultratech (`ultratech`)

*Tech level:* Ultra &nbsp; *Aliases:* ultra, mono, plasma, glitterworld elite, persona

Sleek, precise and minimal. Smooth white ceramic or graphite with a single luminous accent line (cyan mono-edge, orange plasma). Fewer, larger, perfectly clean shapes.

**Shape grammar**

| knob | value |
|---|---|
| corners | rounded |
| corner_px | 2.0 |
| irregularity | 0.0 |
| bulk | 0.9 |
| taper | 0.35 |
| ornament | 0.15 |
| segmentation | 0.35 |

**Materials**

| role | material |
|---|---|
| primary | `ceramic` #f4f6f7 |
| secondary | `graphite` #3c4044 |
| grip | `graphite` #3c4044 |
| accent | `teal_steel` #5e7f7c |
| trim | `steel_bright` #9a9a9a |
| energy | `mono_cyan` #2a8fa8 |
| dark | `undersuit` #303030 |
| lens | `cyan_glow` #5fd8ff |

**Motifs:** edge_line, node_dots, seam_lines, emitter &nbsp; **Glow:** inline

**Palette notes:** Monosword: blade #fff/#dedede, cyan #2986a5 line with bulb dot, grip #646464, guard #969696. Plasma #fc9030/#fcc044. Zeushammer graphite #3c4044 + teal #5e7f7c.

**Do**

- One hero accent - a thin emissive line or blade that follows the form, ending in a node dot.
- Long uninterrupted surfaces; seams are single thin lines, not plates.
- Cataphract-style armor = large smooth shells, high pauldrons/back fins, slit visor.

**Don't**

- No rivets, vents rows, wood or grime; do not cover surfaces with greebles.
- Avoid more than one glow colour per item.

**Vanilla references:** Monosword, Plasmasword, Zeushammer, Persona weapons, Cataphract armor, Cataphract helmet, Locust armor, Phoenix armor
**Mod references:** VE Persona Weapons (modular blades/guards/grips/details), VWE Laser, VFE Deserters

## Archotech (`archotech`)

*Tech level:* Archotech &nbsp; *Aliases:* archite, archonexus, godlike, superintelligence

Impossible precision. Sage-olive monolithic blocks stacked like a city plan, dark frames, glowing yellow circuit traces ending in vias. Feels grown by a superintelligence, not built.

**Shape grammar**

| knob | value |
|---|---|
| corners | monolithic |
| corner_px | 0.5 |
| irregularity | 0.0 |
| bulk | 1.0 |
| taper | 0.15 |
| ornament | 0.6 |
| segmentation | 0.9 |

**Materials**

| role | material |
|---|---|
| primary | `archo_olive` #8a8e6a |
| secondary | `archo_frame` #444444 |
| grip | `archo_frame` #444444 |
| accent | `archo_sage` #9ba594 |
| trim | `archo_sage` #9ba594 |
| energy | `archo_yellow` #e6d53a |
| dark | `archo_frame` #444444 |
| lens | `archo_yellow` #e6d53a |

**Motifs:** nested_blocks, circuit_traces, vias, floating_fragments &nbsp; **Glow:** halo

**Palette notes:** Archotech structures: olive #848864/#949470/#7c7c5c, light #c0c0a0, frame #444444, traces #e6d53a. Archotech eye: sage #525c4f/#737963 with #dedf42 swirl. Archotech HealthItem tint (155,165,148).

**Do**

- Build forms from stepped rectilinear blocks of slightly different olive values.
- Run 1px yellow traces with right-angle turns, ending in round vias; add 1-3 bright nodes.
- Allow small detached fragments hovering beside the main form.

**Don't**

- No visible fasteners, no wear, no organic curves except the archotech eye swirl.
- Do not use cyan/white - that reads ultratech.

**Vanilla references:** Archotech eye, Archotech arm/leg (item tint), Archotech tower, Archonexus core, Archite capsule
**Mod references:** Bionic Icons archotech boxes (sage + mint strip, module = yellow traces)

## Imperial (`imperial`)

*Tech level:* Ultra &nbsp; *Aliases:* royalty, empire, prestige, noble, stellic

Ultratech or spacer gear dressed for the Empire. White shells with gold trim, crests, laurel fans and plumes; purple/regal accents.

**Shape grammar**

| knob | value |
|---|---|
| corners | rounded |
| corner_px | 2.0 |
| irregularity | 0.0 |
| bulk | 1.05 |
| taper | 0.35 |
| ornament | 0.85 |
| segmentation | 0.5 |

**Materials**

| role | material |
|---|---|
| primary | `armor_white` #fcfcfc |
| secondary | `graphite` #3c4044 |
| grip | `imperial_purple` #5a3a6e |
| accent | `imperial_gold` #b4983c |
| trim | `imperial_gold` #b4983c |
| energy | `mono_cyan` #2a8fa8 |
| dark | `undersuit` #303030 |
| lens | `visor_dark` #2c2c2c |

**Motifs:** gold_trim, crest, laurel_fan, plume &nbsp; **Glow:** inline

**Palette notes:** Prestige armor gold #b4983c / #88702c / #584c1c over #fcfcfc shells.

**Do**

- Keep the base item recognisable, then add gold crests, fan/laurel shapes behind the head, gold edging on pauldrons.
- Gold is NOT stuff-tinted: leave it out of the mask.

**Don't**

- Do not gild everything - 15-25% gold coverage at most.

**Vanilla references:** Prestige marine/recon/cataphract armor + helmets, Crown, Stellic crown, Coronet, Royal robe
**Mod references:** VAE Royal trooper/siegebreaker armor, VFE Empire

## Mechanoid (`mechanoid`)

*Tech level:* Spacer &nbsp; *Aliases:* mech, mechanoid hive, centipede, scyther, lancer

Alien war machines. Smooth pale-olive or taupe carapace shells, chamfered plate seams, dark sensor pits and red/pale-blue lights. Weapons look grown from armour plates.

**Shape grammar**

| knob | value |
|---|---|
| corners | faceted |
| corner_px | 3.0 |
| irregularity | 0.1 |
| bulk | 1.15 |
| taper | 0.5 |
| ornament | 0.2 |
| segmentation | 0.6 |

**Materials**

| role | material |
|---|---|
| primary | `mech_taupe` #8c7868 |
| secondary | `mech_pale` #a9ad9c |
| grip | `undersuit` #303030 |
| accent | `mech_conduit` #a4b4bc |
| trim | `mech_pale` #a9ad9c |
| energy | `mech_red` #fc4838 |
| dark | `undersuit` #303030 |
| lens | `mech_red` #fc4838 |

**Motifs:** carapace_plates, conduit_line, vent_slots, sensor_eye &nbsp; **Glow:** inline

**Palette notes:** Charge blaster taupe #8c7868/#9c8c84/#706458/#4c4038 with pale-blue conduit #a4b4bc. Lancer shell #a9ad9c/#bcc0b4. Lights #fc4838.

**Do**

- Wedge/kite silhouettes made of overlapping chamfered plates with an engraved central channel.
- One pale-blue conduit line or a pair of red lights; black slot vents along the sides.

**Don't**

- No human ergonomics (no pistol grips/stocks), no wood/polymer.

**Vanilla references:** Charge blaster, Heavy charge blaster, Inferno cannon, Needle gun, Lancer, Scyther, Centurion, Diabolus
**Mod references:** VFE Mechanoids, DMS automatroids (industrial variant)

## Anomaly (`anomaly`)

*Tech level:* Industrial &nbsp; *Aliases:* void, horax, dark, bioferrite, fleshwork, occult

Wrongness. Bioferrite and dark flesh-metal, jagged asymmetric spikes, twisted forms and a single thin red ichor glow.

**Shape grammar**

| knob | value |
|---|---|
| corners | jagged |
| corner_px | 1.0 |
| irregularity | 0.8 |
| bulk | 1.0 |
| taper | 0.7 |
| ornament | 0.4 |
| segmentation | 0.3 |

**Materials**

| role | material |
|---|---|
| primary | `bioferrite` #645050 |
| secondary | `void_black` #2a2626 |
| grip | `flesh` #b06a6a |
| accent | `flesh` #b06a6a |
| trim | `void_black` #2a2626 |
| energy | `glow_red` #e03a3a |
| dark | `void_black` #2a2626 |
| lens | `glow_red` #e03a3a |

**Motifs:** spikes, cracks, veins, ichor_line &nbsp; **Glow:** inline

**Palette notes:** Nerve spiker #585050/#343434/#706868/#4c2c2c with red #e03a3a line; bioferrite stuff (100,80,80); Horaxian weapons are white jagged (stuff-tinted).

**Do**

- Break symmetry, add barbs and hooks, let outlines zig-zag.
- Thin red line or slit as the only light.

**Don't**

- No clean panel seams or bright colours besides the red.

**Vanilla references:** Horaxian gladius/axe/mace/club/knife, Nerve spiker, Hellcat rifle, Twisted archotech support

## Dead Man's Switch (`dms`)

*Tech level:* Industrial &nbsp; *Aliases:* DMS, ancient military, 90s cyberpunk, automatroid, Nara Interstellar, colonization forces

Ancient colonial-army hardware. Boxy gunmetal with 45-degree chamfers, slot vents, rivet dots and brass ammo; olive drab, khaki and hazard-yellow variants; bio-mech bionic suits of black artificial muscle.

**Shape grammar**

| knob | value |
|---|---|
| corners | chamfered |
| corner_px | 3.5 |
| irregularity | 0.05 |
| bulk | 1.15 |
| taper | 0.15 |
| ornament | 0.1 |
| segmentation | 0.85 |

**Materials**

| role | material |
|---|---|
| primary | `dms_gunmetal` #5c5c5c |
| secondary | `dms_steel` #8a8a8a |
| grip | `polymer` #222222 |
| accent | `brass` #c49a3c |
| trim | `hazard_yellow` #d4a22a |
| energy | `glow_orange` #f07a2a |
| dark | `polymer` #222222 |
| lens | `visor_dark` #2c2c2c |

**Motifs:** vent_slots, rivets, chevrons, scratches, hazard_stripes, stencil, muscle_fibers &nbsp; **Glow:** none

**Palette notes:** Mech/weapon greys #5c5c5c/#7a7a7a/#474747, olive #5e6444, hazard #d4a22a, cargo khaki #a89466, brass ammo. Bionic suit = #3a3a3a muscle fibre + white faceless mask.

**Do**

- Chunky rectangular masses, every corner chamfered, recessed slot vents (3-6 horizontal slots).
- Small diagonal scratch highlights and rivet dots; brass ammo boxes/belts as the only warm accent.
- Heavy weapons are long and detailed (real-world: GAU, M2, Barrett) but still flat grey.

**Don't**

- No glossy ultratech curves, no glow beyond tiny lamps.

**Mod references:** DMS Bionic suit, Hazard suit, Battle Friends walker frame, Tarbosaurus/Iguana weapons, Geochelone

## Bionic (Bionic Icons) (`bionic`)

*Tech level:* Spacer &nbsp; *Aliases:* prosthetic, bionics, implant, body part, augment, Bionic Icons

Body-part items as tier-coloured rounded cases with an engraved organ pictogram and a glowing tier strip, following the Bionic Icons mod. On-pawn bionics are clean light-grey metal with dark teal lenses.

**Shape grammar**

| knob | value |
|---|---|
| corners | rounded |
| corner_px | 6.0 |
| irregularity | 0.0 |
| bulk | 1.0 |
| taper | 0.0 |
| ornament | 0.1 |
| segmentation | 0.3 |

**Materials**

| role | material |
|---|---|
| primary | `bionic_khaki` #bda976 |
| secondary | `steel_bright` #9a9a9a |
| grip | `undersuit` #303030 |
| accent | `lens_teal` #303a3d |
| trim | `steel_bright` #9a9a9a |
| energy | `glow_green` #4be03c |
| dark | `undersuit` #303030 |
| lens | `lens_teal` #303a3d |

**Motifs:** tier_strip, pictogram, lid_band &nbsp; **Glow:** inline

**Palette notes:** Vanilla HealthItem tints: prosthetic (154,124,104), bionic (189,169,118), archotech (155,165,148). Icon colour = (0.25,0.25,0.25) multiply. Bionic eye overlay: #a0a0a0/#e8e8e8 plate, black ring, #303a3d lens.

**Do**

- One pictogram per part (arm, leg, eye, heart, spine...) drawn as a solid silhouette, engraved darker into the case face.
- Encode tier by case colour + bottom strip glow, never by changing the pictogram.

**Don't**

- Don't use EPOE's flat isometric boxes for new bionic art - Bionic Icons is the reference.

**Tiers**

| tier | case | strip |
|---|---|---|
| prosthetic | `prosthetic_mauve` #9a7c68 | - |
| prosthetic_advanced | `prosthetic_mauve` #9a7c68 | `glow_green` #4be03c |
| bionic | `bionic_khaki` #bda976 | - |
| bionic_advanced | `bionic_khaki` #bda976 | `glow_green` #4be03c |
| archotech | `archo_sage` #9ba594 | `glow_mint` #bff2d0 |
| archotech_module | `archo_sage` #9ba594 | `glow_yellow` #eedc3c |
| ultratech | `ultratech_case` #c8c8c8 | `cyan_glow` #5fd8ff |
| synthetic | `ultratech_case` #c8c8c8 | `glow_purple` #9a3ce0 |
| surrogate | `ultratech_case` #c8c8c8 | `glow_orange` #f07a2a |
| organic | `ultratech_case` #c8c8c8 | `glow_red` #e03a3a |

**Vanilla references:** Bionic arm/leg/eye/spine/heart (HealthItem tints), Bionic eye overlay, Archotech eye overlay
**Mod references:** Bionic Icons (AUTOMATIC1111, MIT), EPOE-Forked tier colours (SimplePart #3f6182, BionicPart #68648b, AdvancedPart #1f8e00, SyntheticPart #8500ab)

## Vanilla Expanded (`vanilla_expanded`)

*Tech level:* any &nbsp; *Aliases:* VE, Oskar, VWE, VAE, VFE

House style that stays deliberately vanilla - same outline weight, gray ramps and proportions at 128px - but with more real-world references and modular variants (VE persona weapons are assembled from Blade/Guard/Grip/Detail layers).

**Shape grammar**

| knob | value |
|---|---|
| corners | chamfered |
| corner_px | 1.5 |
| irregularity | 0.05 |
| bulk | 1.0 |
| taper | 0.25 |
| ornament | 0.2 |
| segmentation | 0.6 |

**Materials**

| role | material |
|---|---|
| primary | `gunmetal` #666666 |
| secondary | `polymer` #222222 |
| grip | `polymer` #222222 |
| accent | `tan` #cdb27c |
| trim | `brass` #c49a3c |
| energy | `mono_cyan` #2a8fa8 |
| dark | `polymer` #222222 |
| lens | `lens_teal` #303a3d |

**Motifs:** screws, rails, modular_parts &nbsp; **Glow:** none

**Palette notes:** VWE uses tan #cdb27c, olive drab #6b7347, wood and the vanilla gun ramp; VPWE monosword details use cyan #2a8fa8 on white blades.

**Do**

- Match vanilla exactly; vary silhouettes by swapping modules (stock, handguard, optic, blade, guard).

**Don't**

- No new rendering tricks - VE content must sit beside vanilla unnoticed.

**Mod references:** Vanilla Weapons Expanded, Vanilla Armour Expanded, Vanilla Persona Weapons Expanded

## Materials catalogue

| material | base | light | shade | deep | notes |
|---|---|---|---|---|---|
| `archo_frame` | #444444 | #585c58 | #333333 | #222222 |  |
| `archo_olive` | #8a8e6a | #a9ac86 | #767a5a | #5a5e46 | archotech structures #848864/#949470 |
| `archo_sage` | #9ba594 | #b4bcaf | #7f8879 | #5c6457 | vanilla archotech HealthItem colour (155,165,148) |
| `archo_yellow` | #e6d53a | #fff27a | #b5b73f | #8a8a2a | archotech circuit traces / archotech eye #dedf42 |
| `armor_white` | #fcfcfc | #ffffff | #cccccc | #a3a3a3 | marine/recon/cataphract shells #fcfcfc / #c8ccc8 / #bcbcbc |
| `bioferrite` | #645050 | #806868 | #4c3c3c | #2c2424 | stuff colour (100,80,80) |
| `bionic_khaki` | #bda976 | #d4c494 | #a08e5e | #7a6c46 | vanilla bionic (189,169,118) |
| `blade_white` | #ffffff | #ffffff | #dddddd | #bdbdbd | vanilla melee blades: white top facet, #ddd lower facet (monosword, longsword) |
| `bone` | #e8e0c8 | #f8f2e0 | #c8bea0 | #9a9070 |  |
| `brass` | #c49a3c | #e0c060 | #9a7428 | #6a4f1a | ammo, fittings (minigun, DMS belts) |
| `ceramic` | #f4f6f7 | #ffffff | #c9cfd2 | #9aa3a8 |  |
| `charge_cell` | #738542 | #9dad5a | #5c6b35 | #434f27 | charge rifle olive cells |
| `cloth_khaki` | #a89466 | #c0ac7c | #8a784e | #5e5236 |  |
| `cyan_glow` | #5fd8ff | #c8f6ff | #2aa6d6 | #1a7aa6 |  |
| `dms_gunmetal` | #5c5c5c | #7a7a7a | #474747 | #333333 | DMS mech/weapon greys |
| `dms_olive` | #5e6444 | #747a56 | #4a4f35 | #34382a |  |
| `dms_steel` | #8a8a8a | #a8a8a8 | #6e6e6e | #4e4e4e |  |
| `feather_red` | #b84a3a | #d06a58 | #943a2e | #62251e |  |
| `flesh` | #b06a6a | #c88a84 | #8a4c4c | #5e3030 |  |
| `glow_green` | #4be03c | #b4ff9c | #2fa828 | #1f6e1a |  |
| `glow_mint` | #bff2d0 | #f2fff6 | #8fd0a8 | #5e9a74 |  |
| `glow_orange` | #f07a2a | #ffb070 | #c45a18 | #8a3c10 |  |
| `glow_purple` | #9a3ce0 | #cf9cff | #7426b0 | #4e1878 |  |
| `glow_red` | #e03a3a | #ff8a8a | #b02424 | #741616 |  |
| `glow_yellow` | #eedc3c | #fff59a | #c0ae22 | #857818 |  |
| `graphite` | #3c4044 | #575c61 | #2c2f32 | #1c1e20 | zeushammer head |
| `gunmetal` | #666666 | #919191 | #4d4d4d | #333333 | vanilla receivers: #666 base, #919191 light, #4d4d4d shade |
| `hazard_yellow` | #d4a22a | #e8c048 | #a87e1c | #6e5212 |  |
| `hide` | #a0764c | #b88c60 | #82603c | #5e4428 |  |
| `imperial_gold` | #b4983c | #d4b84c | #88702c | #584c1c | prestige armor trim #b4983c |
| `imperial_purple` | #5a3a6e | #74518a | #452c55 | #2e1d39 |  |
| `iron_dark` | #4a4a4a | #6a6a6a | #3a3a3a | #262626 |  |
| `leather` | #6e4a32 | #86603f | #573a27 | #3e291b |  |
| `led_cyan` | #59a2b9 | #8fd0e2 | #3f8296 | #2a6070 | monosword mono-edge line #59a2b9 / #5b9fb4 |
| `lens_teal` | #303a3d | #4b5b60 | #232a2c | #151a1b | vanilla bionic eye lens |
| `mech_conduit` | #a4b4bc | #d2e4ea | #7a8a92 | #56646a | pale blue conduit line |
| `mech_pale` | #a9ad9c | #bcc0b4 | #848874 | #545444 | lancer shell |
| `mech_red` | #fc4838 | #ff8a7a | #cc4438 | #8a2a22 | diabolus / apocriton lights |
| `mech_taupe` | #8c7868 | #9c8c84 | #706458 | #4c4038 | charge blaster / inferno cannon |
| `mono_blade` | #ffffff | #ffffff | #dedede | #949494 | vanilla monosword blade #fff / #dedfde, edge #aaa top #949494 bottom, split #cecbce |
| `mono_cyan` | #2a8fa8 | #5cc0d8 | #1f6f84 | #164f5e | VE persona monosword details |
| `mono_edge` | #2986a5 | #c0dae3 | #318ea5 | #1d6680 | vanilla monosword cyan #2986a5 (bulb #318ea5, glint #c0dae3) |
| `mono_grip` | #646464 | #949494 | #4a4a4a | #313131 | vanilla monosword grip #636563 / top #313431 |
| `mono_guard` | #969696 | #a8a8a8 | #898989 | #4b4b4b | vanilla monosword guard #949294 / #898789 / #4a4d4a |
| `muscle_fiber` | #3a3a3a | #545454 | #2a2a2a | #1a1a1a | DMS bionic suit |
| `olive_drab` | #6b7347 | #848c5c | #545a37 | #3b3f26 | VWE carbine / DMS uniforms |
| `outline` | #000000 | #000000 | #000000 | #000000 | vanilla outlines are pure black |
| `plasma` | #fc9030 | #fcc044 | #e07020 | #b05010 | plasmasword blade #fc9030 with #fcb840 core |
| `plasteel` | #a0b2b5 | #c6d4d6 | #7f9193 | #5c6b6d | plasteel stuff colour (160,178,181) |
| `polymer` | #222222 | #3a3a3a | #161616 | #0b0b0b | vanilla assault rifle furniture #222 with #333/#444 highlights |
| `prosthetic_mauve` | #9a7c68 | #b09482 | #806654 | #5e4a3e | vanilla prosthetic (154,124,104) |
| `rubber` | #2e2e2e | #444444 | #222222 | #151515 |  |
| `sinew` | #c8b48a | #ddcca6 | #a8946c | #7a6a4a |  |
| `spacer_grey` | #7a7a7a | #a0a0a0 | #5e5e5e | #3e3e3e |  |
| `steel_bright` | #9a9a9a | #c2c2c2 | #757575 | #555555 |  |
| `tan` | #cdb27c | #e0caa0 | #a88e5e | #7e6a44 | VWE battle rifle FDE |
| `teal_steel` | #5e7f7c | #86a8a3 | #47615f | #2f4240 | zeushammer facets |
| `tint_white` | #f2f2f2 | #ffffff | #cccccc | #a6a6a6 | Odyssey unique-weapon colourable parts: #fff/#f2f2f2/#ccc |
| `ultratech_case` | #c8c8c8 | #e2e2e2 | #a8a8a8 | #7e7e7e |  |
| `undersuit` | #303030 | #444444 | #262626 | #1a1a1a | armor undersuit/joints |
| `violet_glow` | #b070ff | #e0c4ff | #8040d8 | #5a28a0 |  |
| `visor_dark` | #2c2c2c | #4a4a4a | #1e1e1e | #121212 |  |
| `void_black` | #2a2626 | #3e3838 | #1c1a1a | #0e0d0d |  |
| `wood` | #9c5c40 | #b06c4c | #744430 | #503024 | bolt-action/shotgun stock |
| `wood_dark` | #7c4c38 | #8c5438 | #684438 | #4a2e22 | LMG furniture |
