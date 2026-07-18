#!/usr/bin/env python3
"""Resolve every weapon art (Ash-of-War equivalent) into a scored catalog.

Chain (validated on the params 2026-07-17): SwordArtsParam.atkParamId ->
AtkParam_Pc = the art's own attack payload; useMagicPoint_L1/L2/R1/R2 = its
FP cost per stage. Droppable weapons roll their art through
EquipParamCustomWeapon.swordArtsTableId -> SwordArtsTableParam
{swordArtsId, chanceWeight} (one row per table id, same shape as the
magic/affix tables).

NOTE: many arts deal damage through the weapon's own moveset (motion.py
already resolves sub-category 111/112 rows as the `skill` action on weapon
AR). An art's atkParamId payload is the art's INDEPENDENT component — the
engine cross-checks redundancy before scoring both (ROADMAP phase B, 3.7).

Output: data/curated/sword_arts.json {art_id: {name, fp, damage, super_armor}}
"""
import json

from nightreign.io import paramdef, regulation
from nightreign.resources import constants

ATK_FIELDS = {"atkPhys": "phys", "atkMag": "mag", "atkFire": "fire",
              "atkThun": "thunder", "atkDark": "dark"}


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    print("  sword_arts: reading regulation.bin ...")
    params = regulation.load_params()

    def decode(name, defname=None):
        _, layout, _ = paramdef.parse_def(constants.DEFS / f"{defname or name}.xml")
        return paramdef.decode_param(params[name], layout)

    arts = decode("SwordArtsParam")
    atk = decode("AtkParam_Pc", "AtkParam")
    names = {e["ID"]: e["Entries"][0]
             for e in json.load(open(constants.NAMES / "SwordArtsParam.json"))["Entries"]
             if e.get("Entries") and e["Entries"][0]}

    out = {}
    n_damage = 0
    for rid, a in arts.items():
        entry = {"name": names.get(rid, f"art {rid}")}
        fp = max((a.get(f) or 0) for f in
                 ("useMagicPoint_L1", "useMagicPoint_L2", "useMagicPoint_R1", "useMagicPoint_R2"))
        if fp:
            entry["fp"] = fp
        row = atk.get(a.get("atkParamId") or -1)
        if row:
            damage = {t: row[f] for f, t in ATK_FIELDS.items() if row.get(f, 0) > 0}
            if damage:
                entry["damage"] = damage
                n_damage += 1
            if row.get("atkSuperArmor"):
                entry["super_armor"] = round(row["atkSuperArmor"], 4)
        out[rid] = entry

    json.dump(out, open(constants.DATA_CURATED / "sword_arts.json", "w"),
              ensure_ascii=False, allow_nan=False, indent=1)
    print(f"  sword_arts: {len(out)} arts ({n_damage} with an independent attack payload)")


if __name__ == "__main__":
    run()
