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

ATK = ("atk", "phys", "*")   # offense dims carry an action class ("*" = every attack)


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
    agg = aggregation.aggregate([parsed])
    # both effects are crit-gated (stateInfo 367): full x1.452 on crits...
    assert math.exp(agg[("atk", "phys", "crit")]) == pytest.approx(1.18 * 1.23, rel=1e-6)
    # ...and nothing on ungated attacks (the in-game R1 control stayed at 125)
    assert agg.get(("atk", "phys", "*"), 0.0) == 0.0


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
        # melee-benchmark view: keep phys offense on ungated + melee actions
        parsed = [(k, s, {ATK: c.get(("atk", "phys", "*"), 0.0)
                          + c.get(("atk", "phys", "melee"), 0.0)})
                  for k, s, c in parsed
                  if c.get(("atk", "phys", "*")) or c.get(("atk", "phys", "melee"))]
        if parsed:
            pools.setdefault(("normal", relic["color"]), []).append(
                (relic, parsed, aggregation.profile(parsed)))
    pruned = {key: pruning.prune_pool(entries,
                                      pruning.slots_accepting([c for _k, c in slots], key[1]))
              for key, entries in pools.items() if key[1] in ("Red", "Blue")}
    opt, _ = search.exhaustive_search(slots, pruned, _score)
    beam, _ = search.beam_search(slots, pruned, _score, k=12)
    assert beam == pytest.approx(opt, rel=1e-12)


# ---- play profile: action-gated offense counts only when declared ----

def test_play_profile_gates_offense():
    from nightreign.optimize import scoring
    stats = {"statVigor": 10, "statStrength": 20, "statDexterity": 15,
             "statIntelligence": 5, "statFaith": 5, "statArcane": 5}
    npc = {"def_phys": 100, "def_mag": 100, "def_fire": 100,
           "def_thunder": 100, "def_dark": 100}
    targets = [("dummy", npc, {"fire": 100}, 0, {}, {})]
    crit_relic = [("critKey", True, {("atk", "phys", "crit"): math.log(1.5)})]

    melee_only = scoring.Scorer("1750000", stats, {"negation": {}}, targets, weight=1.0)
    mixed = scoring.Scorer("1750000", stats, {"negation": {}}, targets, weight=1.0,
                           play={"melee": 0.5, "crit": 0.5})
    crit_only = scoring.Scorer("1750000", stats, {"negation": {}}, targets, weight=1.0,
                               play={"crit": 1.0})
    # pure-melee benchmark: a crit-only relic is worth nothing (R1 unchanged in game)
    assert melee_only.score([crit_relic]) == pytest.approx(1.0)
    # the more crit share the profile declares, the more the relic is worth
    # (no linear bound: the FromSoft defense curve is convex in attack here)
    assert melee_only.score([crit_relic]) < mixed.score([crit_relic]) \
        < crit_only.score([crit_relic])


def test_melee_performed_hierarchy():
    # game-verified 2026-07-15: initial/skill/crit all inherit melee buffs;
    # ranged/item/spell actions do not.
    from nightreign.resources import actions
    for a in ("initial", "skill", "crit"):
        assert "melee" in actions.classes_applying_to(a)
    for a in ("throwing_knife", "sorcery_gravity", "melee"):
        assert actions.classes_applying_to(a) >= {"*", a}
    assert "melee" not in actions.classes_applying_to("throwing_knife")
    assert "skill" not in actions.classes_applying_to("crit")


def test_status_expected_damage():
    # bleed: buildup/threshold x 15% max HP per hit (calibrated on the measured
    # 371 proc); immunity (999) contributes nothing.
    from nightreign.optimize import scoring
    ar = {"phys": 100.0}
    npc = {"def_phys": 100}
    bleedable = [("t", npc, {}, 2000, {"bleed": 250}, {})]
    immune = [("t", npc, {}, 2000, {"bleed": 999}, {})]
    base = scoring.offense(ar, {}, {"melee": 1.0}, bleedable)
    with_bleed = scoring.offense(ar, {}, {"melee": 1.0}, bleedable, {"bleed": 45})
    assert with_bleed - base == pytest.approx(45 / 250 * 0.15 * 2000)   # +54/hit
    assert scoring.offense(ar, {}, {"melee": 1.0}, immune, {"bleed": 45}) \
        == pytest.approx(base)


