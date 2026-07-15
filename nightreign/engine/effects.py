#!/usr/bin/env python3
"""Turn resolved relic effects into per-type attack multipliers.

Consumes data/curated/effects.json (produced by datagen/effects.py), which already
holds each effect's REAL magnitude resolved through the AttachEffect system.

NOTE on stacking: multiplicative combination is a first approximation. Real
Nightreign stacking varies per effect; that calibration is future work.
Stdlib only.
"""
import json

from nightreign.resources import constants

RATE_FIELD_TO_TYPE = {
    "physicsAttackRate": "phys",
    "magicAttackRate": "mag",
    "fireAttackRate": "fire",
    "thunderAttackRate": "thunder",
    "darkAttackRate": "dark",  # Holy
}
DAMAGE_TYPES = ("phys", "mag", "fire", "thunder", "dark")


def load_effects():
    """{effect_id(str): {magnitude, on_hit, condition, characters, ...}}."""
    return json.load(open(constants.DATA_CURATED / "effects.json"))


def effect_multipliers(effect_id, effects):
    """Per-type attack multipliers contributed by a single resolved effect."""
    magnitude = (effects.get(str(effect_id)) or {}).get("magnitude", {})
    out = {}
    for field, dtype in RATE_FIELD_TO_TYPE.items():
        rate = magnitude.get(field)
        if isinstance(rate, (int, float)) and rate > 0:
            out[dtype] = rate
    return out


def attack_multipliers(effect_ids, effects, combine="mult"):
    """Combine several effects into one multiplier per damage type."""
    result = {t: 1.0 for t in DAMAGE_TYPES}
    for eid in effect_ids:
        for dtype, rate in effect_multipliers(eid, effects).items():
            if combine == "mult":
                result[dtype] *= rate
            else:
                result[dtype] += (rate - 1.0)
    return result


def best_single_multiplier(effects, owned_effect_ids):
    """Highest single-effect multiplier available per damage type (a simple proxy)."""
    best = {t: 1.0 for t in DAMAGE_TYPES}
    for eid in owned_effect_ids:
        for dtype, rate in effect_multipliers(eid, effects).items():
            best[dtype] = max(best[dtype], rate)
    return best
