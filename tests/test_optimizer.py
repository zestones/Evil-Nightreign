#!/usr/bin/env python3
"""Regression tests for the optimizer core.

Three pillars, each pinned to something externally verified:
  * aggregation reproduces the IN-GAME measurements of 2026-07-15
    (optimizer_mathematical_formulation.md §5.0),
  * pruning: the single-dominator counterexample is lossy, the s_c-aware rule
    of Theorem 2 is not,
  * beam(k=12) matches the exhaustive optimum on a real pruned context.
"""
import math

import pytest

from nightreign.optimize import aggregation, pruning, search
from nightreign.optimize.context import Context

ATK = ("atk", "phys")


def _relic(*copies):
    """Synthetic parsed relic: copies = (key, stacks, value)."""
    return [(key, stacks, {ATK: value}) for key, stacks, value in copies]


# ---- aggregation: the three game-verified stacking rules ----

def _mult(parsed_relics):
    return math.exp(aggregation.aggregate(parsed_relics)[ATK])


def test_levels_of_a_group_coexist():
    # Dark Night of the Baron: x1.18 (sigma=1) + x1.23 (sigma=0) on ONE relic
    # -> measured x1.452 in game (crit 241 -> 350), not max(1.18, 1.23).
    both = _relic(("critLvl0", True, math.log(1.18)), ("critLvl1", False, math.log(1.23)))
    assert _mult([both]) == pytest.approx(1.18 * 1.23, rel=1e-9)


def test_sigma0_counts_once():
    # adding a second x1.23 copy changed nothing in game (350 -> 350).
    both = _relic(("critLvl0", True, math.log(1.18)), ("critLvl1", False, math.log(1.23)))
    second = _relic(("critLvl1", False, math.log(1.23)))
    assert _mult([both, second]) == pytest.approx(_mult([both]), rel=1e-9)


def test_sigma1_copies_stack():
    # two x1.18 carriers measured x1.188 over one (282 -> 335) -> multiplicative.
    one = _relic(("critLvl0", True, math.log(1.18)))
    assert _mult([one, one]) == pytest.approx(1.18 ** 2, rel=1e-9)


def test_sigma1_profile_sums_intra_relic_copies():
    # one real relic carries the same sigma=1 key three times (Q-2).
    triple = _relic(*[("shards", True, 0.1)] * 3)
    assert aggregation.profile(triple)[(ATK, "shards")] == pytest.approx(0.3)


def test_real_relic_dark_night_of_the_baron():
    relics, effects = _load_real()
    dark = [r for r in relics if r["name"] == "darkNightOfTheBaron"]
    if not dark:
        pytest.skip("relic not in this collection")
    ctx = Context("Wylder")
    parsed = aggregation.parse_relic(dark[0], effects, ctx)
    assert _mult([parsed]) == pytest.approx(1.18 * 1.23, rel=1e-6)


# ---- pruning: Theorem 2 vs the naive rule ----

def _pool(entries):
    return {("normal", "Red"): [(r, p, aggregation.profile(p)) for r, p in entries]}


def _mini_candidates():
    rp = _relic(("g", True, 0.20))
    r = _relic(("g", True, 0.10))
    z = _relic(("junk", True, 0.01))
    mk = lambda i, parsed: ({"record_id": i}, parsed)
    return [mk(1, rp), mk(2, r), mk(3, z)]


def _score(parsed_relics):
    return math.exp(aggregation.aggregate(parsed_relics).get(ATK, 0.0))


def test_single_dominator_pruning_is_lossy_with_two_slots():
    cands = [(r, p, aggregation.profile(p)) for r, p in _mini_candidates()]
    slots = [("normal", "Any"), ("normal", "Any")]
    full = {("normal", "Red"): cands}
    naive = {("normal", "Red"): pruning.prune_pool(cands, s_c=1)}
    correct = {("normal", "Red"): pruning.prune_pool(cands, s_c=2)}
    opt_full, _ = search.exhaustive_search(slots, full, _score)
    opt_naive, _ = search.exhaustive_search(slots, naive, _score)
    opt_sc, _ = search.exhaustive_search(slots, correct, _score)
    assert opt_full == pytest.approx(math.exp(0.30))     # dominated relic still helps
    assert opt_naive < opt_full                          # naive rule loses the optimum
    assert opt_sc == pytest.approx(opt_full)             # Theorem 2 rule is lossless


# ---- beam vs exhaustive on real data ----

def _load_real():
    import json
    from nightreign.resources import constants
    relics = json.load(open(constants.DATA_CURATED / "relics.json"))
    effects = json.load(open(constants.DATA_CURATED / "effects.json"))
    return relics, effects


def test_beam_matches_exhaustive_on_real_context():
    relics, effects = _load_real()
    ctx = Context("Duchess", weapon_type="Greatsword")
    slots = [("normal", "Red"), ("normal", "Red"), ("normal", "Blue")]
    pools = {}
    for relic in relics:
        if relic["type"] == "DeepRelic":
            continue
        parsed = aggregation.parse_relic(relic, effects, ctx)
        parsed = [(k, s, {ATK: c[ATK]}) for k, s, c in parsed if ATK in c]
        if parsed:
            pools.setdefault(("normal", relic["color"]), []).append(
                (relic, parsed, aggregation.profile(parsed)))
    pruned = {key: pruning.prune_pool(entries,
                                      pruning.slots_accepting([c for _k, c in slots], key[1]))
              for key, entries in pools.items() if key[1] in ("Red", "Blue")}
    opt, _ = search.exhaustive_search(slots, pruned, _score)
    beam, _ = search.beam_search(slots, pruned, _score, k=12)
    assert beam == pytest.approx(opt, rel=1e-12)
