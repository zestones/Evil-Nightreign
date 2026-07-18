#!/usr/bin/env python3
"""Two-axis search test — where greedy actually FAILS and beam recovers.

    S(A) = w * exp(Agg_off(A)) + (1-w) * exp(Agg_def(A))

a weighted sum of two exponentials, monotone but NOT submodular. On the
single-color instance the coupling is weak but real (one-instance keys span
colors), and greedy happens to be exact there — measured, not structural.
Real trouble needs "Any" slots: the placement becomes a genuine bipartite
matching (transversal matroid), and the myopic slot-by-slot greedy fails by two
DISTINCT mechanisms, both deepest at w=1.0 (single axis, where S is a monotone
transform of the submodular Agg_off — so neither is the two-axis coupling):

  * vessel order (Any slots first): the Any slots absorb relics the scarce
    colored slot needed — a matching artifact (bites even modular objectives);
  * restrictive slots first: the early colored pick covers a sigma=0 key the
    best Any candidate also carries — coverage overlap, the genuinely
    submodular diminishing-returns trap.

Neither order is safe: with toggles off the failures split cleanly (vessel
order -> Urn, restrictive-first -> Chalice), with real toggles on the vessel
order fails on BOTH vessels (down to -8.7% at w=1.0). Beam is exact everywhere.

We sweep contexts (element x status-toggles x vessel x weight) and report the
DISTRIBUTION of ratios for: greedy in vessel-slot order, greedy with the
restrictive (non-Any) slots first, and beam (top-k partial builds), against the
EXHAUSTIVE optimum. Pools are pruned with the multiplicity-aware rule of
Theorem 2: a relic is dropped only if >= s_c relics strictly dominate it, where
s_c = number of slots accepting its color (single-dominator pruning is unsafe
with "Any" slots — see the counterexample in optimizer-math.md S3).

Aggregation and profiles are PER KEY (optimizer-math.md S2); the data
invariants backing this are checked by experiments/validate_invariants.py.

Run with --verify-pruning to also enumerate the UNPRUNED pools and check
OPT(pruned) == OPT(full) in every context (slower; validates Theorem 2 in the
Any-slot regime instead of assuming it).
"""
import collections
import itertools
import json
import math
import sys

from nightreign.resources import constants

RELICS = json.load(open(constants.DATA_CURATED / "relics.json"))
EFFECTS = json.load(open(constants.DATA_CURATED / "effects.json"))
CUT_FIELDS = ["neutralDamageCutRate", "fireDamageCutRate", "magicDamageCutRate",
              "thunderDamageCutRate", "darkDamageCutRate"]

# SYNTHETIC vessels (only slot colors matter): two "Any" slots = maximal
# coupling, deliberately harsher than the game, where vessels carry at most ONE
# Any slot (the Chalices) — but repeated colors and the mono-color Grails
# ([Red,Red,Red], ...) make s_c up to 3 real. See vessels.json.
VESSELS = [
    ("Urn [Any,Any,Red]", ["Any", "Any", "Red"]),
    ("Chalice [Any,Blue,Green]", ["Any", "Blue", "Green"]),
]
ELEMENTS = ["fire", "magic", "thunder"]
# Toggle sets are DIMENSIONS of the condition taxonomy (resources/conditions.py):
# an effect is active iff its condition dimension is None or committed here.
# (An earlier draft matched condition *labels* that exist nowhere in the data,
# which silently made the toggle axis inert — dimensions actually gate effects.)
STATUS_TOGGLES = [
    set(),
    {"situational", "low_hp"},
]
WEIGHTS = [0.0, 0.3, 0.5, 0.7, 1.0]


def parse(relic, element, toggles):
    """(key, stacks, off_value, def_value) for active effects."""
    out = []
    for e in relic["effects"]:
        info = EFFECTS.get(str(e["id"]))
        if not info:
            continue
        cond = info.get("condition") or {}
        if cond.get("dimension") is not None and cond.get("dimension") not in toggles:
            continue
        m = info.get("magnitude") or {}
        off = math.log(m[f"{element}AttackRate"]) if m.get(f"{element}AttackRate", 1) > 1 else 0.0
        cuts = [m[f] for f in CUT_FIELDS if isinstance(m.get(f), (int, float)) and 0 < m[f] < 1]
        deff = -sum(math.log(c) for c in cuts)
        if off or deff:
            out.append((e["key"], bool(e.get("stacks")), off, deff))
    return out


def agg(parsed_relics, idx):
    """Per-key aggregation of axis `idx` (2=offense, 3=defense): copies of a
    stacking key add; a non-stacking key counts once (max over copies)."""
    sums = collections.defaultdict(float)
    ones = {}
    for cs in parsed_relics:
        for c in cs:
            v = c[idx]
            if v == 0:
                continue
            if c[1]:
                sums[c[0]] += v
            else:
                ones[c[0]] = max(ones.get(c[0], 0.0), v)
    return sum(sums.values()) + sum(ones.values())


def offdef(parsed_relics):
    return math.exp(agg(parsed_relics, 2)), math.exp(agg(parsed_relics, 3))


def score(parsed_relics, w):
    eo, ed = offdef(parsed_relics)
    return w * eo + (1 - w) * ed


def profile(cs):
    """(axis, key) -> value; sigma=1 keys sum intra-relic copies, else max."""
    p = collections.defaultdict(float)
    for c in cs:
        for idx, tag in ((2, "o"), (3, "d")):
            v = c[idx]
            if v == 0:
                continue
            if c[1]:
                p[(tag, c[0])] += v
            else:
                p[(tag, c[0])] = max(p[(tag, c[0])], v)
    return dict(p)


