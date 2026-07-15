#!/usr/bin/env python3
"""Weapon motion category -> weapon-type label.

`wepmotionCategory` (EquipParamWeapon) is the only per-weapon type signal in the
params. The mapping below was derived from the owned data by listing, per
category, the base-variant weapon names and matching them against their known
Elden Ring types (e.g. cat 25 holds Bastard Sword / Claymore -> Greatsword;
cat 31 holds Axe of Godfrey / Duelist Greataxe / Envoy's Greathorn / Dragon
Greatclaw -> Colossal Weapon). Labels match the weapon-type condition taxonomy
in resources/conditions.py so type-gated relic effects can be activated.
"""

WEPMOTION_TO_TYPE = {
    20: "Dagger",
    21: "Torch",              # no relic condition uses it; label kept for display
    22: "Claw",
    23: "Straight Sword",
    24: "Twinblade",
    25: "Greatsword",
    26: "Colossal Sword",
    27: "Thrusting Sword",
    28: "Curved Sword",
    29: "Katana",
    30: "Axe",
    31: "Colossal Weapon",
    32: "Greataxe",
    33: "Hammer",
    34: "Flail",
    35: "Great Hammer",
    36: "Spear",
    37: "Great Spear",
    38: "Halberd",
    39: "Heavy Thrusting Sword",
    40: "Curved Greatsword",
    41: "Staff",
    42: "Fist",
    43: "Whip",
    44: "Bow",
    45: "Greatbow",
    46: "Crossbow",
    47: "Greatshield",
    48: "Small Shield",
    49: "Medium Shield",
    50: "Reaper",
    52: "Ballista",
}


def weapon_type(weapon_row):
    """Type label of a weapons.json row (None when the category is unmapped)."""
    return WEPMOTION_TO_TYPE.get(weapon_row.get("wepmotionCategory"))
