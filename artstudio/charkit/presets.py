"""Class presets for the character kit: the plain base plus five fantasy classes (Tiny-RPG style)."""
from __future__ import annotations

PRESETS = {
    "base": ("male", None),
    "knight": ("male", {"hair": ("short", "brown"), "head": "helm", "head_ramp": "steel", "armor": "plate",
                        "tabard": "crimson", "cape": "crimson", "shirt": "grey", "pants": "grey", "boots": "brown",
                        "weapon": "steel"}),
    "mage": ("female", {"hair": ("long", "purple"), "head": "wizard", "head_ramp": "purple", "robe": "blue",
                        "trim": "gold", "robe_trim": "none", "pattern": "stars", "sash": "red", "shirt": "blue",
                        "pants": "blue", "boots": "brown", "weapon": ("staff", "brown", "blue", "orb")}),
    "ranger": ("male", {"hair": ("short", "brown"), "head": "hood", "head_ramp": "darkgreen", "armor": "leather",
                        "cape": "darkgreen", "shirt": "green", "pants": "brown", "boots": "brown", "weapon": "steel"}),
    "priest": ("female", {"hair": ("short", "blonde"), "head": ("hood", "mitre"), "head_ramp": "white",
                          "robe": "white", "trim": "gold", "robe_trim": "none", "stole": "gold", "mantle": "white",
                          "belt": False,
                          "shirt": "white", "pants": "white", "boots": "brown", "weapon": ("staff", "gold", "gold", "cross")}),
    "berserker": ("male", {"hair": ("short", "red"), "head": "horned", "head_ramp": "steel", "armor": "fur",
                           "pants": "brown", "boots": "brown", "weapon": "axe"}),
    "necromancer": ("male", {"hair": ("short", "black"), "head": "hood", "head_ramp": "black", "robe": "dark",
                             "trim": "necro", "robe_trim": "center", "hem": "tattered", "face_shadow": True,
                             "collar": "spikes", "pauldrons": "skull", "buckle": "bone", "shirt": "black",
                             "pants": "black", "boots": "black", "cape": "black",
                             "weapon": ("staff", "black", "necro", "skull"), "magic": "necro", "eyes": "necro"}),
    "skeleton": ("male", {"skeleton": True, "hair": None, "weapon": "grey", "magic": "necro", "shield": ("grey", "brown"),
                          "stiff": 1.35}),
}

DESCRIPTIONS = {
    "base": "Craftpix base character, unchanged",
    "knight": "Steel helmet, plate armour with pauldrons, red tabard and cape, steel sword",
    "mage": "Purple wizard hat, long purple hair, blue star-patterned robe with a red sash, staff with a blue orb",
    "ranger": "Green hood, leather vest and belt, green cloak, short sword (bow attack synthesised)",
    "priest": "White mitre with a gold cross, white robe with a gold stole and shoulder mantle, gold cross staff",
    "berserker": "Horned helmet, fur pauldrons over leather, axe",
    "necromancer": "Black hood with the face in shadow and glowing green eyes, bone-spike collar, skull pauldrons, tattered black robe and cape, skull staff",
    "skeleton": "Skeleton soldier on the base body (bone, ribs, skull with glowing eyes), old iron sword and a small round shield, stiff slow movement; Summon_Rise",
}

# Class attack: what "Sword_Attack" plays for this preset (casters cast a spell instead of swinging the staff).
ATTACK = {"mage": "Cast_Spell", "priest": "Cast_Spell", "necromancer": "Cast_Spell"}
