#!/usr/bin/env python3
"""Empirically validate the optimizer theory on real data.

Context: Duchess, Greatsword + Fire affinity, offense vs a fire target.
Objective proxy G(A) = log-additive fire-attack multiplier, with stacking rules.
Vessel: Duchess' Chalice normal slots [Red, Blue, Green] (1 relic per color).

We check: (1) dominance pruning reduction, (2) submodularity of G,
(3) greedy vs beam vs EXHAUSTIVE optimum gap.
"""
import json, math, itertools, collections

ROOT = "/home/zestones/Documents/Github/zestones/EvilNightreign"
relics = json.load(open(f"{ROOT}/data/curated/relics.json"))
effects = json.load(open(f"{ROOT}/data/curated/effects.json"))

DTYPE = "fire"
RATE_FIELD = "fireAttackRate"
WEAPON = "Greatsword"
CHARACTER = "Duchess"


def active(effect_id):
    """Is this effect active in our fixed context? and its fire log-value."""
    e = effects.get(str(effect_id))
    if not e:
        return None
    cond = e.get("condition") or {}
    dim = cond.get("dimension")
    # active if always-on, or weapon matches, or our character
    if dim in (None,):
        pass
    elif dim == "weapon_type" and cond.get("label") == WEAPON:
        pass
    elif dim == "character" and cond.get("label") == CHARACTER:
        pass
    else:
        return None  # a toggle we didn't set / another weapon / another character
    rate = (e.get("magnitude") or {}).get(RATE_FIELD)
    if not isinstance(rate, (int, float)) or rate <= 1.0:
        return None
    return math.log(rate)


def relic_effects(relic):
    """Active offense effects of a relic: list of (group, level, stacks, value, key)."""
    out = []
    for eff in relic["effects"]:
        v = active(eff["id"])
        if v is None:
            continue
        out.append((eff.get("group"), eff.get("level"), bool(eff.get("stacks")), v, eff["key"]))
    return out


def G(relic_set):
    """Aggregated log-offense with stacking rules."""
    grouped = collections.defaultdict(list)  # group -> [(level, stacks, v)]
    ungrouped = {}                            # key -> v  (distinct, non-stacking)
    for r in relic_set:
        for (g, lvl, stk, v, key) in relic_effects(r):
            if g is None:
                ungrouped[key] = v            # only one instance counts
            else:
                grouped[g].append((lvl, stk, v))
    total = sum(ungrouped.values())
    for g, items in grouped.items():
        stacks = items[0][1]
        if stacks:                            # all copies add
            total += sum(v for _, _, v in items)
        else:                                 # one per distinct level
            best_per_level = {}
            for lvl, _, v in items:
                best_per_level[lvl] = max(best_per_level.get(lvl, 0), v)
            total += sum(best_per_level.values())
    return total


# ---- candidate relics per color (only fire-relevant ones matter) ----
def contributes(relic):
    return len(relic_effects(relic)) > 0

by_color = collections.defaultdict(list)
for r in relics:
    if r["type"] != "DeepRelic" and contributes(r):
        by_color[r["color"]].append(r)

print("=== 1. Candidats fire-pertinents par couleur (avant élagage) ===")
for c in ("Red", "Blue", "Green"):
    print(f"  {c}: {len(by_color[c])}")


# ---- dominance pruning (structural, context-aware) ----
def profile(relic):
    """(frozenset of ungrouped keys->v, dict group->(maxlevel-value-sum))."""
    ung, grp = {}, collections.defaultdict(dict)
    for (g, lvl, stk, v, key) in relic_effects(relic):
        if g is None:
            ung[key] = v
        else:
            grp[g][lvl] = max(grp[g].get(lvl, 0), v)
    return ung, grp


def dominates(a, b):
    """Does relic a dominate b? (a >= b on every offense dimension)."""
    ua, ga = profile(a)
    ub, gb = profile(b)
    for k, v in ub.items():
        if ua.get(k, 0) < v:
            return False
    for g, levels in gb.items():
        for lvl, v in levels.items():
            if ga.get(g, {}).get(lvl, 0) < v:
                return False
    return True


def prune(cands):
    keep = []
    for r in cands:
        if any(dominates(o, r) and profile(o) != profile(r) for o in cands if o is not r):
            continue
        keep.append(r)
    return keep


pruned = {c: prune(by_color[c]) for c in ("Red", "Blue", "Green")}
print("\n=== 2. Après élagage par dominance ===")
for c in ("Red", "Blue", "Green"):
    print(f"  {c}: {len(by_color[c])} -> {len(pruned[c])}")


# ---- 3. submodularity check: marginal of adding a relic is non-increasing ----
def marginal(r, A):
    return G(A + [r]) - G(A)

# sample: pick a red relic, measure its marginal for growing A
import random
red = pruned["Red"]; blue = pruned["Blue"]; green = pruned["Green"]
if red:
    probe = red[0]
    A0 = []
    A1 = [blue[0]] if blue else []
    A2 = ([blue[0], green[0]] if blue and green else A1)
    m0, m1, m2 = marginal(probe, A0), marginal(probe, A1), marginal(probe, A2)
    print("\n=== 3. Sous-modularité (marginal décroissant) ===")
    print(f"  marginal(A=∅)={m0:.4f}  >=  marginal(A=1)={m1:.4f}  >=  marginal(A=2)={m2:.4f}")
    print(f"  décroissant ? {m0 >= m1 - 1e-9 >= 0 and m1 >= m2 - 1e-9}")


# ---- 4. greedy vs beam vs EXHAUSTIVE ----
slots = ["Red", "Blue", "Green"]  # Duchess' Chalice normal slots


def exhaustive():
    best, best_set = -1, None
    for combo in itertools.product(pruned["Red"], pruned["Blue"], pruned["Green"]):
        s = G(list(combo))
        if s > best:
            best, best_set = s, combo
    return best, best_set


def greedy():
    A, used = [], set()
    for col in slots:
        cands = [r for r in pruned[col] if r["record_id"] not in used]
        r = max(cands, key=lambda r: marginal(r, A))
        A.append(r); used.add(r["record_id"])
    return G(A), A


def beam(k=5):
    beams = [([], 0.0)]
    for col in slots:
        nxt = []
        for (A, _) in beams:
            used = {r["record_id"] for r in A}
            for r in pruned[col]:
                if r["record_id"] in used:
                    continue
                nb = A + [r]
                nxt.append((nb, G(nb)))
        nxt.sort(key=lambda x: -x[1])
        beams = nxt[:k]
    return beams[0][1], beams[0][0]


opt, _ = exhaustive()
g, _ = greedy()
b, _ = beam(5)
print("\n=== 4. Greedy vs Beam vs Exhaustif (optimum réel) ===")
print(f"  Exhaustif (OPT) : {math.exp(opt):.4f}x  (log={opt:.4f})")
print(f"  Beam(k=5)       : {math.exp(b):.4f}x  ({100*b/opt:.2f}% de OPT en log)")
print(f"  Greedy          : {math.exp(g):.4f}x  ({100*g/opt:.2f}% de OPT en log)")
print(f"  garantie théorique greedy sous-modulaire sur matroïde >= 50%")
n_combos = len(pruned['Red'])*len(pruned['Blue'])*len(pruned['Green'])
print(f"  (exhaustif a évalué {n_combos} combinaisons après élagage)")
