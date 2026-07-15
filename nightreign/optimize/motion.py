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
    vals = [_value(r) for r in rows]
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
    return cats


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
