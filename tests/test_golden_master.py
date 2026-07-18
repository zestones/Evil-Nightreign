#!/usr/bin/env python3
"""Golden-master pin of the full optimize() pipeline output.

The multi-source engine refactor (docs/roadmap.md phase B) must keep every
pure-melee profile BIT-IDENTICAL: same scores, same weapon, same relic picks.
These tests freeze representative contexts BEFORE the refactor and fail on
any deviation afterwards.

Regenerating (deliberate, reviewed act — never do it to silence a failure):
    NR_UPDATE_GOLDEN=1 uv run pytest tests/test_golden_master.py

Regeneration log:
  2026-07-17  physical sub-types wired into offense (weapon atkAttribute →
              slash/blow/thrust target multipliers) + DPS-consistent type
              shortlist. duchess_don5_dagger top1: Reduvia 1.3206 → Blade of
              Calling 1.3163; duchess_don5_auto top1: → Raptor Talons 1.3268.
              Deliberate model fix (matrix audit finding #2, 35-44% swings).
  2026-07-17c Scarlet Rot recalibrated to the Nightreign-confirmed total
              (6% HP + 600, faster 1.0s ticks vs the old structural 1.3s).
              recluse_adel_staff_melee top1 Staff of the Guilty -> Rotten
              Crystal Staff (same relics, ~0.3% score). Deliberate.
  2026-07-17b ranged-shot model (isAddBaseAtk flat +77.75 on bow shots, shot
              rows classified from the 200 judge band) + sub-type swing on
              the fixed-Greatsword context (Golden Order → Dark Moon vs
              Gladius). wylder_gladius_greatsword + ironeye_don5_bow_mixed
              regenerated. Deliberate (bows were undervalued ~40%).
"""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nightreign.optimize import runner  # noqa: E402

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"
UPDATE = os.environ.get("NR_UPDATE_GOLDEN") == "1"

# Representative contexts: fixed weapon types keep runs fast; one full "auto"
# exploration pins pick_weapon/best_weapon_types; a Staff-in-melee context pins
# the exact case that must NOT change when spell sources land (melee profile).
CONTEXTS = {
    "duchess_don5_dagger": dict(
        character="Duchess", don=5, weapon_type="Dagger", weight=0.5),
    "duchess_don5_dagger_nodebuffs": dict(
        character="Duchess", don=5, weapon_type="Dagger", weight=0.5,
        count_debuffs=False),
    "wylder_gladius_greatsword": dict(
        character="Wylder", boss="Gladius", weapon_type="Greatsword", weight=0.3),
    "recluse_adel_staff_melee": dict(
        character="Recluse", boss="Adel", weapon_type="Staff", weight=0.5),
    "duchess_don3_generic": dict(
        character="Duchess", don=3, weapon_type=runner.GENERIC, weight=0.5),
    "ironeye_don5_bow_mixed_play": dict(
        character="Ironeye", don=5, weapon_type="Bow", weight=0.5,
        play={"melee": 0.7, "crit": 0.3},
        refused_curses=("lowerAttackWhenBelowMaxHP",)),
    "duchess_don5_auto": dict(
        character="Duchess", don=5, weight=0.5),
}


def _snapshot(results):
    """Stable, comparison-friendly view of optimize() output."""
    return [{
        "score": round(r["score"], 9),
        "weapon_id": r["weapon_id"],
        "weapon": r["weapon"],
        "vessel": r["vessel"],
        "picks": sorted(rel["record_id"] for _slot, rel in r["picks"]),
        "offense_ratio": round(r["breakdown"]["offense_ratio"], 9),
        "survival_ratio": round(r["breakdown"]["survival_ratio"], 9),
    } for r in results]


class GoldenMaster(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = runner.load_data()

    def _check(self, name):
        results = runner.optimize(top=3, data=self.data, **CONTEXTS[name])
        snap = _snapshot(results)
        path = GOLDEN_DIR / f"{name}.json"
        if UPDATE:
            GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
            json.dump(snap, open(path, "w"), indent=1, ensure_ascii=False)
            self.skipTest(f"golden updated: {path.name}")
        self.assertTrue(path.exists(), f"golden fixture missing: {path.name} "
                        "(generate with NR_UPDATE_GOLDEN=1)")
        expected = json.load(open(path))
        self.assertEqual(snap, expected, f"golden mismatch for context '{name}'")


def _make_test(name):
    def test(self):
        self._check(name)
    return test


for _name in CONTEXTS:
    setattr(GoldenMaster, f"test_{_name}", _make_test(_name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
