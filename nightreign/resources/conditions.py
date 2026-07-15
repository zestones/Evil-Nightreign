#!/usr/bin/env python3
"""Taxonomy of relic-effect conditions (AttachEffectFilterParam categories).

Derived from the effects themselves (Smithbox doesn't name these). Each effect's
`condition.category` maps here to a human meaning and, crucially, to a *user
dimension*: what the player can toggle/tweak so the optimizer activates the right
effects (e.g. "I play Greatsword", "I play low-HP", "I run a bleed build").
"""

# 20xxx: weapon-type gate — the effect only works with that weapon equipped.
WEAPON_CATEGORIES = {
    20000: "Dagger", 20010: "Straight Sword", 20020: "Greatsword",
    20030: "Colossal Sword", 20040: "Curved Sword", 20050: "Curved Greatsword",
    20060: "Katana", 20070: "Twinblade", 20080: "Thrusting Sword",
    20090: "Heavy Thrusting Sword", 20100: "Axe", 20110: "Greataxe",
    20120: "Hammer", 20130: "Great Hammer", 20140: "Flail", 20150: "Spear",
    20160: "Great Spear", 20170: "Halberd", 20180: "Reaper", 20190: "Fist",
    20200: "Claw", 20210: "Whip", 20220: "Colossal Weapon", 20230: "Bow",
    20240: "Staff", 20250: "Sacred Seal", 20260: "Greatbow", 20270: "Crossbow",
    20280: "Ballista", 20300: "Small Shield", 20310: "Medium Shield",
    20320: "Greatshield",
}

# 10xxx: character-specific (index matches the Nightfarer order).
CHARACTER_CATEGORIES = {
    10000: "Wylder", 10010: "Guardian", 10020: "Ironeye", 10030: "Duchess",
    10040: "Raider", 10050: "Revenant", 10060: "Recluse", 10070: "Executor",
    10080: "Scholar", 10090: "Undertaker",
}

# 30xxx: gameplay categories. `dimension` = the toggle the user controls
# (None = always on, no toggle). `label` is human-readable.
GAMEPLAY_CATEGORIES = {
    30000: ("Stat bonus", None),
    30010: ("Art / Ultimate gauge", None),
    30020: ("Passive combat buff", None),
    30030: ("Sorcery / Incantation", "caster"),
    30040: ("At low HP", "low_hp"),
    30050: ("Status resistance", None),
    30060: ("FP / HP recovery", None),
    30070: ("Situational (guard / afflicted enemy)", "situational"),
    30080: ("Starting armament skill", "starting_loadout"),
    30090: ("Inflicts status", "status_build"),
    30100: ("Starting armament spell", "starting_loadout"),
    30110: ("Starting item", "starting_loadout"),
    30120: ("Starting tear", "starting_loadout"),
    30130: ("Shop / map utility", None),
    30140: ("Allies / co-op", "coop"),
}


def describe(category):
    """Return {kind, label, dimension} for a condition category.

    kind:      "weapon" | "character" | "gameplay"
    dimension: the user toggle this effect keys on (None = always on)
    """
    if category in WEAPON_CATEGORIES:
        return {"kind": "weapon", "label": WEAPON_CATEGORIES[category], "dimension": "weapon_type"}
    if category in CHARACTER_CATEGORIES:
        return {"kind": "character", "label": CHARACTER_CATEGORIES[category], "dimension": "character"}
    if category in GAMEPLAY_CATEGORIES:
        label, dimension = GAMEPLAY_CATEGORIES[category]
        return {"kind": "gameplay", "label": label, "dimension": dimension}
    return {"kind": "unknown", "label": str(category), "dimension": None}
