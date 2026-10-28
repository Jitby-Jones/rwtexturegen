"""Materials: named 4-tone ramps calibrated against vanilla RimWorld textures.

Every material has ``base`` (flat fill), ``light`` (lit edge / upper facet), ``shade``
(lower facet), ``deep`` (grooves, recesses) plus ``line`` for engraved detail lines and
an optional ``spec`` glint.  Values were sampled from Ludeon's public art source
(see docs/STYLE_GUIDE.md for the measurements) or from the mods named in comments.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, Optional, Union

from .color import RGB, ColorLike, ramp, rgb, to_hex

BLACK: RGB = (0.0, 0.0, 0.0)
WHITE: RGB = (1.0, 1.0, 1.0)


@dataclass
class Material:
    name: str
    base: RGB
    light: RGB
    shade: RGB
    deep: RGB
    line: RGB
    spec: Optional[RGB] = None
    mask: Optional[str] = None        # default CutoutComplex channel: 'r' primary, 'g' secondary
    emissive: bool = False            # bright/self-lit; never tinted; may drive a glow pass
    glow: Optional[RGB] = None        # colour of the halo/bloom when emissive
    note: str = ''

    def tone(self, key: str) -> RGB:
        if key in ('base', 'light', 'shade', 'deep', 'line'):
            return getattr(self, key)
        if key == 'spec':
            return self.spec or self.light
        if key == 'glow':
            return self.glow or self.light
        if key == 'black':
            return BLACK
        if key == 'white':
            return WHITE
        raise KeyError(f'unknown tone {key!r} for material {self.name}')

    def with_mask(self, mask: Optional[str]) -> 'Material':
        return replace(self, mask=mask)

    def describe(self) -> str:
        return ' '.join(f'{k}={to_hex(getattr(self, k))}' for k in ('base', 'light', 'shade', 'deep'))


def make(name: str, base: ColorLike, light: ColorLike | None = None, shade: ColorLike | None = None,
         deep: ColorLike | None = None, line: ColorLike | None = None, spec: ColorLike | None = None,
         mask: Optional[str] = None, emissive: bool = False, glow: ColorLike | None = None,
         note: str = '') -> Material:
    r = ramp(base)
    b = rgb(base)
    lt = rgb(light) if light is not None else r['light']
    sh = rgb(shade) if shade is not None else r['shade']
    dp = rgb(deep) if deep is not None else r['deep']
    ln = rgb(line) if line is not None else dp
    return Material(name, b, lt, sh, dp, ln, rgb(spec) if spec is not None else None, mask, emissive,
                    rgb(glow) if glow is not None else None, note)


M: Dict[str, Material] = {}


def _reg(m: Material) -> Material:
    M[m.name] = m
    return m


# --- universal ---------------------------------------------------------------------------
_reg(make('outline', '#000000', '#000000', '#000000', '#000000', note='vanilla outlines are pure black'))

# --- stuff-tintable (paint white/grey so graphicData colour / stuff colour multiplies) ---
_reg(make('tint_white', '#f2f2f2', '#ffffff', '#cccccc', '#a6a6a6', '#8c8c8c', mask='r',
          note='Odyssey unique-weapon colourable parts: #fff/#f2f2f2/#ccc'))
_reg(make('blade_white', '#ffffff', '#ffffff', '#dddddd', '#bdbdbd', '#a8a8a8', mask='r',
          note='vanilla melee blades: white top facet, #ddd lower facet (monosword, longsword)'))
_reg(make('armor_white', '#fcfcfc', '#ffffff', '#cccccc', '#a3a3a3', '#8a8a8a', mask='r',
          note='marine/recon/cataphract shells #fcfcfc / #c8ccc8 / #bcbcbc'))

# --- industrial ------------------------------------------------------------------------
_reg(make('gunmetal', '#666666', '#919191', '#4d4d4d', '#333333', '#3a3a3a',
          note='vanilla receivers: #666 base, #919191 light, #4d4d4d shade'))
_reg(make('steel_bright', '#9a9a9a', '#c2c2c2', '#757575', '#555555'))
_reg(make('polymer', '#222222', '#3a3a3a', '#161616', '#0b0b0b', '#090909',
          note='vanilla assault rifle furniture #222 with #333/#444 highlights'))
_reg(make('rubber', '#2e2e2e', '#444444', '#222222', '#151515'))
_reg(make('wood', '#9c5c40', '#b06c4c', '#744430', '#503024', '#5e3828', note='bolt-action/shotgun stock'))
_reg(make('wood_dark', '#7c4c38', '#8c5438', '#684438', '#4a2e22', note='LMG furniture'))
_reg(make('tan', '#cdb27c', '#e0caa0', '#a88e5e', '#7e6a44', note='VWE battle rifle FDE'))
_reg(make('olive_drab', '#6b7347', '#848c5c', '#545a37', '#3b3f26', note='VWE carbine / DMS uniforms'))
_reg(make('brass', '#c49a3c', '#e0c060', '#9a7428', '#6a4f1a', note='ammo, fittings (minigun, DMS belts)'))
_reg(make('leather', '#6e4a32', '#86603f', '#573a27', '#3e291b'))
_reg(make('cloth_khaki', '#a89466', '#c0ac7c', '#8a784e', '#5e5236'))

# --- spacer ------------------------------------------------------------------------------
_reg(make('charge_cell', '#738542', '#9dad5a', '#5c6b35', '#434f27', note='charge rifle olive cells'))
_reg(make('spacer_grey', '#7a7a7a', '#a0a0a0', '#5e5e5e', '#3e3e3e'))
_reg(make('plasteel', '#a0b2b5', '#c6d4d6', '#7f9193', '#5c6b6d', note='plasteel stuff colour (160,178,181)'))
_reg(make('mono_grip', '#646464', '#949494', '#4a4a4a', '#313131', note='vanilla monosword grip #636563 / top #313431'))
_reg(make('mono_guard', '#969696', '#a8a8a8', '#898989', '#4b4b4b', note='vanilla monosword guard #949294 / #898789 / #4a4d4a'))
_reg(make('mono_blade', '#ffffff', '#ffffff', '#dedede', '#949494', '#cdcdcd', mask='r',
          note='vanilla monosword blade #fff / #dedfde, edge #aaa top #949494 bottom, split #cecbce'))
_reg(make('mono_edge', '#2986a5', '#c0dae3', '#318ea5', '#1d6680', emissive=True, glow='#5cc0e0',
          note='vanilla monosword cyan #2986a5 (bulb #318ea5, glint #c0dae3)'))
_reg(make('undersuit', '#303030', '#444444', '#262626', '#1a1a1a', '#1a1a1a', note='armor undersuit/joints'))
_reg(make('visor_dark', '#2c2c2c', '#4a4a4a', '#1e1e1e', '#121212'))
_reg(make('lens_teal', '#303a3d', '#4b5b60', '#232a2c', '#151a1b', note='vanilla bionic eye lens'))
_reg(make('led_cyan', '#59a2b9', '#8fd0e2', '#3f8296', '#2a6070', emissive=True, glow='#7fd6ee',
          note='monosword mono-edge line #59a2b9 / #5b9fb4'))

# --- ultratech -----------------------------------------------------------------------------
_reg(make('ceramic', '#f4f6f7', '#ffffff', '#c9cfd2', '#9aa3a8', '#8a9398', mask='r'))
_reg(make('graphite', '#3c4044', '#575c61', '#2c2f32', '#1c1e20', note='zeushammer head'))
_reg(make('teal_steel', '#5e7f7c', '#86a8a3', '#47615f', '#2f4240', note='zeushammer facets'))
_reg(make('mono_cyan', '#2a8fa8', '#5cc0d8', '#1f6f84', '#164f5e', emissive=True, glow='#5cc8e8',
          note='VE persona monosword details'))
_reg(make('cyan_glow', '#5fd8ff', '#c8f6ff', '#2aa6d6', '#1a7aa6', emissive=True, glow='#5fd8ff'))
_reg(make('plasma', '#fc9030', '#fcc044', '#e07020', '#b05010', emissive=True, glow='#ffa040',
          note='plasmasword blade #fc9030 with #fcb840 core'))
_reg(make('violet_glow', '#b070ff', '#e0c4ff', '#8040d8', '#5a28a0', emissive=True, glow='#b070ff'))

# --- imperial (Royalty) -------------------------------------------------------------------
_reg(make('imperial_gold', '#b4983c', '#d4b84c', '#88702c', '#584c1c', note='prestige armor trim #b4983c'))
_reg(make('imperial_purple', '#5a3a6e', '#74518a', '#452c55', '#2e1d39'))

# --- mechanoid -----------------------------------------------------------------------------
_reg(make('mech_taupe', '#8c7868', '#9c8c84', '#706458', '#4c4038', note='charge blaster / inferno cannon'))
_reg(make('mech_pale', '#a9ad9c', '#bcc0b4', '#848874', '#545444', note='lancer shell'))
_reg(make('mech_conduit', '#a4b4bc', '#d2e4ea', '#7a8a92', '#56646a', note='pale blue conduit line'))
_reg(make('mech_red', '#fc4838', '#ff8a7a', '#cc4438', '#8a2a22', emissive=True, glow='#ff5040',
          note='diabolus / apocriton lights'))

# --- archotech -----------------------------------------------------------------------------
_reg(make('archo_olive', '#8a8e6a', '#a9ac86', '#767a5a', '#5a5e46', note='archotech structures #848864/#949470'))
_reg(make('archo_frame', '#444444', '#585c58', '#333333', '#222222'))
_reg(make('archo_sage', '#9ba594', '#b4bcaf', '#7f8879', '#5c6457', note='vanilla archotech HealthItem colour (155,165,148)'))
_reg(make('archo_yellow', '#e6d53a', '#fff27a', '#b5b73f', '#8a8a2a', emissive=True, glow='#f2e45a',
          note='archotech circuit traces / archotech eye #dedf42'))

# --- bionics (Bionic Icons + vanilla HealthItem tier colours) ------------------------------
_reg(make('bionic_khaki', '#bda976', '#d4c494', '#a08e5e', '#7a6c46', note='vanilla bionic (189,169,118)'))
_reg(make('prosthetic_mauve', '#9a7c68', '#b09482', '#806654', '#5e4a3e', note='vanilla prosthetic (154,124,104)'))
_reg(make('ultratech_case', '#c8c8c8', '#e2e2e2', '#a8a8a8', '#7e7e7e'))
_reg(make('glow_green', '#4be03c', '#b4ff9c', '#2fa828', '#1f6e1a', emissive=True, glow='#5bf04a'))
_reg(make('glow_mint', '#bff2d0', '#f2fff6', '#8fd0a8', '#5e9a74', emissive=True, glow='#c8ffd8'))
_reg(make('glow_yellow', '#eedc3c', '#fff59a', '#c0ae22', '#857818', emissive=True, glow='#f6e650'))
_reg(make('glow_orange', '#f07a2a', '#ffb070', '#c45a18', '#8a3c10', emissive=True, glow='#ff8a3a'))
_reg(make('glow_purple', '#9a3ce0', '#cf9cff', '#7426b0', '#4e1878', emissive=True, glow='#a850ff'))
_reg(make('glow_red', '#e03a3a', '#ff8a8a', '#b02424', '#741616', emissive=True, glow='#ff4a4a'))

# --- neolithic / medieval ------------------------------------------------------------------
_reg(make('bone', '#e8e0c8', '#f8f2e0', '#c8bea0', '#9a9070'))
_reg(make('hide', '#a0764c', '#b88c60', '#82603c', '#5e4428'))
_reg(make('sinew', '#c8b48a', '#ddcca6', '#a8946c', '#7a6a4a'))
_reg(make('iron_dark', '#4a4a4a', '#6a6a6a', '#3a3a3a', '#262626'))
_reg(make('feather_red', '#b84a3a', '#d06a58', '#943a2e', '#62251e'))

# --- anomaly -------------------------------------------------------------------------------
_reg(make('bioferrite', '#645050', '#806868', '#4c3c3c', '#2c2424', note='stuff colour (100,80,80)'))
_reg(make('void_black', '#2a2626', '#3e3838', '#1c1a1a', '#0e0d0d'))
_reg(make('flesh', '#b06a6a', '#c88a84', '#8a4c4c', '#5e3030'))

# --- Dead Man's Switch (AOBA) --------------------------------------------------------------
_reg(make('dms_gunmetal', '#5c5c5c', '#7a7a7a', '#474747', '#333333', note='DMS mech/weapon greys'))
_reg(make('dms_steel', '#8a8a8a', '#a8a8a8', '#6e6e6e', '#4e4e4e'))
_reg(make('dms_olive', '#5e6444', '#747a56', '#4a4f35', '#34382a'))
_reg(make('hazard_yellow', '#d4a22a', '#e8c048', '#a87e1c', '#6e5212'))
_reg(make('muscle_fiber', '#3a3a3a', '#545454', '#2a2a2a', '#1a1a1a', '#161616', note='DMS bionic suit'))

# --- stuff colours (multiply onto white textures; from the RimWorld wiki infoboxes) --------
STUFF: Dict[str, RGB] = {k: rgb(v) for k, v in {
    'Steel': (102, 102, 105), 'Plasteel': (160, 178, 181), 'Uranium': (100, 100, 100),
    'Gold': (255, 235, 122), 'Silver': (180, 173, 150), 'Jade': (85, 118, 69), 'Wood': (133, 97, 67),
    'Granite': (105, 95, 97), 'Marble': (132, 135, 132), 'Slate': (70, 70, 70), 'Hyperweave': (0, 106, 126),
    'Devilstrand': (180, 60, 60), 'Bioferrite': (100, 80, 80), 'Obsidian': (50, 50, 50),
}.items()}

# multiply tints observed in-game
TINTS: Dict[str, RGB] = {
    # persona (bladelink) weapons render with a pink multiply; measured from the wiki image
    'persona': (0.97, 0.78, 0.79),
    'none': (1.0, 1.0, 1.0),
}

MaterialLike = Union[str, Material, dict]


def get(m: MaterialLike) -> Material:
    """Resolve a material: registry name, '#hex' (auto ramp), dict, or Material."""
    if isinstance(m, Material):
        return m
    if isinstance(m, dict):
        d = dict(m)
        name = d.pop('name', 'custom')
        if 'from' in d:  # derive from a registry material with overrides
            src = get(d.pop('from'))
            over = {k: (rgb(v) if k in ('base', 'light', 'shade', 'deep', 'line', 'spec', 'glow') and v is not None else v)
                    for k, v in d.items()}
            return replace(src, name=name, **over)
        return make(name, **d)
    if isinstance(m, str):
        if m in M:
            return M[m]
        if m.startswith('#'):
            return make(m, m)
    raise KeyError(f'unknown material {m!r}; known: {", ".join(sorted(M))}')
