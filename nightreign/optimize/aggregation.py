#!/usr/bin/env python3
"""Per-key effect aggregation — the verified stacking model (optimizer_mathematical_formulation.md §2).

Unit of aggregation = the effect KEY (INV-1/2, machine-checked by
experiments/validate_invariants.py; rules game-verified §5.0):
  * sigma(key)=1 : every copy adds (modular),
  * sigma(key)=0 : one instance counts (max over copies),
  * distinct levels of a group are distinct keys and coexist.

Multiplicative fields (attack rates, cut rates, maxHpRate) aggregate in LOG
space; additive fields (flat stat bonuses) aggregate on raw values. Both follow
the same per-key rule. Never key stacking off the group: 3 real groups mix
flags across their levels.
"""
import collections
import math

# multiplicative magnitude fields the optimizer tracks, by axis
ATTACK_RATE_FIELDS = {
    "physicsAttackRate": "phys",
    "magicAttackRate": "mag",
    "fireAttackRate": "fire",
    "thunderAttackRate": "thunder",
    "darkAttackRate": "dark",
}
CUT_RATE_FIELDS = {
    "neutralDamageCutRate": "phys",
    "slashDamageCutRate": "slash",
    "blowDamageCutRate": "blow",
    "thrustDamageCutRate": "thrust",
    "magicDamageCutRate": "mag",
    "fireDamageCutRate": "fire",
    "thunderDamageCutRate": "thunder",
    "darkDamageCutRate": "dark",
}
MAX_HP_FIELD = "maxHpRate"
# status buildup fields (relic magnitude or on-hit effects) -> status name
STATUS_BUILDUP_FIELDS = {
    "bloodAttackPower": "bleed", "poizonAttackPower": "poison",
    "diseaseAttackPower": "rot", "freezeAttackPower": "frost",
    "sleepAttackPower": "sleep", "madnessAttackPower": "madness",
    "curseAttackPower": "curse",
}
# additive stat bonus fields -> hero_stats field they add to
STAT_ADD_FIELDS = {
    "addStrengthStatus": "statStrength",
    "addDexterityStatus": "statDexterity",
    "addFaithStatus": "statFaith",
    "addLuckStatus": "statArcane",
    "addLifeForceStatus": "statVigor",
}


def parse_relic(relic, effects_db, context):
    """Active effect copies of a relic in a context.

    Returns a list of (key, stacks, contrib) where contrib maps:
      ("atk", dtype, action) -> log multiplier  (offense; action "*" = every attack)
      ("cut", dtype)  -> -log cut rate    (defense axis, >= 0)
      ("hp",)         -> log maxHpRate
      ("stat", field) -> flat stat bonus  (raw, additive)
      ("stbuild", status) -> flat status buildup per hit (raw, additive)
    Only effects whose condition is satisfied by the context contribute.
    Action-gated offense (crit-only, throwing-knife-only, ...) carries its
    action class so the scorer can weight it by the play profile.
    """
    out = []
    for entry in relic["effects"]:
        info = effects_db.get(str(entry["id"]))
        if not info or not context.effect_active(info, entry):
            continue
        magnitude = info.get("magnitude") or {}
        actions = info.get("actions") or ["*"]
        contrib = {}
        # INV-3 (asserted by validate_invariants.py): no tracked field carries a
        # malus, so every log contribution below is > 0 — monotonicity holds.
        for field, dtype in ATTACK_RATE_FIELDS.items():
            v = magnitude.get(field)
            if isinstance(v, (int, float)) and v > 1:
                for action in actions:
                    contrib[("atk", dtype, action)] = math.log(v)
        for field, dtype in CUT_RATE_FIELDS.items():
            v = magnitude.get(field)
            if isinstance(v, (int, float)) and 0 < v < 1:
                contrib[("cut", dtype)] = -math.log(v)
        v = magnitude.get(MAX_HP_FIELD)
        if isinstance(v, (int, float)) and v > 1:
            contrib[("hp",)] = math.log(v)
        on_hit = info.get("on_hit") or {}
        for field, status in STATUS_BUILDUP_FIELDS.items():
            v = (magnitude.get(field) or 0) + (on_hit.get(field) or 0)
            if isinstance(v, (int, float)) and v > 0:
                contrib[("stbuild", status)] = float(v)
        for field, stat in STAT_ADD_FIELDS.items():
            v = magnitude.get(field)
            if isinstance(v, (int, float)) and v:
                contrib[("stat", stat)] = float(v)
        if contrib:
            out.append((entry["key"], bool(entry.get("stacks")), contrib))
    return out


def aggregate(parsed_relics):
    """Per-key aggregation over a set of parsed relics -> {dimension: total}.

    Applies the sigma rule per (dimension, key): stacking copies sum, non-
    stacking keys count once (max over copies) — for every dimension alike.
    """
    sums = collections.defaultdict(float)
    ones = {}
    for copies in parsed_relics:
        for key, stacks, contrib in copies:
            for dim, v in contrib.items():
                if stacks:
                    sums[(dim, key)] += v
                else:
                    slot = (dim, key)
                    ones[slot] = max(ones.get(slot, 0.0), v)
    total = collections.defaultdict(float)
    for (dim, _key), v in sums.items():
        total[dim] += v
    for (dim, _key), v in ones.items():
        total[dim] += v
    return total


def profile(parsed_relic):
    """Dominance profile of ONE relic: {(dimension, key): value}.

    sigma=1 keys sum their intra-relic copies (a real relic carries the same
    key three times); sigma=0 keys take the max copy.
    """
    prof = collections.defaultdict(float)
    for key, stacks, contrib in parsed_relic:
        for dim, v in contrib.items():
            slot = (dim, key)
            if stacks:
                prof[slot] += v
            else:
                prof[slot] = max(prof[slot], v)
    return dict(prof)


def dominates(profile_a, profile_b, eps=1e-12):
    """profile_a >= profile_b on every dimension (within eps)."""
    return all(profile_a.get(k, 0.0) >= v - eps for k, v in profile_b.items())
