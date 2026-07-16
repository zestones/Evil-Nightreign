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

from nightreign.resources import actions, conditions, constants, curses

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


def _cycle_magnitude(effect_params, *sp_ids):
    """Magnitude reached one hop down a cycleOccurrenceSpEffectId chain.

    Some curses (nearDeathReducesMaxHP, repeatedEvasionsLowerDamageNegation) hold
    no direct magnitude on their passive SpEffect — only replace/cycle pointers —
    and their real value (maxHpRate, DamageCutRate) lives on the periodic-tick
    effect. Followed only for the curses that resources/curses.py opts in, so no
    other effect's magnitude changes.
    """
    out = {}
    for sp_id in sp_ids:
        if sp_id is None or sp_id < 0:
            continue
        row = effect_params.get(str(sp_id)) or {}
        cyc = row.get("cycleOccurrenceSpEffectId", -1)
        if isinstance(cyc, int) and cyc > 0:
            out.update(_magnitude(effect_params, cyc))
    return out


def _action_gates(effect_params, *sp_ids):
    """(action classes, state gate) restricting where the effect applies.

    Reads the SpEffect `magicSubCategoryChange*` fields (attack sub-category
    gates) and `stateInfo` (engine behaviors) — see resources/actions.py.
    Empty actions = the effect applies to every attack.
    """
    acts, state = set(), None
    mag = miracle = False
    for sp_id in sp_ids:
        if sp_id is None or sp_id < 0:
            continue
        row = effect_params.get(str(sp_id)) or {}
        for field, value in row.items():
            if "SubCategory" in field and isinstance(value, int) and value > 0:
                label = actions.SUBCATEGORY_ACTIONS.get(value)
                if label:
                    acts.add(label)
            elif field == "stateInfo" and isinstance(value, int):
                if value in actions.STATEINFO_ACTIONS:
                    acts.add(actions.STATEINFO_ACTIONS[value])
                elif value in actions.STATEINFO_STATES:
                    state = actions.STATEINFO_STATES[value]
            elif field == "magParamChange" and value:
                mag = True
            elif field == "miracleParamChange" and value:
                miracle = True
    # exactly one spell flag and no finer gate = generic sorcery/incant buff
    # (generic offense carries BOTH flags; school buffs are sub-category gated)
    if not acts and mag != miracle:
        acts.add("sorcery_any" if mag else "incant_any")
    return sorted(acts), state


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
                                 on_hit={}, condition=None, actions=[], state_gate=None,
                                 characters="all", is_debuff=False)
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
        acts, state_gate = _action_gates(
            effect_params, ae.get("passiveSpEffectId_1"), ae.get("passiveSpEffectId_2"),
            ae.get("passiveSpEffectId_3"), ae.get("permanentSpEffectId"))

        is_debuff = bool(ae.get("isDebuff"))
        # Deep-of-Night curse: for the SCORED ones (resources/curses.py), resolve
        # the cycle-hop magnitude and apply the explicit gate; drop any auto state
        # gate. Display-only curses fall through unchanged (surfaced, not scored).
        curse = curses.spec(key) if is_debuff else None
        if curse:
            if curse["follow_cycle"]:
                magnitude = {**magnitude, **_cycle_magnitude(
                    effect_params, ae.get("passiveSpEffectId_1"),
                    ae.get("passiveSpEffectId_2"), ae.get("passiveSpEffectId_3"))}
            condition = {"kind": "curse", "label": "Deep of Night curse",
                         "dimension": curse["gate"]}
            state_gate = None

        resolved[eid] = dict(
            key=key, text=text_by_id[eid],
            magnitude=magnitude, on_hit=on_hit, condition=condition,
            actions=acts, state_gate=state_gate,
            characters=characters, is_debuff=is_debuff,
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
