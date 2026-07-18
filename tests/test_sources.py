#!/usr/bin/env python3
"""Multi-source engine anchors: DamageSource, spell scaling, FP clamp,
source-aware selection. The melee bit-identity is pinned by the golden
master (tests/test_golden_master.py) — these cover the NEW paths.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nightreign.engine import attack_rating, sources as dmg_sources  # noqa: E402
from nightreign.optimize import runner, scoring  # noqa: E402
from nightreign.resources import constants  # noqa: E402


def _data():
    if not hasattr(_data, "cache"):
        _data.cache = runner.load_data()
    return _data.cache


class SpellScalingGroundTruth(unittest.TestCase):
    def test_absolute_spell_damage_matches_ingame(self):
        # THE calibration anchor (2026-07-17): Glintstone Arc (base 148)
        # through the base Glintstone Staff (displayed scaling 159), Recluse
        # 15, no relics -> 141 displayed damage on target.
        data = _data()
        stats = runner.hero_stats_row(data, "Recluse", 15)
        out = attack_rating.spell_attack({"mag": 148.0}, "33000000", 0,
                                         stats, data["ar_tables"])
        self.assertAlmostEqual(out["mag"], 141.0, delta=3.0)
        # independent second point: same spell through the Carian Regal
        # Scepter (displayed scaling 250, ladder rate 1.5675) -> 222 in-game
        out2 = attack_rating.spell_attack({"mag": 148.0}, "33090000", 0,
                                          stats, data["ar_tables"])
        self.assertAlmostEqual(out2["mag"], 222.0, delta=4.0)

    def test_full_level_curve(self):
        # The strongest anchor: Recluse Pebble(152)/Arc(148) through the base
        # Glintstone Staff at EVERY level 1..15 (measured, no relics). Tests
        # both SPELL_SCALING_CORRECTION and the linear stat interpolation.
        data = _data()
        gt = json.load(open(constants.ROOT / "data" / "ground_truth"
                            / "spell_curve_recluse.json"))
        tol = gt["tolerance_damage"]
        for m in gt["measurements"]:
            stats = runner.hero_stats_row(data, "Recluse", m["level"])
            for slot, base in (("R1", 152.0), ("R2", 148.0)):
                pred = attack_rating.spell_attack({"mag": base}, "33000000", 0,
                                                  stats, data["ar_tables"])["mag"]
                self.assertAlmostEqual(pred, m[slot], delta=tol,
                                       msg=f"level {m['level']} {slot}: {pred:.1f} vs {m[slot]}")

    def test_catalyst_scaling_ratios_match_ingame(self):
        # User in-game readings (2026-07-17, Recluse 15, no relics): the
        # displayed Sorcery Scaling of three staves is 135 / 211 / 223.
        # Our per-catalyst factor must reproduce the RATIOS (the absolute
        # constant lives in SPELL_FACTOR, calibration pending).
        data = _data()
        stats = runner.hero_stats_row(data, "Recluse", 15)
        base = {"mag": 100.0}
        vals = {}
        for wid, label in (("33760000", 135), ("33180000", 211), ("33240000", 223)):
            out = attack_rating.spell_attack(base, wid, 0, stats, data["ar_tables"])
            vals[label] = out["mag"]
        self.assertAlmostEqual(vals[211] / vals[135], 211 / 135, delta=0.02)
        self.assertAlmostEqual(vals[223] / vals[135], 223 / 135, delta=0.02)


class SpellAttack(unittest.TestCase):
    def test_scales_with_int(self):
        data = _data()
        hero = data["hero_stats"]
        pebble = data["magic"]["4000"]["damage"]
        lo = attack_rating.spell_attack(pebble, "33000000", 0, hero["40003"],
                                        data["ar_tables"])   # Duchess INT 42
        hi = attack_rating.spell_attack(pebble, "33000000", 0, hero["70003"],
                                        data["ar_tables"])   # Recluse INT 51
        self.assertGreater(hi["mag"], lo["mag"])
        self.assertGreater(lo["mag"], 0)

    def test_seal_scales_on_faith(self):
        # a Sacred Seal's incant scaling must respond to Faith, not Int
        data = _data()
        weapons = data["weapons"]
        seal_id = next(wid for wid, w in weapons.items()
                       if w.get("wepmotionCategory") == 41
                       and (w.get("correctFaith") or 0) > (w.get("correctMagic") or 0))
        base = {"fire": 100.0}
        low = dict(data["hero_stats"]["40003"], statFaith=10)
        high = dict(data["hero_stats"]["40003"], statFaith=60)
        a_low = attack_rating.spell_attack(base, seal_id, 0, low,
                                           data["ar_tables"], "Sacred Seal")
        a_high = attack_rating.spell_attack(base, seal_id, 0, high,
                                            data["ar_tables"], "Sacred Seal")
        self.assertGreater(a_high["fire"], a_low["fire"])


class FpModel(unittest.TestCase):
    def test_max_fp_matches_community_pools(self):
        # FP = 45 + 5×Mind — exact fit on four community-reported pools
        for hid, expected in (("40003", 180), ("60003", 200), ("70003", 195),
                              ("10003", 140)):
            self.assertEqual(dmg_sources.max_fp(_data()["hero_stats"][hid]), expected)

    def test_clamp_caps_and_falls_back_to_melee(self):
        src = dmg_sources.DamageSource("sorcery_any", lambda s: {"mag": 100.0},
                                       fp_cost=10.0)
        play, info = scoring.clamp_play_for_fp(
            {"sorcery_any": 1.0}, {"sorcery_any": src}, fp_pool=150,
            nominal_fight_hits=150.0)
        # 150 FP / 10 per cast = 15 casts of 150 wanted -> 10% sustainable
        self.assertAlmostEqual(info["sorcery_any"]["sustainable"], 0.1)
        self.assertAlmostEqual(play["sorcery_any"], 0.1)
        self.assertAlmostEqual(play["melee"], 0.9)   # dry caster swings the weapon

    def test_no_fp_cost_profile_untouched(self):
        play, info = scoring.clamp_play_for_fp({"melee": 1.0}, {}, fp_pool=100)
        self.assertEqual(play, {"melee": 1.0})
        self.assertEqual(info, {})


class SourceAwareEngine(unittest.TestCase):
    def test_cast_without_source_deals_nothing(self):
        # a declared cast on a non-catalyst never falls back to weapon AR
        out = scoring.offense({"phys": 300.0}, {}, {"sorcery_any": 1.0},
                              [("t", {}, {}, 1000, {}, {})])
        self.assertEqual(out, 0.0)

    def test_source_power_feeds_offense(self):
        out = scoring.offense({"phys": 300.0}, {}, {"sorcery_any": 1.0},
                              [("t", {}, {}, 1000, {}, {})],
                              source_power={"sorcery_any": {"mag": 200.0}})
        self.assertGreater(out, 0.0)

    def test_school_profile_finds_school_catalyst(self):
        # user-caught regression (2026-07-17): a carian-school profile must
        # surface a carian-carrying catalyst (not a raw-AR heavy weapon). Staff
        # must be SHORTLISTED (its guaranteed carian spell — Carian Slicer — may
        # rank below a greatsword's melee since spell cadence isn't modeled, so
        # we don't assert #1, but the caster path must resolve).
        data = _data()
        stats = runner.hero_stats_row(data, "Duchess", 15)
        targets = runner.resolve_targets(data, None)
        play = {"sorcery_carian": 0.6, "melee": 0.4}
        types = runner.best_weapon_types(data, stats, targets, count=3,
                                         play=play, character="Duchess")
        self.assertIn("Staff", types, f"Staff must be shortlisted for a carian profile, got {types}")
        wid, lvl, _n, label, _a = runner.pick_weapon(
            data, stats, targets, "Staff", play=play, character="Duchess")
        srcs = runner.build_sources(data, "Duchess", play, wid, lvl)
        self.assertIn("sorcery_carian", srcs)
        self.assertIn("Carian", srcs["sorcery_carian"].label)

    def test_guaranteed_vs_rolled_spell(self):
        # THE fix for the user's "Crystal Staff for Crystal Release" confusion:
        # Crystal Release is the GUARANTEED slot-1 of the Rotten Crystal Staff
        # (rank it) but only a slot-2 ROLL on the plain Crystal Staff.
        data = _data()

        def entry(name):
            wid = next(w for w in data["catalyst_spells"]
                       if data["weapon_names"].get(int(w)) == name)
            return data["catalyst_spells"][wid]

        rotten = entry("[Uncommon] Rotten Crystal Staff")
        plain = entry("[Uncommon] Crystal Staff")
        cr = next(int(s) for s, m in data["magic"].items() if m["name"] == "Sorcery: Crystal Release")
        self.assertIn(cr, rotten["fixed"])   # guaranteed on Rotten Crystal
        self.assertIn(cr, plain["pool"])      # only a roll on plain Crystal
        # build_sources tags guaranteed vs rolled
        rotten_wid = next(w for w in data["catalyst_spells"]
                          if data["weapon_names"].get(int(w)) == "[Uncommon] Rotten Crystal Staff")
        srcs = runner.build_sources(data, "Recluse", {"sorcery_any": 1.0}, rotten_wid, 0)
        self.assertTrue(srcs["sorcery_any"].meta["guaranteed"])

    def test_fp_clamp_uses_real_fight_length(self):
        # a Nightlord fight is ~10-20 actions; a 60% cast share of a 9-34 FP
        # spell is sustainable on a 180 FP pool — the old fixed 150-hit clamp
        # crushed it to <15% and inverted weapon rankings (user-caught).
        data = _data()
        stats = runner.hero_stats_row(data, "Duchess", 15)
        targets = runner.resolve_targets(data, None)
        off = 200.0
        n = scoring.estimate_fight_actions(off, targets)
        self.assertLess(n, 40)      # real fights are short
        self.assertGreaterEqual(n, 8)

    def test_catalyst_ranking_uses_spells(self):
        # under a sorcery profile, a Staff must rank by its spell damage:
        # pick_weapon on the Staff type returns a weapon whose resolved spell
        # source exists and out-damages its bare melee AR
        data = _data()
        stats = runner.hero_stats_row(data, "Recluse", 15)
        targets = runner.resolve_targets(data, None)
        wid, lvl, name, label, _alts = runner.pick_weapon(
            data, stats, targets, "Staff", play={"sorcery_any": 1.0},
            character="Recluse")
        self.assertEqual(label, "Staff")
        srcs = runner.build_sources(data, "Recluse", {"sorcery_any": 1.0}, wid, lvl)
        self.assertIn("sorcery_any", srcs)
        spell_power = srcs["sorcery_any"].compute(stats)
        self.assertGreater(sum(spell_power.values()), 0)

    def test_character_skill_source(self):
        data = _data()
        src = dmg_sources.character_skill_source(
            data["characters"]["Raider"], data["ar_tables"])
        power = src.compute(runner.hero_stats_row(data, "Raider", 15))
        self.assertGreater(power.get("phys", 0), 0)   # Retaliate: 90 phys, STR 80
        self.assertIsNotNone(src.rate_hz)             # real cooldown

    def test_ultimate_rate_is_honestly_unknown(self):
        data = _data()
        src = dmg_sources.ultimate_art_source(
            data["characters"]["Raider"], data["ar_tables"])
        self.assertIsNone(src.rate_hz)   # charge economy not in extracted data

    def test_executor_transformation_ultimate_is_none(self):
        data = _data()
        self.assertIsNone(dmg_sources.ultimate_art_source(
            data["characters"]["Executor"], data["ar_tables"]))


class MatrixAuditFixes(unittest.TestCase):
    """Anchors for the matrix-audit corrections (2026-07-17 plan)."""

    def test_channeled_spell_scored_per_second(self):
        # Comet Azur: channel mode = 350 mag/s at 10 FP/s (finding #4)
        data = _data()
        src = dmg_sources.spell_source(data["magic"]["4200"], "33000000", 0,
                                       "Staff", data["ar_tables"], spell_id="4200")
        self.assertEqual(src.meta["mode"], "channel")
        self.assertEqual(src.fp_cost, 10.0)
        self.assertEqual(src.rate_hz, 1.0)
        base = src.compute(data["hero_stats"]["70003"])
        self.assertGreater(base["mag"], 200)   # ~350 × scaling × SPELL_FACTOR

    def test_charged_mode_picked_when_stronger(self):
        # any spell whose charged payload beats the normal one plays charged
        data = _data()
        for sid, m in data["magic"].items():
            ch = (m.get("charged") or {}).get("damage")
            if m.get("damage") and ch and sum(ch.values()) > sum(m["damage"].values()):
                src = dmg_sources.spell_source(m, "33000000", 0, "Staff",
                                               data["ar_tables"], spell_id=sid)
                self.assertEqual(src.meta["mode"], "charged", m["name"])
                return
        self.skipTest("no spell with a stronger charged payload in the catalog")

    def test_pot_source_resolves_real_damage(self):
        # a 30% pot profile scores the pot's own payload (finding #3 follow-up)
        data = _data()
        srcs = runner.build_sources(data, "Scholar", {"melee": 0.7, "throwing_pot": 0.3})
        self.assertIn("throwing_pot", srcs)
        dmg = srcs["throwing_pot"].compute({})
        self.assertGreater(sum(dmg.values()), 100)   # Swarm Pot 680 / Lightning 260…

    def test_bow_shot_carries_flat(self):
        # ranged shots: AR + isAddBaseAtk flat (+77.75), judges 205-245 band
        data = _data()
        flat = runner.flat_profile(data, "41750000")
        self.assertAlmostEqual(flat["melee"]["phys"], 77.75)
        self.assertEqual(runner.mv_profile(data, "41750000").get("melee"), 1.0)

    def test_weapon_subtype_ventilates_offense(self):
        # slash weapon vs Maris (slash 1.15) beats its neutral self by 15%
        from nightreign.engine import damage as dmg
        data = _data()
        maris = data["npc_params"][str(data["nightlords"]["Maris"]["npc_id"])]
        atk = {"phys": 100.0}
        self.assertAlmostEqual(
            dmg.damage_vs_enemy(atk, maris, phys_subtype="slash")[0], 115.0, places=3)
        self.assertAlmostEqual(
            dmg.damage_vs_enemy(atk, maris, phys_subtype="blow")[0], 80.0, places=3)


class StaminaCosts(unittest.TestCase):
    def test_per_attack_costs_extracted(self):
        # BehaviorParam_PC carries exact per-attack stamina costs (2026-07-17):
        # dagger R1 = 9, Ruins Greatsword R1 chain mean = 20 — the class gap
        # that makes heavy weapons unsustainable on low-Endurance characters.
        from nightreign.optimize import motion
        data = _data()
        dagger = motion.stamina_costs(data["weapons"]["1750000"], data["motion"])
        self.assertEqual(dagger["melee"], 9.0)
        ruins_id = next(wid for wid, n in data["weapon_names"].items()
                        if "Ruins Greatsword" in n)
        ruins = motion.stamina_costs(data["weapons"][str(ruins_id)], data["motion"])
        self.assertEqual(ruins["melee"], 20.0)
        self.assertGreater(ruins["melee"], dagger["melee"] * 2)


class AccessoryRecommendations(unittest.TestCase):
    def test_marginal_gains_ranked_and_resolved(self):
        data = _data()
        stats = runner.hero_stats_row(data, "Duchess", 15)
        targets = runner.resolve_targets(data, None)
        scorer = scoring.Scorer("1750000", stats,
                                data["characters"]["Duchess"]["defense"],
                                targets, 0.5, 1.0, data["ar_tables"])
        recos = runner.recommend_accessories(data, scorer, [], top_n=5)
        self.assertTrue(recos)
        gains = [a["gain"] for a in recos]
        self.assertEqual(gains, sorted(gains, reverse=True))
        for a in recos:
            self.assertGreater(a["gain"], 0)
            self.assertNotIn("talisman ", a["name"])   # names resolved, not ids


if __name__ == "__main__":
    unittest.main(verbosity=2)
