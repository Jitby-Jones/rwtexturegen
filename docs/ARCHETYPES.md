# Archetypes and the spec / parts API

Each archetype is a *function* (sword, rifle, armor...) that reads a **style** from the lexicon
and returns a `Scene`, or an `ApparelSet` for worn apparel. Every argument is optional. When you
leave one out, the style's default is used, so you set only what makes your item unique.

```python
from rwtex.archetypes import build
scene = build('sword', style='archotech', name='MyBlade')       # -> rwtex.render.Scene
scene.render().save('MyBlade.png')                               # 128 px RGBA
```

Common arguments:

| argument | meaning |
|---|---|
| `style` | A lexicon key or alias (`ultratech`, `ultra`, `DMS`, `VE`...), or a dict `{base: ultratech, materials: {...}, shape: {...}}` to override parts of a style. |
| `size` | Canvas size in px, 128 by default. Every measurement scales by `size / 128`. |
| `seed` | Seed for any randomised detail (knapping, scratches...). |
| `name` | The texture name, used for output files. |
| `mats` | A role → material map, e.g. `{blade: plasteel, grip: leather}`. Run `python -m rwtex list materials` to see the choices. |
| `outline` | The outer outline width in px. The default is 3 px at 128. |

## sword

The blade lies horizontally, with the pommel on the left and the tip on the right. The `ultratech`
defaults reproduce the vanilla monosword exactly.

| parameter | values |
|---|---|
| `blade` | `flared` (monosword), `straight`, `leaf`, `wavy`, `serrated`, `tanto`, `clip`, `curved`, `cleaver`, `knapped`, `stepped`, `jagged`, `scythe` |
| `guard` | `none`, `block`, `cross`, `crescent`, `ring`, `disc`, `wing`, `claw`, `nested`, `carapace`, `finger` |
| `grip` | `plain`, `wrapped`, `segmented`, `lashed`, `ribbed`, `riveted`, `frame`, `twisted` |
| `pommel` | `round`, `disc`, `diamond`, `fishtail`, `cap`, `ring`, `spike`, `knob`, `cube`, `butt` |
| `motif` (blade decoration) | `none`, `line` (mono-edge), `dashes`, `dots`, `double`, `wedge`, `ring`, `split`, `circuit`, `conduit`, `ichor`, `fuller` |
| geometry | `blade_h` (14), `grip_len` (30), `guard_w` / `guard_h` (5.5 / 18), `pommel_s`, `x_start` (7), `x_tip` (122.5), `curve`, `flare`, `taper`, `tip_len`, `teeth`, `waves`, `notches` (list of `(t, depth, width)`), `facet` (lower-facet split, 0.43) |
| motif placement | `motif_t` (start and end along the blade, `(0.023, 0.535)`), `motif_width`, `motif_offset`, `motif_mat` |
| extras | `glow` (material for an emissive halo), `led`, `trim`, `trim_mask` |

Material roles: `blade`, `guard`, `grip`, `wrap`, `pommel`, `energy`. Set `trim`, `glow` and `motif_mat` per item.

## polearm

The haft is horizontal with the head on the right, like the vanilla spear, ikwa and zeushammer.

| parameter | values |
|---|---|
| `head` | `spear`, `glaive`, `axe`, `hammer` |
| `butt` | `none`, `cap`, `spike`, `cube` |
| `bands` | the number of grip bands |
| geometry | `haft_h` (4.5), `x_start` (6), `head_x` (86), `x_tip` (123), `head_h` |
| `motif`, `glow` | same as for the sword |

Material roles: `head`, `haft`, `band`, `socket`, `butt`, `accent`, `energy`.

## rifle (`ranged` in the matrix)

The rifle is horizontal with the muzzle on the right and the bore at y = 63.5. The layout is
measured from the vanilla assault rifle.

