#!/usr/bin/env python3
"""Resolve every owned relic effect to its REAL magnitude and condition.

Nightreign relic effects go through the AttachEffect system, not direct SpEffects:

    relic effect id -> AttachEffectParam[id]
        .passiveSpEffectId_1/2/3  -> SpEffectParam rows  (the magnitude)
        .onHitSpEffect            -> SpEffectParam row    (on-hit / status buildup)
        .attachFilterParamId      -> AttachEffectFilterParam (the condition)
        .allow<Character>         -> which Nightfarers can use it
        .isDebuff / displayedModifierValue

This gives 100% coverage of owned effects with real values pulled from the game.
Output: data/curated/effects.json

Run: python3 -m nightreign data effects
"""
import json

from nightreign.resources import conditions, constants

CHARACTERS = ["Wylder", "Guardian", "Ironeye", "Duchess", "Raider",
              "Revenant", "Recluse", "Executor", "Scholar", "Undertaker"]

# Field-name fragments that are engine metadata, not gameplay magnitudes.
_NOISE = ("vowType", "effectTarget", "iconId", "vfxId", "stateInfo", "Category",
          "motionInterval", "spEffectTextId", "Trigger", "Condition", "condition",
          "invocation", "Behavior", "cycle", "replace", "ParamChange", "throw",
          "addBehavior", "changeType", "SfxId", "SeId", "Sfx", "wep", "saveCategory")


def _meaningful(field, value):
    """Keep real magnitudes; drop neutral defaults (1.0 rate, 0, -1) and metadata."""
    if any(s in field for s in _NOISE):
        return False
    if isinstance(value, float):
        return value not in (0.0, 1.0, -1.0) and value == value  # last check drops NaN
    if isinstance(value, int) and not isinstance(value, bool):
        return value not in (0, -1)
    return False


def _magnitude(effect_params, *sp_ids):
    """Merge the meaningful fields of one or more SpEffect rows."""
    out = {}
    for sp_id in sp_ids:
        if sp_id is None or sp_id < 0:
            continue
        for k, v in (effect_params.get(str(sp_id)) or {}).items():
            if _meaningful(k, v):
                out[k] = v
    return out


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    relics = json.load(open(constants.DATA_CURATED / "relics.json"))
    effect_params = json.load(open(constants.DATA_RAW / "effect_params.json"))
    attach = json.load(open(constants.DATA_RAW / "attach_effect.json"))
    filters = json.load(open(constants.DATA_RAW / "attach_effect_filter.json"))

    owned_ids, text_by_id = {}, {}
    for relic in relics:
        for e in relic["effects"]:
            owned_ids[e["id"]] = e["key"]
            text_by_id[e["id"]] = e["text"]

    resolved, with_mag, with_cond = {}, 0, 0
    for eid, key in owned_ids.items():
        ae = attach.get(str(eid))
        if not ae:
            resolved[eid] = dict(key=key, text=text_by_id[eid], magnitude={},
                                 on_hit={}, condition=None, characters="all", is_debuff=False)
            continue

        magnitude = _magnitude(effect_params, ae.get("passiveSpEffectId_1"),
                               ae.get("passiveSpEffectId_2"), ae.get("passiveSpEffectId_3"),
                               ae.get("permanentSpEffectId"))
        on_hit = _magnitude(effect_params, ae.get("onHitSpEffect"))

        condition = None
        filt = filters.get(str(ae.get("attachFilterParamId")))
        category = filt.get("attachEffectFilterCategory") if filt else None
        if category:
            condition = {"category": category, "value": filt.get("filterValue"),
                         **conditions.describe(category)}

        allowed = [c for c in CHARACTERS if ae.get(f"allow{c}")]
        characters = "all" if len(allowed) == len(CHARACTERS) else allowed

        resolved[eid] = dict(
            key=key, text=text_by_id[eid],
            magnitude=magnitude, on_hit=on_hit, condition=condition,
            characters=characters, is_debuff=bool(ae.get("isDebuff")),
            displayed_value=ae.get("displayedModifierValue"),
        )
        with_mag += bool(magnitude or on_hit)
        with_cond += bool(condition)

    json.dump(resolved, open(constants.DATA_CURATED / "effects.json", "w"),
              ensure_ascii=False, indent=1)
    print(f"  effects: resolved {len(resolved)} owned effects "
          f"({with_mag} with magnitude, {with_cond} with a condition)")


if __name__ == "__main__":
    run()
