"""Search tags for assets and Pixel Forge builders.

Tags are English only: lower case ASCII, words joined with "-" (``fire``, ``top-down``, ``action:walk``).
``normalize_tags`` is applied whenever an asset is saved, so tags typed in another language are dropped
(the UI labels are translated; tags stay English so search works the same for everyone).

``BUILDER_TAGS`` gives every Pixel Forge builder its tags (scene, monster, skill element …); they are listed in the
Forge gallery search and copied onto every asset the builder makes."""
from __future__ import annotations

import re

_SEP = re.compile(r"[\s_/]+")
_BAD = re.compile(r"[^a-z0-9:\-_]")
MAX_LEN = 40


def normalize_tag(tag) -> str | None:
    """'Top Down' → 'top-down'; non-English (non-ASCII) tags → None. Underscores are kept (builder ids use them)."""
    if not isinstance(tag, str):
        return None
    t = tag.strip().lower()
    if not t or any(ord(c) > 127 for c in t):
        return None
    t = re.sub(r"\s+", "-", t)
    t = _BAD.sub("", t).strip("-:")
    t = re.sub(r"-{2,}", "-", t)
    return t[:MAX_LEN] or None


def normalize_tags(tags) -> list[str]:
    """Normalise, drop non-English/empty tags, de-duplicate, keep first-seen order."""
    out, seen = [], set()
    for t in tags or []:
        n = normalize_tag(t)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


# Shared vocabularies (documented in docs/asset-packs.md).
SKILL = ["skill", "effect"]
SPELL = ["skill", "spell", "magic", "effect"]
SCENE = ["scenery", "scene", "environment"]

BUILDER_TAGS: dict[str, list[str]] = {
    # items / scenery
    "potion": ["item", "consumable", "potion", "loot", "glass"],
    "chest": ["scenery", "dungeon", "prop", "chest", "treasure", "loot", "container", "top-down"],
    "chest_open": ["scenery", "dungeon", "prop", "chest", "treasure", "loot", "open", "animated"],
    "hero_shrine": SCENE + ["dungeon", "temple", "shrine", "altar", "prop", "holy", "save-point"],
    # skills (top-down / side effects)
    "fireball": SPELL + ["fire", "projectile", "attack", "damage"],
    "sword_slash": SKILL + ["melee", "slash", "sword", "physical", "attack"],
    "ice_spear": SPELL + ["ice", "frost", "projectile", "attack", "pierce"],
    "heal": SPELL + ["holy", "heal", "support", "restore"],
    "buff_aura": SPELL + ["buff", "aura", "support", "status"],
    "lightning_strike": SPELL + ["lightning", "electric", "thunder", "attack", "strike"],
    "shield_barrier": SPELL + ["shield", "barrier", "defense", "buff", "support"],
    "frost_nova": SPELL + ["ice", "frost", "nova", "aoe", "attack"],
    "poison_cloud": SPELL + ["poison", "toxic", "cloud", "aoe", "debuff", "dot"],
    "lava_burn": SPELL + ["fire", "lava", "ground", "aoe", "grid", "top-down", "dot"],
    "meteor": SPELL + ["fire", "meteor", "aoe", "grid", "top-down", "attack"],
    "fire_pillar": SPELL + ["fire", "pillar", "grid", "top-down", "attack"],
    "earth_spike": SPELL + ["earth", "rock", "spike", "grid", "top-down", "attack"],
    "whirlpool": SPELL + ["water", "whirlpool", "aoe", "grid", "top-down", "control"],
    "gale": SPELL + ["wind", "air", "tornado", "grid", "top-down", "attack"],
    "ice_field": SPELL + ["ice", "frost", "ground", "aoe", "grid", "top-down", "control"],
    "holy_judgment": SPELL + ["holy", "light", "aoe", "grid", "top-down", "attack"],
    "dark_vortex": SPELL + ["dark", "shadow", "void", "aoe", "grid", "top-down", "attack"],
    "life_drain": SPELL + ["dark", "blood", "drain", "lifesteal", "grid", "top-down"],
    # icons
    "weapon_icon": ["icon", "item", "equipment", "weapon", "inventory"],
    "armor_icon": ["icon", "item", "equipment", "armor", "inventory"],
    "consumable_icon": ["icon", "item", "consumable", "potion", "inventory"],
    "material_icon": ["icon", "item", "material", "crafting", "inventory"],
    "skill_icon": ["icon", "skill", "ui", "ability"],
    "status_icon": ["icon", "status", "buff", "debuff", "ui"],
    # UI kit
    "ui_panel": ["ui", "panel", "window", "dialog", "9-slice"],
    "ui_button": ["ui", "button"],
    "ui_bar": ["ui", "bar", "hp", "mp", "gauge"],
    "ui_frame": ["ui", "frame", "portrait", "slot"],
    "ui_icon": ["ui", "icon", "hud"],
    # characters (preset-specific tags come from preset_tags below)
    "character_kit": ["character", "humanoid", "four-direction", "top-down"],
}

# character_kit presets → tags. Hero classes vs monsters, so "monster" finds the necromancer and the skeleton.
PRESET_TAGS: dict[str, list[str]] = {
    "base": ["hero", "human"],
    "knight": ["hero", "human", "knight", "melee", "sword", "shield", "armor"],
    "mage": ["hero", "human", "mage", "caster", "magic", "staff"],
    "ranger": ["hero", "human", "ranger", "archer", "bow", "ranged"],
    "priest": ["hero", "human", "priest", "healer", "caster", "holy", "staff"],
    "berserker": ["hero", "human", "berserker", "melee", "axe"],
    "necromancer": ["monster", "enemy", "necromancer", "caster", "undead", "dark", "dungeon", "boss"],
    "skeleton": ["monster", "enemy", "skeleton", "undead", "melee", "sword", "shield", "dungeon"],
}


def builder_tags(builder: str, params: dict | None = None) -> list[str]:
    """Tags for an asset made by `builder` with `params` (includes the builder id itself)."""
    params = params or {}
    tags = ["procedural", builder] + BUILDER_TAGS.get(builder, [])
    if builder == "character_kit":
        preset = params.get("preset") or "base"
        tags += PRESET_TAGS.get(preset, []) + [preset]
        if params.get("action"):
            tags.append("action:" + str(params["action"]).lower())
    for key in ("element", "theme", "kind", "variant"):   # common builder params that are good search words
        v = params.get(key)
        if isinstance(v, str):
            tags.append(v)
    return normalize_tags(tags)
