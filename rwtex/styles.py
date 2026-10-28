"""Style lexicon loader.  See ``rwtex/data/lexicon.yaml`` and docs/STYLE_LEXICON.md."""
from __future__ import annotations

import copy
import os
from typing import Any, Dict, List, Optional, Union

from .materials import Material, get as getmat
from .render import Bevel

_HERE = os.path.dirname(os.path.abspath(__file__))
LEXICON_PATH = os.path.join(_HERE, 'data', 'lexicon.yaml')


def _load_yaml(path: str) -> dict:
    try:
        import yaml  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise SystemExit('PyYAML is required: pip install pyyaml') from e
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


class Style:
    """A resolved visual language."""

    def __init__(self, key: str, data: dict):
        self.key = key
        self.data = data
        self.label: str = data.get('label', key)
        self.tech_level: str = data.get('tech_level', '')
        self.aka: List[str] = data.get('aka', [])
        self.summary: str = data.get('summary', '')
        self.shape: Dict[str, Any] = dict(data.get('shape', {}))
        self.materials: Dict[str, Optional[str]] = dict(data.get('materials', {}))
        self.shading: Dict[str, Any] = dict(data.get('shading', {}))
        self.motifs: List[str] = list(data.get('motifs', []))
        self.glow: str = data.get('glow', 'none')
        self.tiers: Dict[str, dict] = dict(data.get('tiers', {}))

    # access -----------------------------------------------------------------------------------
    def mat(self, role: str, fallback: Optional[str] = None) -> Material:
        name = self.materials.get(role) or fallback
        if name is None:
            raise KeyError(f'style {self.key} has no material for role {role!r}')
        return getmat(name)

    def has_mat(self, role: str) -> bool:
        return bool(self.materials.get(role))

    def s(self, key: str, default: Any = None) -> Any:
        return self.shape.get(key, default)

    def has(self, motif: str) -> bool:
        return motif in self.motifs

    @property
    def corners(self) -> str:
        return self.shape.get('corners', 'chamfered')

    @property
    def corner_px(self) -> float:
        return float(self.shape.get('corner_px', 1.5))

    def bevel(self, scale: float = 1.0, **kw) -> Bevel:
        return Bevel(self.shading.get('bevel_light', 1.4) * scale, self.shading.get('bevel_shade', 1.6) * scale, **kw)

    def wants_split(self) -> bool:
        return bool(self.shading.get('split', False))

    def override(self, **changes) -> 'Style':
        d = copy.deepcopy(self.data)
        for k, v in changes.items():
            if isinstance(v, dict) and isinstance(d.get(k), dict):
                d[k].update(v)
            else:
                d[k] = v
        return Style(self.key, d)

    def __repr__(self) -> str:
        return f'Style({self.key})'


_CACHE: Dict[str, Any] = {}


def lexicon() -> dict:
    if 'lex' not in _CACHE:
        _CACHE['lex'] = _load_yaml(LEXICON_PATH)
    return _CACHE['lex']


def all_styles() -> Dict[str, Style]:
    lex = lexicon()
    return {k: Style(k, v) for k, v in lex['styles'].items()}


def get(spec: Union[str, dict, Style, None]) -> Style:
    """Resolve a style by key/alias, or a dict ``{'base': 'ultratech', 'materials': {...}}``."""
    if isinstance(spec, Style):
        return spec
    styles = all_styles()
    if spec is None:
        return styles['industrial']
    if isinstance(spec, dict):
        base = get(spec.get('base', 'industrial'))
        changes = {k: v for k, v in spec.items() if k != 'base'}
        return base.override(**changes)
    key = str(spec).strip().lower().replace(' ', '_').replace('-', '_')
    if key in styles:
        return styles[key]
    for s in styles.values():
        if key in [a.lower().replace(' ', '_').replace('-', '_') for a in s.aka] or key == s.label.lower():
            return s
    raise KeyError(f'unknown style {spec!r}; known: {", ".join(styles)}')


TECH_ORDER = ['neolithic', 'medieval', 'industrial', 'spacer', 'ultratech', 'archotech']
