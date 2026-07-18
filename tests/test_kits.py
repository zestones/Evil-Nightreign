#!/usr/bin/env python3
"""Kit-sheet anchors: schema of the 10 sheets, sourced-figure doctrine,
paradigm-aware source construction, and the offense factor mechanics."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nightreign.optimize import runner  # noqa: E402
from nightreign.resources import kits  # noqa: E402

PARADIGMS = {"strike", "replay", "utility"}


class KitSheets(unittest.TestCase):
    def test_all_ten_characters_have_sheets(self):
        self.assertEqual(sorted(kits.KITS), sorted(runner.HERO_ORDER))

    def test_schema(self):
        for name, k in kits.KITS.items():
            self.assertIn(k.get("skill_paradigm"), PARADIGMS, name)
            self.assertIn(k.get("ultimate_paradigm"), PARADIGMS, name)
            self.assertTrue(k.get("archetypes"), f"{name}: no archetype presets")
            for arch in k["archetypes"]:
                self.assertTrue(arch.get("play"), f"{name}/{arch.get('name')}")
                self.assertAlmostEqual(sum(arch["play"].values()), 1.0, places=6,
                                       msg=f"{name}/{arch['name']} play must sum to 1")
            # doctrine: every scored figure carries a source
            passive = k.get("passive") or {}
            if passive.get("value") is not None:
                self.assertTrue(passive.get("source"), f"{name} passive unsourced")
            for buff in k.get("team_buffs") or []:
                if buff.get("factor") is not None:
                    self.assertTrue(buff.get("source"), f"{name}/{buff['name']} unsourced")


class OffenseFactor(unittest.TestCase):
    def test_neutral_by_default(self):
        # no toggles, melee profile: every kit factor must be 1.0 (constant
        # factors are display-side; the default profile shows raw numbers)
        for name in kits.KITS:
            f, details = kits.offense_factor(name, frozenset(), {"melee": 1.0})
            self.assertEqual(f, 1.0, name)
            self.assertEqual(details, {}, name)

    def test_tenacity_gated_by_status_build(self):
        f, d = kits.offense_factor("Executor", frozenset({"status_build"}), {"melee": 1.0})
        self.assertAlmostEqual(f, 1.2)
        self.assertIn("Tenacity", d)

    def test_fighters_resolve_gated_by_low_hp(self):
        f, _ = kits.offense_factor("Raider", frozenset({"low_hp"}), {"melee": 1.0})
        self.assertAlmostEqual(f, 1.5)

    def test_restage_replay_window(self):
        # 50% of a 3s window every 12s -> ×1.125 average offense
        f, d = kits.offense_factor("Duchess", frozenset(), {"melee": 0.8, "char_skill": 0.2})
        self.assertAlmostEqual(f, 1.125)
        self.assertIn("replay", d)

    def test_marking_team_buff_via_play(self):
        f, d = kits.offense_factor("Ironeye", frozenset(),
                                   {"melee": 0.8, "char_skill": 0.2})
        self.assertAlmostEqual(f, 1.10)
        self.assertIn("Marking", d)

    def test_unsourced_figures_never_score(self):
        # Recluse's Soulblood split is wiki-unconfirmed (factor None): the
        # ultimate declared in play must contribute NO factor
        f, d = kits.offense_factor("Recluse", frozenset(),
                                   {"sorcery_any": 0.8, "ultimate_art": 0.2})
        self.assertEqual(f, 1.0)


class ParadigmAwareSources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = runner.load_data()

    def test_replay_skill_builds_no_strike_source(self):
        # Duchess Restage is a replay: char_skill must NOT become a hidden-
        # weapon strike source (the kit factor carries it instead)
        srcs = runner.build_sources(self.data, "Duchess",
                                    {"melee": 0.8, "char_skill": 0.2})
        self.assertNotIn("char_skill", srcs)

    def test_strike_skill_builds_a_source(self):
        srcs = runner.build_sources(self.data, "Raider",
                                    {"melee": 0.8, "char_skill": 0.2})
        self.assertIn("char_skill", srcs)

    def test_utility_ultimate_builds_no_source(self):
        # Guardian's Wings of Salvation is utility (rez), not a strike
        srcs = runner.build_sources(self.data, "Guardian",
                                    {"melee": 0.8, "ultimate_art": 0.2})
        self.assertNotIn("ultimate_art", srcs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
