#!/usr/bin/env python3
"""Proposition 1 test — the aggregation is submodular, and NOT trivially modular.

Agg decomposes as a sum of per-key functions f_k (see optimizer_mathematical_formulation.md S2; for
grouped effects key <-> (group, level), invariant INV-2). We isolate a single
f_k on real relics — three carriers of the same (group, level) — and measure
its marginals:

  * sigma=0 key (one instance counts): marginal must STRICTLY drop to 0 once
    the key is already covered  -> genuinely submodular.
  * sigma=1 key (stacks, additive): marginal is constant -> modular, which is
    the special (trivial) case of submodular.

Showing the sigma=0 case is the point: the earlier validation only ever hit the
modular regime, so it never exercised diminishing returns. Note sigma is a
property of the KEY, not the group (3 real groups mix flags across levels);
find_group below buckets by (field, group, level), i.e. by key.
"""
import collections
import json
import math

from nightreign.resources import constants

RELICS = json.load(open(constants.DATA_CURATED / "relics.json"))
EFFECTS = json.load(open(constants.DATA_CURATED / "effects.json"))
ATTACK_FIELDS = ["magicAttackRate", "fireAttackRate", "thunderAttackRate", "physicsAttackRate"]


def group_hits(relic, field, group):
    """(level, log-magnitude) pairs this relic contributes to `group` on `field`."""
    out = []
    for e in relic["effects"]:
        if e.get("group") != group:
            continue
        m = (EFFECTS.get(str(e["id"])) or {}).get("magnitude") or {}
        if isinstance(m.get(field), (int, float)) and m[field] > 1:
            out.append((e.get("level"), math.log(m[field])))
    return out


def f_group(relic_set, field, group, stacks):
    """The isolated per-group aggregation f_g (S2 of the math doc)."""
    items = [hit for r in relic_set for hit in group_hits(r, field, group)]
    if not items:
        return 0.0
    if stacks:  # sigma=1: every copy adds (modular)
        return sum(v for _, v in items)
    per_level = {}  # sigma=0: keep the best value per distinct level (coverage)
    for level, v in items:
        per_level[level] = max(per_level.get(level, 0), v)
    return sum(per_level.values())


def find_group(stacks_flag):
    """A (field, group, level) carried by >=3 distinct relics at the SAME level."""
    for field in ATTACK_FIELDS:
        buckets = collections.defaultdict(dict)
        for r in RELICS:
            for e in r["effects"]:
                if not e.get("group") or bool(e.get("stacks")) != stacks_flag:
                    continue
                m = (EFFECTS.get(str(e["id"])) or {}).get("magnitude") or {}
                if isinstance(m.get(field), (int, float)) and m[field] > 1:
                    buckets[(field, e["group"], e.get("level"))][r["record_id"]] = r
        for key, relics in buckets.items():
            if len(relics) >= 3:
                return key, list(relics.values())[:3]
    return None, None


def main():
    for label, flag in [("sigma=0  (coverage, one-per-level)", False),
                        ("sigma=1  (stacks, additive)", True)]:
        key, relics = find_group(flag)
        if not key:
            print(f"{label}: no 3-relic example found")
            continue
        field, group, level = key
        r1, r2, r3 = relics
        m1 = f_group([r1], field, group, flag) - f_group([], field, group, flag)
        m2 = f_group([r1, r2], field, group, flag) - f_group([r1], field, group, flag)
        m3 = f_group([r1, r2, r3], field, group, flag) - f_group([r1, r2], field, group, flag)
        print(f"\n{label}")
        print(f"  group '{group}' level {level} on {field}  (3 relics, same level)")
        print(f"  marginals:  1st = {m1:.4f}   2nd = {m2:.4f}   3rd = {m3:.4f}")
        if not flag:
            ok = m1 > 1e-9 and abs(m2) < 1e-9 and abs(m3) < 1e-9
            print(f"  STRICT diminishing return (>0 then 0): submodular, non-modular? {ok}")
        else:
            ok = abs(m1 - m2) < 1e-9 and abs(m2 - m3) < 1e-9
            print(f"  constant marginal: modular (trivial case of submodular)? {ok}")


if __name__ == "__main__":
    main()