| parameter | values |
|---|---|
| `stock` | `none`, `fixed`, `skeletal`, `wood`, `block`, `sleek`, `stepped` |
| `receiver` | `ar`, `ak`, `block`, `sleek`, `stepped`, `wedge` |
| `grip` | `angled`, `none` |
| `mag` | `none`, `curved`, `straight`, `box`, `cell`, `cells` (charge cells), `drum` |
| `handguard` | `round`, `rail`, `shroud`, `sleek`, `stepped` |
| `sight` | `none`, `carry`, `iron`, `dot`, `scope` |
| `muzzle` | `none`, `flash`, `brake`, `emitter`, `spikes` |
| `extras` | a list of `vents`, `rivets`, `bipod`, `conduit`, `ichor`, `fragments`, `edge_line`, `gold_trim`, `circuit` |
| `length` | overall length factor (1.0 is the assault rifle; 0.93 is shorter) |
| `bore_y`, `x_muzzle` | layout anchors |
| `mask_parts` | the parts to paint white and mask red, making them colourable like Odyssey unique weapons, e.g. `[stock, handguard]` |

Material roles: `stock`, `receiver`, `upper`, `grip`, `mag`, `handguard`, `barrel`, `sight`,
`muzzle`, `energy`, `trim`, `ammo`.

## bow

`kind` is one of `short`, `recurve` or `long` (drawn upright), or `crossbow` or `compound`
(horizontal). Material roles: `limb`, `stock`, `grip`, `string`, `tip`.

## armor (body apparel) → `ApparelSet`

One design renders **5 body types × 3 directions + a ground icon**, and a mask for each.

| parameter | values |
|---|---|
| `design` | 3D-form designs (perspective-correct, recommended): `marine`, `recon`, `cataphract`, `bionic`. Older 2D designs: `plate`, `tribal`, `flak`, `monolith`, `exo`. |
| `mats` | A role map. Roles are `shell`, `undersuit`, `strap`, `accent`, `trim`, `energy`, `joint` and `lens`. |
| `mask_roles` | The roles masked red for stuff or ideology tint. The default is `('shell',)`; pass `()` for an unmasked armor. |
| `body_types`, `dirs` | Subsets to render. All are rendered by default. |
| `ground`, `ground_scale` (1.3), `ground_body` (`Male`) | Ground icon settings. |
| design options | `fibers: true` (DMS muscle-fibre undersuit, for marine and cataphract), `fins: false` (cataphract), `glow: false` (bionic: no cyan nodes), `trim_gold: true`, `spikes: true` |
| `design_fn` | Your own design function `f(c: Ctx)`. See *Custom apparel* below. |

The output files are `Name_<BodyType>_<dir>.png`, plus `Name_<BodyType>_<dir>m.png`, `Name.png`
and `Name_m.png`.

## helmet → `ApparelSet`

| parameter | values |
|---|---|
| `design` | 3D-form designs: `marine`, `recon`, `cataphract`, `bionic`. Others: `helm` (barrel helm), `ballistic`, `mask` (tribal face plate), `gasmask`, `monolith`. |
| options | `crest: true` (cataphract and imperial), `glow` (bionic) |

The output files are `Name_<dir>.png`, plus `Name_<dir>m.png`, `Name.png` and `Name_m.png`.

## bionic_part (Bionic Icons language, 64 px)

| parameter | values |
|---|---|
| `tier` | `prosthetic`, `prosthetic_advanced`, `bionic`, `bionic_advanced`, `archotech`, `archotech_module`, `ultratech`, `synthetic`, `surrogate`, `organic` |
| `part` | `arm`, `shoulder`, `leg`, `hand`, `eye`, `heart`, `lung`, `spine`, `kidney`, `liver`, `stomach`, `jaw`, `brain`, `ear`, `generic` |
| `mask` | `true` renders a neutral case plus a CutoutComplex mask (R = case, G = pictogram) |
| `case`, `strip` | override the tier's materials |

---

## Spec files

YAML or JSON (`python -m rwtex new <archetype> --name X --style Y` writes a starter):

```yaml
name: PersonaMonosword_Tidewarden      # texture / output base name
archetype: sword
style: ultratech
size: 128
seed: 0
params: {blade: straight, curve: 4, guard: crescent, grip: segmented, pommel: ring, motif: split}
output:
  dir: output/weapons/PersonaMonosword_Tidewarden
  tex_path: Things/Item/Equipment/WeaponMelee/PersonaMonosword_Tidewarden
  mask: auto            # auto | true | false
  svg: true
preview:
  tints: {persona: persona}        # names from TINTS / STUFF, or [r, g, b]
  stuff: [Plasteel, Gold]          # stuff swatches (shown only when a mask exists)
xml: {def_name: MeleeWeapon_PersonaMonosword_Tidewarden, melee: true, tint: persona}
items:                             # optional extra textures rendered into the same folder
  - {name: Other, archetype: rifle, params: {...}}
```