def dominates(a, b):
    return all(a.get(k, 0.0) >= v - 1e-12 for k, v in b.items())


def build_pool(element, toggles):
    """Per-color candidates (rid, parsed, profile), unpruned."""
    by_color = collections.defaultdict(list)
    for r in RELICS:
        if r["type"] == "DeepRelic":
            continue
        cs = parse(r, element, toggles)
        if cs:
            by_color[r["color"]].append((r["record_id"], cs, profile(cs)))
    return by_color


def prune_for_vessel(by_color, slots):
    """Theorem 2: drop a relic only if >= s_c relics strictly dominate it."""
    pool = {}
    for color, arr in by_color.items():
        s_c = sum(1 for s in slots if s == "Any" or s == color)
        pool[color] = [
            (rid, cs) for i, (rid, cs, pf) in enumerate(arr)
            if sum(1 for j, o in enumerate(arr)
                   if j != i and dominates(o[2], pf) and o[2] != pf) < s_c
        ]
    return pool


def candidates_for(pool, slot):
    return [(rid, cs) for color in pool for (rid, cs) in pool[color]
            if slot == "Any" or slot == color]


def exhaustive_all_w(slots, pool):
    """One enumeration, OPT for every weight at once."""
    best = {w: -1.0 for w in WEIGHTS}
    for combo in itertools.product(*(candidates_for(pool, s) for s in slots)):
        ids = [x[0] for x in combo]
        if len(set(ids)) != len(ids):
            continue
        eo, ed = offdef([x[1] for x in combo])
        for w in WEIGHTS:
            s = w * eo + (1 - w) * ed
            if s > best[w]:
                best[w] = s
    return best


def greedy(slots, pool, w):
    """Myopic slot-by-slot greedy, in the given slot order."""
    chosen, used = [], set()
    for s in slots:
        cands = [(rid, cs) for (rid, cs) in candidates_for(pool, s) if rid not in used]
        if not cands:
            continue
        rid, cs = max(cands, key=lambda x: score([c[1] for c in chosen] + [x[1]], w))
        chosen.append((rid, cs))
        used.add(rid)
    return score([c[1] for c in chosen], w)


def restrictive_first(slots):
    return sorted(slots, key=lambda s: s == "Any")


def beam(slots, pool, w, k=12):
    beams = [[]]
    for s in slots:
        nxt = []
        for partial in beams:
            used = {x[0] for x in partial}
            for (rid, cs) in candidates_for(pool, s):
                if rid not in used:
                    nxt.append(partial + [(rid, cs)])
        nxt.sort(key=lambda p: -score([x[1] for x in p], w))
        beams = nxt[:k]
    return score([x[1] for x in beams[0]], w)


def main():
    verify_pruning = "--verify-pruning" in sys.argv
    rows, losses = [], []
    for element in ELEMENTS:
        for toggles in STATUS_TOGGLES:
            by_color = build_pool(element, toggles)
            if sum(len(v) for v in by_color.values()) < 3:
                continue
            for vname, slots in VESSELS:
                pool = prune_for_vessel(by_color, slots)
                opt = exhaustive_all_w(slots, pool)
                if verify_pruning:
                    full = {c: [(rid, cs) for rid, cs, _ in arr]
                            for c, arr in by_color.items()}
                    opt_full = exhaustive_all_w(slots, full)
                    for w in WEIGHTS:
                        if opt_full[w] > opt[w] + 1e-9:
                            losses.append((vname, element, bool(toggles), w,
                                           opt[w] / opt_full[w]))
                for w in WEIGHTS:
                    g = greedy(slots, pool, w) / opt[w]
                    gr = greedy(restrictive_first(slots), pool, w) / opt[w]
                    b = beam(slots, pool, w) / opt[w]
                    rows.append((vname, element, bool(toggles), w, g, gr, b))

    print(f"Swept {len(rows)} contexts (element x toggles x vessel x weight)\n")
    print("Cases where either greedy variant < OPT (beam alongside):")
    print(f"  {'vessel':26}{'elem':8}{'tog':4}{'w':>4}  "
          f"{'greedy/OPT':>11}{'restr/OPT':>10}{'beam/OPT':>9}")
    for vname, elem, tog, w, g, gr, b in rows:
        if g < 0.9999 or gr < 0.9999:
            print(f"  {vname:26}{elem:8}{int(tog):<4}{w:>4}  "
                  f"{g:>11.4f}{gr:>10.4f}{b:>9.4f}")

    g_all = [r[4] for r in rows]
    gr_all = [r[5] for r in rows]
    b_all = [r[6] for r in rows]

    def line(name, vals):
        print(f"  {name:22}: min {min(vals):.4f}, mean {sum(vals)/len(vals):.4f}, "
              f"< OPT in {sum(1 for v in vals if v < 0.9999)}/{len(vals)} cases")

    print("\nDistribution:")
    line("greedy/OPT", g_all)
    line("greedy restr-first/OPT", gr_all)
    line("beam(k=12)/OPT", b_all)

    if verify_pruning:
        print(f"\nTheorem 2 check (s_c-aware pruning vs FULL pool): "
              f"{len(losses)} lossy case(s) out of {len(rows)}")
        for l in losses:
            print(f"  LOSS: {l}")

    print("\nEvery static slot order fails somewhere (matching artifact on the Urn,"
          "\nsigma=0 coverage overlap on the Chalice; which one bites depends on the"
          "\ntoggle set), always deepest at w=1.0 (single axis) -> not the two-axis"
          "\ncoupling. Beam (k=12) is exact in every swept case and is what the"
          " pipeline keeps.")


if __name__ == "__main__":
    main()
