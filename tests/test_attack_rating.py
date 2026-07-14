#!/usr/bin/env python3
"""Ground-truth regression test for the AR formula.

These are REAL in-game Attack Rating readings (Duchess). If a change to the
formula or the AR factor breaks them, this test fails loudly.

Run: python tests/test_attack_rating.py   (or `pytest`)
"""
import json

from nightreign.engine import attack_rating
from nightreign.resources import constants

TOLERANCE = 1.5  # AR

# weapon id -> {Duchess hero_stats row id: measured in-game AR}
MEASURED = {
    "1750000": {"40000": 38, "40001": 46, "40002": 67, "40003": 72},  # Duchess Dagger, lv 1/2/12/15
    "1040000": {"40003": 94},                                          # Reduvia, lv15
    "1010000": {"40003": 122},                                         # Black Knife, lv15
}


def _cases():
    tables = attack_rating.load_tables()
    hero = json.load(open(constants.DATA_RAW / "hero_stats.json"))
    for weapon_id, readings in MEASURED.items():
        for hero_id, expected in readings.items():
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
