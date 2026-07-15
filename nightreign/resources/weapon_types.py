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


# Relative attack cadence (R1 light attacks per second) per weapon class.
# Class-level frame data (well-established ER weapon-class speeds); the extracted
# TAE animation durations (nr data animations) corroborate the ORDERING — full
# R1 animation lengths span ~1.5-5.3s, fast classes short, heavy/ranged long —
# but full per-animation cadence needs the TAE moveset-inheritance graph, so a
# class table is used. This is the DPS divisor that stops the slowest single
# hit (ballista, greatbow) from topping the cross-type ranking.
CADENCE = {
    "Dagger": 1.5, "Claw": 1.55, "Fist": 1.5,
    "Straight Sword": 1.2, "Curved Sword": 1.3, "Thrusting Sword": 1.25,
    "Heavy Thrusting Sword": 1.0, "Twinblade": 1.2, "Katana": 1.1,
    "Axe": 1.05, "Hammer": 1.05, "Flail": 1.0, "Spear": 1.1, "Whip": 1.05,
    "Greatsword": 0.85, "Curved Greatsword": 0.8, "Great Spear": 0.85,
    "Halberd": 0.9, "Reaper": 0.9, "Great Hammer": 0.65, "Greataxe": 0.7,
    "Colossal Sword": 0.6, "Colossal Weapon": 0.55,
    "Bow": 0.85, "Crossbow": 0.8, "Greatbow": 0.4, "Ballista": 0.3,
    "Staff": 1.0, "Sacred Seal": 1.0, "Torch": 1.1,
    "Small Shield": 1.1, "Medium Shield": 1.0, "Greatshield": 0.7,
}
DEFAULT_CADENCE = 1.0


def cadence(weapon_row):
    """Relative attacks/second for a weapon's class (DPS divisor)."""
    return CADENCE.get(weapon_type(weapon_row), DEFAULT_CADENCE)
