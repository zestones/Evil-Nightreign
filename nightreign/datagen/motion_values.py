#!/usr/bin/env python3
"""Extract player motion values: BehaviorParam_PC -> AtkParam_Pc.

Every attack of a weapon moveset is a behavior row (variationId = the
weapon's behaviorVariationId, behaviorJudgeId = the move) pointing at an
AtkParam_Pc row whose atk*Correction fields are the MOTION VALUES (% of AR).
Movesets resolve through a fallback chain: weapon-specific variation ->
class base variation (variation // 100 * 100) -> global variation 0.

Validated in game (2026-07-15): the greatsword chain MVs 100/101/102/110
reproduce the measured R1 damages 125/126 exactly, and each attack carries
the same sub-category tags that gate relic effects (112 = skill, 103 = guard
counter, 119 = first hit ... resources/actions.py).

Output: data/raw/motion_values.json  {variationId: {judge: row}}
"""
import json

from nightreign.io import paramdef, regulation
from nightreign.resources import constants

MV_FIELDS = {
    "atkPhysCorrection": "phys", "atkMagCorrection": "mag",
    "atkFireCorrection": "fire", "atkThunCorrection": "thunder",
    "atkDarkCorrection": "dark",
}


def run():
    constants.DATA_RAW.mkdir(parents=True, exist_ok=True)
    params = regulation.load_params()

    def decode(name, defname=None):
        _, layout, _ = paramdef.parse_def(constants.DEFS / f"{defname or name}.xml")
        return paramdef.decode_param(params[name], layout)

    beh = decode("BehaviorParam_PC", "BehaviorParam")
    atk = decode("AtkParam_Pc", "AtkParam")

    out = {}
    for r in beh.values():
        if r.get("refType") != 0:
            continue
        a = atk.get(r.get("refId"))
        if not a:
            continue
        mv = {t: a.get(f) for f, t in MV_FIELDS.items() if a.get(f)}
        if not mv:
            continue
        subs = sorted(a.get(f"subCategory{i}") for i in range(1, 6)
                      if a.get(f"subCategory{i}"))
        var, judge = r.get("variationId"), r.get("behaviorJudgeId")
        out.setdefault(str(var), {})[str(judge)] = {"mv": mv, "subs": subs}

    json.dump(out, open(constants.DATA_RAW / "motion_values.json", "w"),
              ensure_ascii=False)
    total = sum(len(v) for v in out.values())
    print(f"  motion_values: {len(out)} movesets, {total} attacks with motion values")


if __name__ == "__main__":
    run()
