"""Functional archetypes: the same *function* (sword, rifle, armor...) rendered in any style.

Each builder takes ``style`` plus optional overrides and returns a :class:`~rwtex.render.Scene`
(or an :class:`~rwtex.archetypes.apparel.ApparelSet` for worn apparel).
"""
from __future__ import annotations

import inspect
import warnings
from typing import Callable, Dict

REGISTRY: Dict[str, Callable] = {}

# free-form design options understood by the armor / helmet designs (everything else is a typo)
APPAREL_OPTIONS = {'fibers', 'glow', 'crest', 'trim_gold', 'spikes', 'mask_roles'}


def register(name: str):
    def deco(fn):
        REGISTRY[name] = fn
        fn.archetype_name = name
        return fn
    return deco


def unknown_params(archetype: str, kw: dict) -> list:
    """Keyword arguments an archetype would silently ignore (usually misspelled knobs)."""
    fn = REGISTRY[archetype]
    sig = inspect.signature(fn)
    named = {n for n, p in sig.parameters.items() if p.kind not in (p.VAR_KEYWORD, p.VAR_POSITIONAL)}
    extra = [k for k in kw if k not in named]
    if archetype in ('armor', 'helmet'):
        extra = [k for k in extra if k not in APPAREL_OPTIONS]
    return sorted(extra)


def build(archetype: str, **kw):
    if archetype not in REGISTRY:
        raise KeyError(f'unknown archetype {archetype!r}; known: {", ".join(sorted(REGISTRY))}')
    bad = unknown_params(archetype, kw)
    if bad:
        warnings.warn(f'{archetype}: unknown parameter(s) {", ".join(bad)} are ignored - see docs/ARCHETYPES.md',
                      stacklevel=2)
    return REGISTRY[archetype](**kw)


from . import sword, polearm, rifle, bow, apparel, armor3d, bionic  # noqa: E402,F401  (registration)
