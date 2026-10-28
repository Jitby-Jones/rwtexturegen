"""Functional archetypes: the same *function* (sword, rifle, armor...) rendered in any style.

Each builder takes ``style`` plus optional overrides and returns a :class:`~rwtex.render.Scene`
(or an :class:`~rwtex.archetypes.apparel.ApparelSet` for worn apparel).
"""
from __future__ import annotations

from typing import Callable, Dict

REGISTRY: Dict[str, Callable] = {}


def register(name: str):
    def deco(fn):
        REGISTRY[name] = fn
        fn.archetype_name = name
        return fn
    return deco


def build(archetype: str, **kw):
    if archetype not in REGISTRY:
        raise KeyError(f'unknown archetype {archetype!r}; known: {", ".join(sorted(REGISTRY))}')
    return REGISTRY[archetype](**kw)


from . import sword, polearm, rifle, bow, apparel, armor3d, bionic  # noqa: E402,F401  (registration)
