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

    # AttachEffect system: the real relic-effect mechanism. Each relic effect is
    # an AttachEffectParam row that points to passive SpEffects (magnitude) and an
    # AttachEffectFilterParam row (the condition, e.g. weapon type). Kept in full.
    for name, fname in [("AttachEffectParam", "attach_effect.json"),
                        ("AttachEffectFilterParam", "attach_effect_filter.json")]:
        _, layout, _ = paramdef.parse_def(constants.DEFS / f"{name}.xml")
        rows = paramdef.decode_param(params[name], layout)
        out = {rid: {k: _sanitize(v) for k, v in f.items() if _sanitize(v) is not None}
               for rid, f in rows.items()}
        json.dump(out, open(constants.DATA_RAW / fname, "w"), ensure_ascii=False, allow_nan=False)
        print(f"  params: {name} -> {len(rows)} rows")

    # Enemy attack system (for boss damage / the one-shot check): an enemy's
    # behaviorVariationId links to BehaviorParam rows whose refId points at
    # AtkParam_Npc rows carrying the real per-element attack damage.
    _, beh_layout, _ = paramdef.parse_def(constants.DEFS / "BehaviorParam.xml")
    beh = paramdef.decode_param(params["BehaviorParam"], beh_layout)
    beh_out = {rid: {k: f.get(k) for k in ("variationId", "refType", "refId")}
               for rid, f in beh.items()}
    json.dump(beh_out, open(constants.DATA_RAW / "behavior.json", "w"),
              ensure_ascii=False, allow_nan=False)
    print(f"  params: BehaviorParam -> {len(beh)} rows")

    _, atk_layout, _ = paramdef.parse_def(constants.DEFS / "AtkParam.xml")
    atk = paramdef.decode_param(params["AtkParam_Npc"], atk_layout)
    atk_fields = ("atkPhys", "atkMag", "atkFire", "atkThun", "atkDark", "atkStam",
                  "atkSuperArmor", "atkAttribute")
    atk_out = {rid: d for rid, f in atk.items()
               if (d := {k: _sanitize(f[k]) for k in atk_fields if f.get(k)})}
    json.dump(atk_out, open(constants.DATA_RAW / "atk_npc.json", "w"),
              ensure_ascii=False, allow_nan=False)
    print(f"  params: AtkParam_Npc -> {len(atk)} rows ({len(atk_out)} with damage)")
    # Owned-effect resolution (magnitude + condition) is done by the `effects` step.
