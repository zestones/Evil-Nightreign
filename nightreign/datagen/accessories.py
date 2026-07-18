#!/usr/bin/env python3
"""Extract talismans (in-run accessory drops) with their real magnitudes.

EquipParamAccessory (136 rows, discovered 2026-07-17) -> spEffectId_1 ->
SpEffectParam, the same magnitude space the relic optimizer already
aggregates — so a talisman's effect flows through the existing per-key
aggregation untouched once the engine gives it a slot (ROADMAP phase D).

Output: data/curated/accessories.json
  {id: {name, magnitude, rarity, group, is_drop}}
"""
import json

from nightreign.io import paramdef, regulation
from nightreign.resources import constants
from nightreign.datagen.effects import _magnitude


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    print("  accessories: reading regulation.bin ...")
    params = regulation.load_params()

    def decode(name, defname=None):
        _, layout, _ = paramdef.parse_def(constants.DEFS / f"{defname or name}.xml")
        return paramdef.decode_param(params[name], layout)

    acc = decode("EquipParamAccessory")
    effect_params = json.load(open(constants.DATA_RAW / "effect_params.json"))
    names_path = constants.NAMES / "EquipParamAccessory.json"
    names = {e["ID"]: e["Entries"][0]
             for e in json.load(open(names_path))["Entries"]
             if e.get("Entries") and e["Entries"][0]} if names_path.exists() else {}

    # Gate fields that make an effect CONDITIONAL (only on a weapon/attack
    # subcategory, a state, or an HP threshold). The flat magnitude drops them,
    # so a gated buff would otherwise be scored as a universal multiplier — e.g.
    # Roar Medallion (roars/breaths only), Dagger Talisman (crit state), the
    # weapon-type talismans, low-/full-HP talismans. We flag them so the engine
    # refuses to credit the buff it cannot yet gate.
    GATE_FIELDS = ("magicSubCategoryChange1", "magicSubCategoryChange2",
                   "magicSubCategoryChange3", "stateInfo",
                   "conditionHp", "conditionHpRate")

    out = {}
    n_mag = 0
    n_cond = 0
    for rid, r in acc.items():
        sp = r.get("spEffectId_1")
        if not sp or sp <= 0:
            continue
        magnitude = _magnitude(effect_params, sp)
        raw = effect_params.get(str(sp)) or effect_params.get(sp) or {}
        gates = {g: raw.get(g) for g in GATE_FIELDS
                 if raw.get(g) not in (0, -1, None, "")}
        entry = {"name": names.get(rid, f"talisman {rid}"),
                 "sp_effect": sp,
                 "rarity": r.get("rarity", 0),
                 "group": r.get("accessoryGroup", 0),
                 "is_drop": bool(r.get("isDrop"))}
        if magnitude:
            entry["magnitude"] = magnitude
            n_mag += 1
        if gates:
            entry["conditional"] = True
            entry["gate"] = gates
            n_cond += 1
        out[rid] = entry

    json.dump(out, open(constants.DATA_CURATED / "accessories.json", "w"),
              ensure_ascii=False, allow_nan=False, indent=1)
    print(f"  accessories: {len(out)} talismans ({n_mag} with resolved magnitudes, "
          f"{n_cond} conditional/gated)")


if __name__ == "__main__":
    run()
