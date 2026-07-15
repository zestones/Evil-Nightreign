#!/usr/bin/env python3
"""Extract everything needed to compute real Attack Rating (AR).

Outputs (data/raw/): hero_stats.json, weapons.json, reinforce_weapon.json,
calc_correct_graph.json, attack_element_correct.json
"""
import json
import math

from nightreign.io import paramdef, regulation
from nightreign.resources import constants

# AR-relevant EquipParamWeapon fields.
WEAPON_FIELDS = [
    "attackBasePhysics", "attackBaseMagic", "attackBaseFire",
    "attackBaseThunder", "attackBaseDark", "attackBaseStamina",
    "staminaConsumptionRate",  # stamina economy (per-attack cost factor)
    "correctStrength", "correctAgility", "correctMagic", "correctFaith", "correctLuck",
    "correctType_Physics", "correctType_Magic", "correctType_Fire",
    "correctType_Thunder", "correctType_Dark",
    "reinforceTypeId", "attackElementCorrectId", "materialSetId",
    "properStrength", "properAgility", "properMagic", "properFaith", "properLuck",
    "weight", "wepmotionCategory", "isDualBlade", "originEquipWep",
]


def _san(v):
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return round(v, 6)
    return v


def run():
    constants.DATA_RAW.mkdir(parents=True, exist_ok=True)
    print("  weapons: reading regulation.bin ...")
    params = regulation.load_params()

    def decode(name):
        _, layout, _ = paramdef.parse_def(constants.DEFS / f"{name}.xml")
        return paramdef.decode_param(params[name], layout)

    def dump(obj, fname):
        json.dump(obj, open(constants.DATA_RAW / fname, "w"), ensure_ascii=False, allow_nan=False)

    hero = decode("HeroStatusParam")
    dump({rid: {k: _san(v) for k, v in f.items() if _san(v) is not None} for rid, f in hero.items()},
         "hero_stats.json")
    print(f"  weapons: HeroStatusParam -> {len(hero)} rows")

    weapons = decode("EquipParamWeapon")
    dump({rid: {k: _san(f[k]) for k in WEAPON_FIELDS if k in f} for rid, f in weapons.items()},
         "weapons.json")
    print(f"  weapons: EquipParamWeapon -> {len(weapons)} weapons")

    for name, fname in [("ReinforceParamWeapon", "reinforce_weapon.json"),
                        ("CalcCorrectGraph", "calc_correct_graph.json"),
                        ("AttackElementCorrectParam", "attack_element_correct.json")]:
        rows = decode(name)
        dump({rid: {k: _san(v) for k, v in f.items() if _san(v) is not None} for rid, f in rows.items()},
             fname)
        print(f"  weapons: {name} -> {len(rows)} rows")

    # The DROPPABLE weapon pool: EquipParamCustomWeapon defines the instances
    # that actually spawn in a run (base weapon + weaponLevel + affix/art
    # tables + isCursed for Deep of Night gear). Every EquipParamWeapon id
    # outside this table (e.g. "Sacred Bloodstained Dagger") is engine-only
    # and must never be recommended — verified in game 2026-07-15.
    customs = decode("EquipParamCustomWeapon")
    dump({rid: {"weapon_id": r.get("targetWeaponId"),
                "level": r.get("weaponLevel"),
                "sword_arts_table": r.get("swordArtsTableId"),
                "affix_tables": [r.get(f"attachEffectTableId_{i}") for i in range(1, 7)
                                 if (r.get(f"attachEffectTableId_{i}") or -1) > 0],
                "is_cursed": bool(r.get("isCursed"))}
          for rid, r in customs.items() if r.get("targetWeaponId")},
         "custom_weapons.json")
    print(f"  weapons: EquipParamCustomWeapon -> {len(customs)} droppable instances")