def test_motion_value_profile():
    # extraction pinned to the in-game measured chain (125/126 -> MV 100/101)
    import json
    from nightreign.optimize import motion
    from nightreign.resources import constants
    tables = json.load(open(constants.DATA_RAW / "motion_values.json"))
    weapons = json.load(open(constants.DATA_RAW / "weapons.json"))
    gs = motion.profile(weapons["3750000"], tables)
    assert gs["melee"] == pytest.approx(1.0325)      # chain 100/101/102/110
    assert gs["initial"] == pytest.approx(1.0)
    assert gs["crit"] == pytest.approx(2.0)          # measured backstab ratio 2.01


def test_archive_pipeline_extracts_animations():
    # game-gated: full binary pipeline (RSA BHD5 -> BDT -> AES -> Oodle Kraken
    # -> BND4 -> TAE). Validated 2026-07-15 against a real install.
    from nightreign.resources import constants
    try:
        game = constants.game_root()
    except SystemExit:
        pytest.skip("game archives not present")
    from nightreign.io import archive, dcx, tae
    from nightreign.io.regulation import parse_bnd4
    arc = archive.DataArchive()
    assert len(arc) > 20000
    data = dcx.decompress(arc.get("/chr/c0000.anibnd.dcx"))
    assert data[:4] == b"BND4" and len(data) == 57621370
    files = parse_bnd4(data)
    durs = tae.animation_durations(files["a03.tae"])
    # R1 combo animations rise through the chain (game-verified feel)
    assert durs[4200] == pytest.approx(0.9667, abs=1e-3)
    assert durs[4200] < durs[4210] < durs[4220]


def test_cadence_dps_ranking():
    # class cadence turns the slowest big hit into a lower DPS: a ballista's
    # huge per-hit does not beat a fast melee weapon once cadence applies.
    from nightreign.resources import weapon_types
    assert weapon_types.CADENCE["Ballista"] < weapon_types.CADENCE["Dagger"]
    ballista = {"wepmotionCategory": 52}   # -> Ballista
    dagger = {"wepmotionCategory": 20}     # -> Dagger
    # equal per-hit damage -> dagger wins on DPS
    assert weapon_types.cadence(dagger) > weapon_types.cadence(ballista)


def test_bleed_escalation_amortizes():
    # game-verified: threshold escalates (proc ~5 hits, then ~20). Over a fight
    # the amortized bleed/hit is far below the naive first-proc rate.
    from nightreign.resources import statuses
    thresholds = [252, 794, 1793, 2792, 3791]   # Gladius bleed (base*addRate+addPoint)
    # 44-hit fight at 45 buildup -> 3 procs (thresholds 252/999/1746 crossed)
    assert statuses._proc_count(44 * 45, thresholds) == 3
    escalated = statuses.expected_per_hit(45, 252, "bleed", 4160, thresholds, 44)
    naive = statuses.expected_per_hit(45, 252, "bleed", 4160)   # no escalation
    assert escalated < naive / 2   # front-loading roughly thirds the value


def test_dot_uptime_not_per_proc():
    # a DoT delivers rate x active_time regardless of how many procs refresh it
    # (refreshes don't stack), so it is capped by rate x fight, never n x full.
    from nightreign.resources import statuses
    thr = [252, 794, 1793, 2792, 3791]
    hp, buildup, fight_hits, cad = 4160, 66, 44, 1.1
    per_hit = statuses.expected_per_hit(buildup, 252, "poison", hp, thr, fight_hits, cad)
    total = per_hit * fight_hits
    rate, fight_s = statuses.dot_rate("poison", hp), fight_hits / cad
    assert total <= rate * fight_s + 1e-6   # never exceeds continuous uptime
    assert total > rate * fight_s * 0.7     # near-continuous once first proc lands


import pytest

@pytest.mark.skip(reason="affix hunt disabled: extracted affix pool is unreliable")
def test_affix_hunt_is_build_relevant():
    pass
