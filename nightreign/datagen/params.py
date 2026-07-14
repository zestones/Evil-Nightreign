#!/usr/bin/env python3
"""Extract SpEffectParam + NpcParam from regulation.bin, and join owned effects.

Outputs:
  data/raw/effect_params.json      : magnitudes per SpEffect (diff vs the null effect)
  data/raw/npc_params.json         : every combat/gameplay field for each enemy row
  data/curated/relic_effect_magnitudes.json : owned effects joined to magnitudes
"""
import json
import math

from nightreign.io import paramdef, regulation
from nightreign.resources import constants


def _sanitize(v):
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return round(v, 5)
    return v


def _differs(v, baseline):
    if isinstance(v, float) and isinstance(baseline, float) and math.isnan(v) and math.isnan(baseline):
        return False
    return v != baseline


def run():
    constants.DATA_RAW.mkdir(parents=True, exist_ok=True)
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    print("  params: reading regulation.bin ...")
    params = regulation.load_params()

    # SpEffectParam: effect magnitudes (kept as diff vs the null effect id 0).
    _, sp_layout, _ = paramdef.parse_def(constants.DEFS / "SpEffectParam.xml")
    sp = paramdef.decode_param(params["SpEffectParam"], sp_layout)
    baseline = sp.get(0, {})
    effect_params = {}
    for row_id, fields in sp.items():
        diff = {k: _sanitize(v) for k, v in fields.items() if _differs(v, baseline.get(k))}
        diff = {k: v for k, v in diff.items() if v is not None}
        if diff:
            effect_params[row_id] = diff
    json.dump(effect_params, open(constants.DATA_RAW / "effect_params.json", "w"),
              ensure_ascii=False, allow_nan=False)
    print(f"  params: SpEffectParam -> {len(effect_params)} effects")

    # NpcParam: full combat/gameplay stats per enemy.
    _, npc_layout, _ = paramdef.parse_def(constants.DEFS / "NpcParam.xml")
    npc = paramdef.decode_param(params["NpcParam"], npc_layout)
    npc_out = {rid: {k: _sanitize(v) for k, v in f.items() if _sanitize(v) is not None}
               for rid, f in npc.items()}
    json.dump(npc_out, open(constants.DATA_RAW / "npc_params.json", "w"),
              ensure_ascii=False, allow_nan=False)
    print(f"  params: NpcParam -> {len(npc)} enemies")

    # Join owned effects -> magnitudes (needs curated/relics.json from the relics step).
    relics_path = constants.DATA_CURATED / "relics.json"
    if relics_path.exists():
        relics = json.load(open(relics_path))
        owned, matched = {}, 0
        for relic in relics:
            for effect in relic["effects"]:
                eid = effect["id"]
                if eid in owned:
                    continue
                mag = effect_params.get(eid)
                owned[eid] = dict(key=effect["key"], text=effect["text"], magnitudes=mag)
                matched += bool(mag)
        json.dump(owned, open(constants.DATA_CURATED / "relic_effect_magnitudes.json", "w"),
                  ensure_ascii=False, indent=1)
        print(f"  params: joined {len(owned)} owned effects ({matched} with magnitudes)")
