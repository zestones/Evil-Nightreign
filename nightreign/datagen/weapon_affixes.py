#!/usr/bin/env python3
"""Extract the pool of random weapon affixes (in-run weapon rolls).

Weapons found in a run carry random passive affixes (+X% Attack, +Endurance, ...).
They use the SAME AttachEffect system as relics:

    EquipParamCustomWeapon.attachEffectTableId_1..6
        -> AttachEffectTableParam row -> attachEffectId
        -> AttachEffectParam -> passiveSpEffect (magnitude) + displayedModifierValue

So the optimizer can tell you which affix to look for on a weapon. Output is the
deduplicated affix pool with real values. Output: data/curated/weapon_affixes.json
"""
import json

from nightreign.io import paramdef, regulation
from nightreign.resources import conditions, constants
from nightreign.datagen.effects import _magnitude

TABLE_FIELDS = [f"attachEffectTableId_{i}" for i in range(1, 7)]


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    params = regulation.load_params()

    def decode(name):
        _, layout, total = paramdef.parse_def(constants.DEFS / f"{name}.xml")
        return paramdef.decode_param(params[name], layout, total)

    custom = decode("EquipParamCustomWeapon")
    table = decode("AttachEffectTableParam")
    attach = json.load(open(constants.DATA_RAW / "attach_effect.json"))
    filters = json.load(open(constants.DATA_RAW / "attach_effect_filter.json"))
    effect_params = json.load(open(constants.DATA_RAW / "effect_params.json"))

    # collect every affix id referenced by a weapon's affix tables
    affix_ids = set()
    for w in custom.values():
        for field in TABLE_FIELDS:
            row = table.get(w.get(field))
            if row and row.get("attachEffectId", 0) > 0:
                affix_ids.add(row["attachEffectId"])

    pool = {}
    for eid in sorted(affix_ids):
        ae = attach.get(str(eid))
        if not ae:
            continue
        magnitude = _magnitude(effect_params, ae.get("passiveSpEffectId_1"),
                               ae.get("passiveSpEffectId_2"), ae.get("passiveSpEffectId_3"))
        condition = None
        filt = filters.get(str(ae.get("attachFilterParamId")))
        if filt and filt.get("attachEffectFilterCategory"):
            condition = conditions.describe(filt["attachEffectFilterCategory"])
        pool[eid] = {
            "display_value": ae.get("displayedModifierValue"),
            "percent": bool(ae.get("displayPercentageSymbol")),
            "magnitude": magnitude,
            "condition": condition,
        }

    json.dump(pool, open(constants.DATA_CURATED / "weapon_affixes.json", "w"),
              ensure_ascii=False, indent=1)
    with_mag = sum(1 for v in pool.values() if v["magnitude"])
    print(f"  weapon_affixes: {len(pool)} possible affixes ({with_mag} with magnitude)")


if __name__ == "__main__":
    run()
