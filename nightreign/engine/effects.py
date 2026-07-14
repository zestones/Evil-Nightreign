#!/usr/bin/env python3
"""Aggregate a set of relic effects into per-type attack multipliers.

Maps SpEffect "xxxAttackRate" fields to damage types and combines them.

NOTE on stacking: multiplicative combination is a first approximation. Real
Nightreign stacking varies per effect (some additive, some capped); that
calibration is future work. The combination strategy is isolated here.
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


def load_effect_params():
    return json.load(open(constants.DATA_RAW / "effect_params.json"))


def effect_multipliers(effect_id, effect_params):
    """Per-type attack multipliers contributed by a single effect (default 1.0)."""
    fields = effect_params.get(str(effect_id)) or effect_params.get(effect_id) or {}
    out = {}
    for field, dtype in RATE_FIELD_TO_TYPE.items():
        rate = fields.get(field)
        if isinstance(rate, (int, float)) and rate > 0:
            out[dtype] = rate
    return out


def attack_multipliers(effect_ids, effect_params, combine="mult"):
    """Combine several effects into one multiplier per damage type."""
    result = {t: 1.0 for t in DAMAGE_TYPES}
    for eid in effect_ids:
        for dtype, rate in effect_multipliers(eid, effect_params).items():
            if combine == "mult":
                result[dtype] *= rate
            else:
                result[dtype] += (rate - 1.0)
    return result


def best_single_multiplier(effect_params, owned_effect_ids):
    """Highest single-effect multiplier available per damage type (a simple proxy)."""
    best = {t: 1.0 for t in DAMAGE_TYPES}
    for eid in owned_effect_ids:
        for dtype, rate in effect_multipliers(eid, effect_params).items():
            best[dtype] = max(best[dtype], rate)
    return best
