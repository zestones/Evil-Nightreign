#!/usr/bin/env python3
"""Theorem 2 test — dominance pruning is LOSSLESS on real data.

The earlier validation only showed candidate counts shrinking (47->36, ...),
which proves nothing about optimality. The real test is:

    OPT over the pruned pool  ==  OPT over the full pool.

Context: Duchess, Greatsword + Fire, offense vs a fire target, colored slots
[Red, Blue, Green]. One slot per color means s_c = 1, so Theorem 2 licenses the
single-dominator rule used below (with "Any" slots it would need >= s_c strict
dominators — see the counterexample in optimizer_mathematical_formulation.md S3). We enumerate BOTH
pools exhaustively and check the two optima are identical. Enumerating the full
pool is exactly the right practice: the ground-truth optimum must not trust the
pruning it validates.

Aggregation and profiles are PER KEY (optimizer_mathematical_formulation.md S2): copies of a
stacking key add, a non-stacking key counts once (max over copies). Data
invariants backing this model: experiments/validate_invariants.py.
"""
import collections
import itertools
import json
import math

from nightreign.resources import constants

RELICS = json.load(open(constants.DATA_CURATED / "relics.json"))
EFFECTS = json.load(open(constants.DATA_CURATED / "effects.json"))
WEAPON, CHARACTER = "Greatsword", "Duchess"


def fire_effects(relic):
    """Active fire-attack effects: (key, stacks, log-value)."""
    out = []
    for e in relic["effects"]:
        info = EFFECTS.get(str(e["id"]))
        if not info:
            continue
        cond = info.get("condition") or {}
        dim = cond.get("dimension")
        if dim is not None and not (
            (dim == "weapon_type" and cond.get("label") == WEAPON)
            or (dim == "character" and cond.get("label") == CHARACTER)
        ):
            continue
        rate = (info.get("magnitude") or {}).get("fireAttackRate")
        if isinstance(rate, (int, float)) and rate > 1:
            out.append((e["key"], bool(e.get("stacks")), math.log(rate)))
    return out


def agg(relic_set):
    """Per-key log-offense aggregation (S2 of the math doc)."""
    sums = collections.defaultdict(float)
    ones = {}
    for r in relic_set:
        for key, stk, v in fire_effects(r):
            if stk:
                sums[key] += v
            else:
                ones[key] = max(ones.get(key, 0.0), v)
    return sum(sums.values()) + sum(ones.values())


def profile(relic):
    """key -> value; sigma=1 keys sum intra-relic copies, sigma=0 keys take max."""
    p = collections.defaultdict(float)
    for key, stk, v in fire_effects(relic):
        if stk:
            p[key] += v
        else:
            p[key] = max(p[key], v)
    return dict(p)


def dominates(a, b):
    return all(a.get(k, 0.0) >= v - 1e-12 for k, v in b.items())


def prune(cands):
    """Single strict dominator suffices here: one slot per color (s_c = 1)."""
    keep = []
    for i, r in enumerate(cands):
        pf = profile(r)
        if any(j != i and dominates(profile(o), pf) and profile(o) != pf
               for j, o in enumerate(cands)):
            continue
        keep.append(r)
    return keep


def best(pools, colors):
    top = -1.0
    for combo in itertools.product(*(pools[c] for c in colors)):
        top = max(top, agg(list(combo)))
    return top


def main():
    colors = ("Red", "Blue", "Green")
    full = collections.defaultdict(list)
    for r in RELICS:
        if r["type"] != "DeepRelic" and fire_effects(r):
            full[r["color"]].append(r)
    pruned = {c: prune(full[c]) for c in colors}

    n_full = math.prod(len(full[c]) for c in colors)
    n_pruned = math.prod(len(pruned[c]) for c in colors)
    opt_full = best(full, colors)
    opt_pruned = best(pruned, colors)

    print("Theorem 2 (lossless pruning) — Duchess / Greatsword+Fire / [Red,Blue,Green]")
    print(f"  per-color full  : {[len(full[c]) for c in colors]}  -> {n_full} combos")
    print(f"  per-color pruned: {[len(pruned[c]) for c in colors]}  -> {n_pruned} combos "
          f"({100 * (n_full - n_pruned) / n_full:.1f}% dropped)")
    print(f"  OPT_full   = {opt_full:.10f}")
    print(f"  OPT_pruned = {opt_pruned:.10f}")
    print(f"  LOSSLESS (OPT_full == OPT_pruned)? {abs(opt_full - opt_pruned) < 1e-12}")


if __name__ == "__main__":
    main()
