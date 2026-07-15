#!/usr/bin/env python3
"""Extract each Nightfarer's ability metadata + defensive profile.

- HeroParam: Character Skill / Ultimate Art cooldown, charge, usage.
- CharaInitParam (the playable "[X] Night ..." rows, id 30000 + index*100): the
  fixed armor (helm/body/gauntlet/legs) and starting/skill weapons.
- EquipParamProtector: each armor piece's damage negation, flat defense and status
  resistance; combined across the 4 pieces gives the character's base defense
  (needed for the survival / one-shot check).

Output: data/curated/characters.json
"""
import json

from nightreign.io import paramdef, regulation
from nightreign.resources import constants

# Nightfarer order -> HeroParam id (index+1), playable CharaInitParam id (30000+index*100).
HEROES = ["Wylder", "Guardian", "Ironeye", "Duchess", "Raider",
          "Revenant", "Recluse", "Executor", "Scholar", "Undertaker"]

ARMOR_SLOTS = ["equip_Helm", "equip_Armer", "equip_Gaunt", "equip_Leg"]
# Damage-negation multipliers (product across pieces; <1 = takes less damage).
NEGATION = {"phys": "neutralDamageCutRate", "slash": "slashDamageCutRate",
            "blow": "blowDamageCutRate", "thrust": "thrustDamageCutRate",
            "magic": "magicDamageCutRate", "fire": "fireDamageCutRate",
            "thunder": "thunderDamageCutRate", "dark": "darkDamageCutRate"}
DEFENSE = {"phys": "defensePhysics", "magic": "defenseMagic",
           "fire": "defenseFire", "thunder": "defenseThunder"}
RESIST = {"poison": "resistPoison", "bleed": "resistBlood", "frost": "resistFreeze",
          "sleep": "resistSleep", "madness": "resistMadness", "disease": "resistDisease",
          "curse": "resistCurse"}


def _defense(chara_row, protectors):
    """Combine the 4 armor pieces: negation multiplies, defense/resist add up."""
    negation = {k: 1.0 for k in NEGATION}
    flat_defense = {k: 0 for k in DEFENSE}
    status_resist = {k: 0 for k in RESIST}
    for slot in ARMOR_SLOTS:
        piece = protectors.get(chara_row.get(slot), {})
        for k, field in NEGATION.items():
            negation[k] *= piece.get(field, 1.0) or 1.0
        for k, field in DEFENSE.items():
            flat_defense[k] += piece.get(field, 0) or 0
        for k, field in RESIST.items():
            status_resist[k] += piece.get(field, 0) or 0
    return {"negation": {k: round(v, 4) for k, v in negation.items()},
            "flat_defense": flat_defense, "status_resist": status_resist}


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    params = regulation.load_params()

    def decode(name):
        _, layout, _ = paramdef.parse_def(constants.DEFS / f"{name}.xml")
        return paramdef.decode_param(params[name], layout)

    hero = decode("HeroParam")
    chara = decode("CharaInitParam")
    protectors = decode("EquipParamProtector")

    out = {}
    for index, name in enumerate(HEROES):
        h = hero.get(index + 1, {})
        c = chara.get(30000 + index * 100, {})
        out[name] = {
            "skill_cooldown": h.get("characterAbilityCooldown"),
            "skill_usage_count": h.get("characterAbilityUsageCount"),
            "ultimate_charge": h.get("ultimateArtCharge"),
            "starting_weapon": c.get("equip_Wep_Right_1"),
            "skill_weapon": c.get("characterSkillWeapon"),
            "ultimate_weapon": c.get("ultimateArtWeapon"),
            "defense": _defense(c, protectors),
        }

    json.dump(out, open(constants.DATA_CURATED / "characters.json", "w"),
              ensure_ascii=False, indent=1)
    print(f"  characters: wrote {len(out)} Nightfarers (abilities + armor defense)")


if __name__ == "__main__":
    run()
