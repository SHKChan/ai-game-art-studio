"""Procedural builders for Pixel Forge. Each builder is a deterministic generator of pixel-engine tool
calls (DESCRIPTION, PARAMS, ASSET_TYPE, build(**params) -> list[call]). The engine executes them,
stores the layered document and records its own replayable `doc.recipe`."""
from importlib import import_module

_NAMES = ["potion", "chest", "chest_open", "fireball", "sword_slash", "ice_spear", "hero_shrine",
          "heal", "buff_aura", "lightning_strike", "shield_barrier", "frost_nova", "poison_cloud",
          # v0.6 — top-down grid skills, JRPG item / skill / status icons
          "lava_burn", "meteor", "fire_pillar", "earth_spike", "whirlpool", "gale", "ice_field", "holy_judgment",
          "dark_vortex", "life_drain",
          "weapon_icon", "armor_icon", "consumable_icon", "material_icon", "skill_icon", "status_icon",
          # v0.6 — UI kit
          "ui_panel", "ui_button", "ui_bar", "ui_frame", "ui_icon",
          # v0.7 — character kit (Craftpix base + class costumes; needs the local base pack)
          "character_kit"]
BUILDERS = {}
for _n in _NAMES:
    try:
        BUILDERS[_n] = import_module(f"{__name__}.{_n}")
    except ModuleNotFoundError as _e:  # builder not present in this build
        if _e.name != f"{__name__}.{_n}":
            raise
