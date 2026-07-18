#!/usr/bin/env python3
"""Per-weapon motion-value profile for the play-profile actions.

A weapon's moveset resolves through the behavior fallback chain (global
variation 0 -> class base variation -> weapon variation; later overrides
earlier per judge id). Attacks self-classify through the same sub-category
tags that gate relic effects:

  * basic chain  = judges < 100 tagged 130 (melee) — extracted values
    reproduce the in-game measured chain exactly (100/101/102/110),
  * initial      = the chain hit tagged 119 (first standard attack),
  * skill        = rows tagged 111/112 (weapon-art hits; per-HIT value —
    multi-hit arts like Halo Scythe's ring land several of them per cast),
  * guard counter= rows tagged 103 (one-handed variant),
  * crit         = the 500-family: the family MINIMUM matches the measured
    backstab ratio (286/142 = 2.01 vs family min 200), the larger rows are
    ripostes/full-charge variants.

Motion values are % of AR; factors returned as multipliers (MV / 100).
Actions with no identifiable rows fall back to 1.0 (neutral).
"""

SKILL_SUBS = {111, 112}
GUARD_COUNTER_SUB = 103
FIRST_HIT_SUB = 119
TWO_HAND_SUB = 124
DUAL_SUB = 125


def _value(row):
    mv = row.get("mv") or {}
    return mv.get("phys") or max(mv.values(), default=100)


def _mean(rows):
    # flat-only rows (ranged shots, art payloads: no correction fields) carry
    # no MOTION VALUE — excluding them keeps the class means clean; their
    # damage contribution flows through flat_profile() instead
    vals = [_value(r) for r in rows if r.get("mv")]
    return (sum(vals) / len(vals)) / 100.0 if vals else 1.0


def _classify(rows):
    """Split one variation's rows into the play-profile categories."""
    cats = {"melee": [], "initial": [], "skill": [], "guard_counter": [], "crit": []}
    for judge, row in rows.items():
        subs = set(row.get("subs") or ())
        if SKILL_SUBS & subs:
            cats["skill"].append(row)
            continue
        j = int(judge)
        if 500 <= j < 600:
            cats["crit"].append(row)
        elif GUARD_COUNTER_SUB in subs and TWO_HAND_SUB not in subs and DUAL_SUB not in subs:
            cats["guard_counter"].append(row)
        elif j < 100 and 130 in subs:
            cats["melee"].append(row)
            if FIRST_HIT_SUB in subs:
                cats["initial"].append(row)
    if not cats["melee"]:
        # ranged movesets (bows: judges 205-245) have no sub-100 chain — their
        # standard SHOTS are the 130-tagged rows in the 200 band, ALSO tagged
        # 111/112 (shots benefit from weapon-skill buffs). Discovered
        # 2026-07-17: without this, a bow's "melee" (its shot) never resolves
        # and falls back to a neutral 1.0 with no flat payload.
        for judge, row in rows.items():
            subs = set(row.get("subs") or ())
            j = int(judge)
            if 130 in subs and 200 <= j < 300:
                cats["melee"].append(row)
    return cats


def flat_profile(weapon_row, tables):
    """{action: {damage_type: flat}} — the isAddBaseAtk flat payload of the
    action's rows (mean), added ON TOP of weapon AR × MV.

    MELEE-family only (the ranged classes' standard shots, +71-80 flat —
    discovered 2026-07-17). The `skill` category is deliberately EXCLUDED:
    its add_base rows are the class's possible WEAPON-ART payloads, and a
    dropped weapon rolls ONE art, not the class average — scoring that mean
    would pollute every melee weapon's skill action (rolled-art payloads are
    explicit backlog, like affixes)."""
    var = weapon_row.get("behaviorVariationId") or 0
    levels = [_classify(tables.get(str(v), {}))
              for v in (var, var // 100 * 100, 0)]
    out = {}
    for action in ("melee", "initial"):
        for level in levels:
            rows = [r for r in level[action] if r.get("add_base") and r.get("flat")]
            if level[action]:
                if rows:
                    acc = {}
                    for r in rows:
                        for t, v in r["flat"].items():
                            acc[t] = acc.get(t, 0.0) + v / len(rows)
                    out[action] = acc
                break
    return out


def stamina_costs(weapon_row, tables):
    """{action: mean stamina cost per use} through the same most-specific
    variation resolution as profile(). Costs are exact params (BehaviorParam
    `stamina`); actions without a costed row are absent (never invented).
    The sustain CONSTRAINT (pool/regen) awaits the calibration measures."""
    var = weapon_row.get("behaviorVariationId") or 0
    levels = [_classify(tables.get(str(v), {}))
              for v in (var, var // 100 * 100, 0)]
    out = {}
    for action in ("melee", "initial", "skill", "guard_counter", "crit"):
        for level in levels:
            costs = [r["stamina"] for r in level[action] if r.get("stamina")]
            if costs:
                out[action] = sum(costs) / len(costs)
                break
    return out


def profile(weapon_row, tables):
    """{action: motion-value factor} for the play-profile actions.

    Each category resolves at the MOST SPECIFIC variation that defines it
    (weapon -> class -> global 0): merging levels would pollute a class's
    clean chain with the global table's generic judges.
    """
    var = weapon_row.get("behaviorVariationId") or 0
    levels = [_classify(tables.get(str(v), {}))
              for v in (var, var // 100 * 100, 0)]
    out = {}
    for action in ("melee", "initial", "skill", "guard_counter", "crit"):
        for level in levels:
            rows = level[action]
            if rows:
                if action == "crit":
                    # drop partial-hit fragments (< 150) of multi-part crit
                    # animations; the filtered minimum is the plain backstab —
                    # 200 matches the measured backstab/R1 ratio 286/142 = 2.01
                    full = [v for v in (_value(r) for r in rows) if v >= 150]
                    out[action] = (min(full) if full else max(_value(r) for r in rows)) / 100.0
                else:
                    out[action] = _mean(rows)
                break
    return {a: f for a, f in out.items() if f} or {"melee": 1.0}
