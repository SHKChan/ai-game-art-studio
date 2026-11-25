"""Procedural builders for Engine A. Each builder is a deterministic generator of pixel-engine tool
calls (DESCRIPTION, PARAMS, ASSET_TYPE, build(**params) -> list[call]). The engine executes them,
stores the layered document and records its own replayable `doc.recipe`."""
from importlib import import_module

_NAMES = ["potion", "chest", "chest_open", "fireball", "sword_slash", "ice_spear"]
BUILDERS = {}
for _n in _NAMES:
    try:
        BUILDERS[_n] = import_module(f"{__name__}.{_n}")
    except ModuleNotFoundError as _e:  # builder not present in this build
        if _e.name != f"{__name__}.{_n}":
            raise
