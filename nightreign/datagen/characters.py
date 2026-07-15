#!/usr/bin/env python3
"""Extract each Nightfarer's ability metadata (HeroParam) -> data/curated/characters.json.

HeroParam holds the Character Skill / Ultimate Art / passive metadata: cooldown,
charge, usage count, and the text ids for their names/descriptions. The ability
*damage* is not here (it lives in AtkParam_Pc, reached via animation/behavior data
in the game archives) - see the notes in the project for that harder path.
"""
import json

from nightreign.io import paramdef, regulation
from nightreign.resources import constants

# HeroParam row id -> Nightfarer (in game order).
HEROES = {1: "Wylder", 2: "Guardian", 3: "Ironeye", 4: "Duchess", 5: "Raider",
          6: "Revenant", 7: "Recluse", 8: "Executor", 9: "Scholar", 10: "Undertaker"}


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    params = regulation.load_params()
    _, layout, _ = paramdef.parse_def(constants.DEFS / "HeroParam.xml")
    hero = paramdef.decode_param(params["HeroParam"], layout)

    out = {}
    for rid, name in HEROES.items():
        r = hero.get(rid, {})
        out[name] = {
            "skill_cooldown": r.get("characterAbilityCooldown"),
            "skill_usage_count": r.get("characterAbilityUsageCount"),
            "ultimate_charge": r.get("ultimateArtCharge"),
            "hero_status_param_id": r.get("heroStatusParamId"),
            "text_ids": {
                "skill": r.get("characterSkillTitleId"),
                "ultimate": r.get("ultimateArtTitleId"),
                "passive": r.get("passiveAbilityTitleId"),
            },
        }

    json.dump(out, open(constants.DATA_CURATED / "characters.json", "w"),
              ensure_ascii=False, indent=1)
    print(f"  characters: wrote {len(out)} Nightfarers (ability metadata)")


if __name__ == "__main__":
    run()
