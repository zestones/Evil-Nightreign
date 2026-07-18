#!/usr/bin/env python3
"""Per-key effect aggregation — the verified stacking model (optimizer-math.md §2).

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
# additive stat bonus fields -> hero_stats field they add to. Only stats the
# scorer actually consumes are tracked: the five AR scaling stats (Str/Dex/Int/
# Fai/Arc — attack_rating.SCALING) plus Vigor (survival). Mind (FP) and Endurance
# (stamina) touch neither axis and are deliberately left out.
STAT_ADD_FIELDS = {
    "addStrengthStatus": "statStrength",
    "addDexterityStatus": "statDexterity",
    "addMagicStatus": "statIntelligence",  # Magic = Intelligence; AR scales on it
    "addFaithStatus": "statFaith",
    "addLuckStatus": "statArcane",
    "addLifeForceStatus": "statVigor",
}


def parse_relic(relic, effects_db, context):
    """Active effect copies of a relic in a context.

    Returns a list of (key, stacks, contrib) where contrib maps:
      ("atk", dtype, action) -> log multiplier  (offense; action "*" = every attack)
      ("cut", dtype)  -> -log cut rate    (defense axis; signed: curses go < 0)
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
        is_debuff = info.get("is_debuff")
        contrib = {}
        # Multiplicative fields aggregate in LOG space, sign-correct by design
        # ("higher = better" on every axis): buffs land on the good side of 1,
        # Deep-of-Night curses on the bad side, and BOTH are admitted. The only
        # load-bearing guard is the log domain (v > 0); the sign is carried by
        # the monotone exp() downstream (scoring.py). INV-3 (no malus) is thus
        # restricted to non-debuff keys — see validate_invariants.py.
        for field, dtype in ATTACK_RATE_FIELDS.items():
            v = magnitude.get(field)
            if isinstance(v, (int, float)) and v > 0 and v != 1:
                for action in actions:
                    contrib[("atk", dtype, action)] = math.log(v)
        for field, dtype in CUT_RATE_FIELDS.items():
            v = magnitude.get(field)
            if isinstance(v, (int, float)) and v > 0 and v != 1:
                contrib[("cut", dtype)] = -math.log(v)
        v = magnitude.get(MAX_HP_FIELD)
        if isinstance(v, (int, float)) and v > 0 and v != 1:
            contrib[("hp",)] = math.log(v)
        # status buildup here is the ENEMY's (offense). A curse's *AttackPower is
        # buildup inflicted on the PLAYER (out of axis) — never count it.
        if not is_debuff:
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
                    # seed at the first occurrence, not 0.0: a non-stacking curse
                    # carries v < 0, and max(0.0, v) would erase it.
                    ones[slot] = v if slot not in ones else max(ones[slot], v)
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
                # seed at first occurrence (a curse slot can be negative)
                prof[slot] = v if slot not in prof else max(prof[slot], v)
    return dict(prof)


def dominates(profile_a, profile_b, eps=1e-12):
    """profile_a >= profile_b on every dimension (within eps).

    Iterates the UNION of keys: with signed contributions (curses), a key present
    only in profile_a may be negative, so skipping it (iterating b alone) would
    let a cursed relic falsely dominate a clean one — unsound for Theorem 2.
    """
    keys = set(profile_a) | set(profile_b)
    return all(profile_a.get(k, 0.0) >= profile_b.get(k, 0.0) - eps for k in keys)
