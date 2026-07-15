#!/usr/bin/env python3
"""Status ailments: buildup fields, proc damage models, enemy resistance keys.

Mechanics (game engine): every hit adds the weapon's buildup (+ relic on-hit
buildup) to the target's gauge; the gauge caps at the target's resistance and
procs. Expected extra damage per hit = buildup / resistance x proc damage.

Proc damage calibration (2026-07-15):
  * bleed  — burst 15% of target max HP. LOCKED: player-measured proc of 371
    matches a day-3 troll (1901 HP x1.3) at 0.1%, and 15% is the engine's
    canonical hemorrhage value (SpEffectParam 1612: changeHpRate -15).
  * frost  — burst 5% (SpEffectParam 1611, the structural twin of the bleed
    row: same shape, same tick, adjacent id). To confirm in game.
  * poison — DoT, stateInfo 2 rows: 40s at 1.3s ticks, 10 HP + 0.10% max HP
    per tick (~31 ticks). Structural.
  * rot    — DoT, stateInfo 5 row (sp 3128): 40s at 1.3s, 15 HP + 0.15% per
    tick. Structural.
  * sleep / madness / curse — no damage contribution modeled (sleep is crowd
    control, madness is human-only and bosses are mostly immune, curse is an
    instakill niche); their buildup is still extracted for future use.
"""

#: SpEffect buildup field -> status name (as used by enemy resistance tables)
BUILDUP_FIELDS = {
    "bloodAttackPower": "bleed",
    "poizonAttackPower": "poison",
    "diseaseAttackPower": "rot",
    "freezeAttackPower": "frost",
    "sleepAttackPower": "sleep",
    "madnessAttackPower": "madness",
    "curseAttackPower": "curse",
}

#: proc damage models: ("burst", fraction of max HP) or ("dot", ticks, flat, hp_fraction per tick)
PROC = {
    "bleed": ("burst", 0.15),
    "frost": ("burst", 0.05),
    "poison": ("dot", 30.8, 10.0, 0.0010),
    "rot": ("dot", 30.8, 15.0, 0.0015),
}


#: a DoT proc rarely delivers its full 40s: re-procs REFRESH the effect and
#: waste the remaining duration, and fights truncate it. Bursts pay instantly.
#: 0.5 is a documented placeholder until attack cadence data allows the exact
#: overlap computation (motion values / swing-speed work).
DOT_EFFICIENCY = 0.5

#: frost proc also applies "damage taken x1.15 for 30s" (SpEffectParam family
#: of 195 rows, stateInfo 260). A frost weapon procs every ~5-10 hits, so the
#: debuff is near-permanently up once the fight starts: modeled as a flat
#: multiplier on ALL damage dealt to non-immune targets.
FROST_DEBUFF = 1.15


def proc_damage(status, target_max_hp):
    """Expected damage of one proc of `status` on a target with that max HP
    (0.0 for the non-damage statuses)."""
    model = PROC.get(status)
    if model is None:
        return 0.0
    if model[0] == "burst":
        return model[1] * target_max_hp
    _kind, ticks, flat, fraction = model
    return DOT_EFFICIENCY * ticks * (flat + fraction * target_max_hp)


def expected_per_hit(buildup, resistance, status, target_max_hp):
    """Expected extra damage each hit contributes through this status.

    resistance >= 999 is the game's immunity convention."""
    if not buildup or not resistance or resistance >= 999:
        return 0.0
    return (buildup / resistance) * proc_damage(status, target_max_hp)
