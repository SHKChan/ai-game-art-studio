"""Class presets for the character kit: the plain base plus five fantasy classes (Tiny-RPG style)."""
from __future__ import annotations

PRESETS = {
    "base": ("male", None),
    "knight": ("male", {"hair": ("short", "brown"), "head": "helm", "head_ramp": "steel", "armor": "plate",
                        "tabard": "crimson", "cape": "crimson", "shirt": "grey", "pants": "grey", "boots": "brown",
                        "weapon": "steel"}),
    "mage": ("female", {"hair": ("long", "purple"), "head": "wizard", "head_ramp": "purple", "robe": "blue",
                        "trim": "gold", "shirt": "blue", "pants": "blue", "boots": "brown",
                        "weapon": ("staff", "brown", "blue", "orb")}),
    "ranger": ("male", {"hair": ("short", "brown"), "head": "hood", "head_ramp": "darkgreen", "armor": "leather",
                        "cape": "darkgreen", "shirt": "green", "pants": "brown", "boots": "brown", "weapon": "steel"}),
    "priest": ("female", {"hair": ("short", "blonde"), "head": ("hood", "circlet"), "head_ramp": "white",
                          "robe": "white", "trim": "gold", "shirt": "white", "pants": "white", "boots": "brown",
                          "weapon": ("staff", "gold", "gold", "cross")}),
    "berserker": ("male", {"hair": ("short", "red"), "head": "horned", "head_ramp": "steel", "armor": "fur",
                           "pants": "brown", "boots": "brown", "weapon": "axe"}),
}

DESCRIPTIONS = {
    "base": "Craftpix base character, unchanged",
    "knight": "Steel helmet, plate armour with pauldrons, red tabard and cape, steel sword",
    "mage": "Purple wizard hat, blue robe with gold trim, staff with a blue orb",
    "ranger": "Green hood, leather vest and belt, green cloak, short sword (bow attack synthesised)",
    "priest": "White hood with gold circlet, white robe with gold trim, gold cross staff",
    "berserker": "Horned helmet, fur pauldrons over leather, axe",
}
