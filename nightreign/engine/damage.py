#!/usr/bin/env python3
"""Elden Ring / Nightreign damage model.

Final damage for a single damage type:
    damage = (1 - negation) * defense_multiplier(atk, def) * attack_power * motion_value

where defense_multiplier is FromSoft's piecewise attack/defense curve (r = atk/def).
The curve is continuous, clamped to [0.1, 0.9]. Verified against the community
"Calculating Damage" references (same engine as Elden Ring, confirmed for Nightreign).

Damage types: phys, mag, fire, thunder (lightning), dark (holy).
Stdlib only.
"""

# NpcParam defense field for each damage type (flat defense, feeds the atk/def curve).
DEFENSE_FIELD = {
    "phys": "def_phys",
    "mag": "def_mag",
    "fire": "def_fire",
    "thunder": "def_thunder",
    "dark": "def_dark",  # "dark" is the internal name for Holy in Nightreign
}

# Physical sub-type extra defenses (added on top of def_phys for that sub-type).
PHYS_SUBTYPE_DEFENSE = {"slash": "def_slash", "blow": "def_blow", "thrust": "def_thrust"}

# NpcParam per-element DAMAGE MULTIPLIER (the real elemental weakness/resistance).
# 1.0 = neutral, >1.0 = weakness (e.g. 1.2 = +20%), <1.0 = resistance (e.g. 0.6).
# This, not def_*, is what makes one element better than another against a boss.
CUT_RATE_FIELD = {
    "phys": "neutralDamageCutRate",
    "mag": "magicDamageCutRate",
    "fire": "fireDamageCutRate",
    "thunder": "thunderDamageCutRate",
    "dark": "darkDamageCutRate",
}
PHYS_SUBTYPE_CUT_RATE = {
    "slash": "slashDamageCutRate",
    "blow": "blowDamageCutRate",
    "thrust": "thrustDamageCutRate",
}


def defense_multiplier(attack, defense):
    """REFUTED for Nightreign player damage — measured in game 2026-07-15.

    Two daggers on the same def_phys=100 enemy dealt EXACTLY their displayed
    attack (103 and 122) where this Elden Ring curve predicts a x0.40
    multiplier; every NPC in the game carries the same flat 100 defense
    (inert placeholder). Player damage is linear: attack x MV x cut rate.
    Kept only as historical reference — do not reintroduce without a new
    in-game measurement contradicting the linear model.
    """
    if defense <= 0:
        return 0.9
    r = attack / defense
    if r <= 0.125:
        return 0.10
    if r <= 1.0:
        return 19.2 / 49.0 * (r - 0.125) ** 2 + 0.1
    if r <= 2.5:
        return -0.4 / 3.0 * (r - 2.5) ** 2 + 0.7
    if r <= 8.0:
        return -0.8 / 121.0 * (r - 8.0) ** 2 + 0.9
    return 0.90


def damage(attack_power, defense, motion_value=1.0, cut_rate=1.0, negation=0.0):
    """Damage of one type against one enemy — LINEAR (game-verified).

    damage = attack x motion value x cut rate x (1 - negation). The flat
    def_* fields are identical (100) on all 200 NPCs and measured inert:
    in-game hits equal the displayed attack exactly (2026-07-15, two-dagger
    duel on a camp soldier), so no attack/defense curve applies.

    attack_power : effective AR of this type (weapon + scaling + relic multipliers)
    defense      : ignored (kept for signature stability; inert in Nightreign)
    motion_value : attack move's motion value (1.0 = neutral / per-hit AR)
    cut_rate     : enemy per-element damage multiplier (weakness>1, resistance<1)
    negation     : extra fractional negation (0..1), usually 0 for enemies
    """
    return (1.0 - negation) * attack_power * motion_value * cut_rate


def enemy_defense(npc, damage_type, phys_subtype=None):
    """Enemy flat defense for a damage type from an npc_params.json row."""
    base = npc.get(DEFENSE_FIELD[damage_type], 0) or 0
    if damage_type == "phys" and phys_subtype in PHYS_SUBTYPE_DEFENSE:
        base += npc.get(PHYS_SUBTYPE_DEFENSE[phys_subtype], 0) or 0
    return base


def enemy_cut_rate(npc, damage_type, phys_subtype=None):
    """Enemy per-element damage multiplier (1.0 if unspecified)."""
    field = CUT_RATE_FIELD[damage_type]
    if damage_type == "phys" and phys_subtype in PHYS_SUBTYPE_CUT_RATE:
        field = PHYS_SUBTYPE_CUT_RATE[phys_subtype]
    rate = npc.get(field)
    return rate if isinstance(rate, (int, float)) else 1.0


def damage_vs_enemy(attack_by_type, npc, motion_value=1.0, phys_subtype=None, weak_point=False):
    """Total damage of a multi-type attack against one enemy.

    attack_by_type : {"fire": AR, "thunder": AR, ...} effective attack power per type.
    weak_point     : if True, apply the enemy's weakPartsDamageRate multiplier.
    Returns (total, per_type_breakdown).
    """
    weak_mult = (npc.get("weakPartsDamageRate", 1.0) or 1.0) if weak_point else 1.0
    per_type = {}
    for dtype, ar in attack_by_type.items():
        if ar <= 0:
            continue
        d = enemy_defense(npc, dtype, phys_subtype)
        cut = enemy_cut_rate(npc, dtype, phys_subtype)
        per_type[dtype] = damage(ar, d, motion_value, cut) * weak_mult
    return sum(per_type.values()), per_type
