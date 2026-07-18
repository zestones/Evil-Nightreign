#!/usr/bin/env python3
"""Ground-truth regression test for the AR formula.

REAL in-game Attack Rating readings (Duchess), loaded from the versioned
measurement bank data/ground_truth/attack_rating.json. If a change to the
formula or the AR factor breaks them, this test fails loudly.

Run: python tests/test_attack_rating.py   (or `pytest`)
"""
import json

from nightreign.engine import attack_rating
from nightreign.resources import constants

GROUND_TRUTH = json.load(open(constants.ROOT / "data" / "ground_truth" / "attack_rating.json"))
TOLERANCE = GROUND_TRUTH["tolerance_ar"]


def _cases():
    tables = attack_rating.load_tables()
    hero = json.load(open(constants.DATA_RAW / "hero_stats.json"))
    for m in GROUND_TRUTH["measurements"]:
        weapon_id, hero_id, expected = m["weapon_id"], m["hero_stats_id"], m["value"]
        predicted = sum(attack_rating.attack_rating(weapon_id, 0, hero[hero_id], tables).values())
        yield weapon_id, hero_id, predicted, expected


def test_attack_rating_matches_ingame():
    failures = []
    for weapon_id, hero_id, predicted, expected in _cases():
        if abs(predicted - expected) > TOLERANCE:
            failures.append(f"weapon {weapon_id} @ {hero_id}: {predicted:.1f} vs {expected} in-game")
    assert not failures, "AR mismatch:\n  " + "\n  ".join(failures)


if __name__ == "__main__":
    ok = True
    for weapon_id, hero_id, predicted, expected in _cases():
        delta = predicted - expected
        flag = "OK" if abs(delta) <= TOLERANCE else "FAIL"
        ok &= abs(delta) <= TOLERANCE
        print(f"  [{flag}] weapon {weapon_id} @ {hero_id}: {predicted:6.1f} vs {expected} ({delta:+.1f})")
    print("PASSED" if ok else "FAILED")
    raise SystemExit(0 if ok else 1)
