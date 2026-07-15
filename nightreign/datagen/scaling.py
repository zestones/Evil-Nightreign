#!/usr/bin/env python3
"""Extract Nightreign mode/difficulty scaling -> data/curated/mode_scaling.json.

`ClearCountCorrectParam` is the difficulty ladder (Deep of Night depth): at each
level, enemies get an attack and HP multiplier. This is what decides whether a
boss one-shots you deep into a run. Real values, e.g. level 7 = attack x1.45.

Attack multipliers are uniform across damage types, so we store one `attack` value
plus `hp` and `stamina`. Row 0 is an unused baseline (all zeros); we keep levels
whose base rate is > 0.

(AcrossDayCorrectParam and MultiPlayCorrectionParam also scale a run, but their
fields are unnamed / applied indirectly via SpEffects — left for later.)
"""
import json

from nightreign.io import paramdef, regulation
from nightreign.resources import constants


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    params = regulation.load_params()
    _, layout, _ = paramdef.parse_def(constants.DEFS / "ClearCountCorrectParam.xml")
    rows = paramdef.decode_param(params["ClearCountCorrectParam"], layout)

    deep_of_night = {}
    for level in sorted(rows):
        r = rows[level]
        attack = r.get("PhysicsAttackRate")
        if not attack:  # skip the empty baseline row 0
            continue
        deep_of_night[level] = {
            "attack": round(attack, 3),
            "hp": round(r.get("MaxHpRate", attack), 3),
            "stamina": round(r.get("MaxStaminaRate", attack), 3),
        }

    out = {"deep_of_night": deep_of_night}
    json.dump(out, open(constants.DATA_CURATED / "mode_scaling.json", "w"),
              ensure_ascii=False, indent=1)
    print(f"  scaling: Deep of Night ladder -> {len(deep_of_night)} levels "
          f"(x{min(v['attack'] for v in deep_of_night.values())}"
          f"..x{max(v['attack'] for v in deep_of_night.values())} attack)")


if __name__ == "__main__":
    run()