A **Python spec** (`.py`) defines `SPEC` (the same keys, minus `archetype`) and
`build(spec) -> Scene | ApparelSet | list`. Use one for compositions that no archetype covers;
`specs/arc_glaive_halcyon.py` is a full example. `python -m rwtex build` treats both kinds the
same way.

## Parts API (Python)

```python
from rwtex import geom as G
from rwtex.parts import common as C, melee as ML
from rwtex.render import Scene, Part, Bevel, Split, Facets, Dome, Gradient, Rim, Line, Fill, Glow

s = Scene(128, name='Thing')                           # light_angle=-105, outline=3 px @128
p = s.add('body', G.chamfer(G.rect(20, 56, 100, 72), 3), 'gunmetal', z=1,
          shading=[Bevel(1.5, 1.8), Split(at=0.6, tone='shade')])
p.detail(*C.vent_slots(56, 58, 90, 66, 5))             # motifs return Line/Fill details
p.line([(24, 60), (96, 60)], 0.8, 'deep')              # engraved line, clipped to the part
p.fill(G.circle(30, 64, 2), 'led_cyan.base', mask=None)
s.add('cell', G.rounded(G.rect(70, 72, 84, 84), 2), 'charge_cell', z=0)   # lower z = behind
img = s.render(); mask = s.render_mask(); svg = s.to_svg()
```

- **Colour references** (`ColorRef`) can be a tone of the part's own material (`'light'`, `'base'`,
  `'shade'`, `'deep'`, `'line'`, `'spec'`), another material's tone (`'mono_cyan.base'`), a hex
  string or an RGB tuple.
- **Masks**: `mask='r'` makes a part tint with colorOne and `'g'` with colorTwo. The default,
  `'material'`, uses the material's own mask setting (`armor_white`, `tint_white` and `ceramic` are
  red).
- **Geometry**: the main helpers are `rect`, `poly`, `circle`, `ellipse`, `capsule`, `rounded`,
  `chamfer`, `bezier`, `qbezier`, `spline` and the `Path` builder. Transforms are `translate`,
  `scale`, `rotate` and `mirror_x`/`mirror_y`. `offset` grows or shrinks a shape; `taper`, `strip`,
  `wobble` and `zigzag` are also available.
- **Motifs** (`rwtex/parts/common.py`): `vent_slots`, `rivets`, `screws`, `seam`, `diag_bands`,
  `wrap_lines`, `ring_lines`, `grain`, `circuit`, `led`, `hazard_stripes`, `chevron`, `scratches`,
  `knap_facets` and `spikes_along`.
- **Melee parts** (`rwtex/parts/melee.py`): `blade_geom`, `blade_part`, `guard_part`, `grip_part`,
  `pommel_part` and `edge_motif`. These are the building blocks of the sword archetype, so a custom
  spec can mix them freely.

### Custom apparel

Pass `design_fn=f` to `armor()` or `helmet()`. It is called once per body type and direction
with a `Ctx` object:

- `c.scene`: the scene to add to.
- `c.form`: the 3D proxy, `TorsoForm` or `HeadForm`.
- `c.dir`, `c.bt`: the direction and body type.
- `c.k`: the scale factor.
- `c.m(role)`: the material for a role.
- `c.front`, `c.side`, `c.back`: which way the view faces.

The perspective-correct helpers are in `rwtex/archetypes/armor3d.py`:

- `splate(c, name, poly_theta_v, z, role, r, cols, rows, ...)` is a plate patch in surface
  coordinates. `theta` runs around the body (0 = front, +π/2 = the pawn's right side, π = back)
  and `v` runs down from the shoulders (0) to the bottom (1). The patch is projected into each
  view and flat-shaded per facet.
- `slab(c, name, face, z, depth)` is an extruded rigid plate, such as a shoulder pad, whose
  thickness faces are lit.
- `sline`, `sjoint`, `collar` and `fibers` add surface lines, bionic joint caps, the neck ring
  and muscle striations.
- `hpanel(...)` is the head equivalent, with `(theta, phi)` coordinates.

Copy `d3_marine` or `h3_marine` as a starting point, then register the result with
`DESIGNS['name'] = fn` or `HELMET_DESIGNS['name'] = fn`.
