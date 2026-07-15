#!/usr/bin/env python3
"""Status ailments: buildup fields, proc models, fight-amortized expected damage.

Mechanics (extracted from the game params): every hit adds the weapon's buildup
(+ relic on-hit buildup) to the target's gauge; it procs at the resistance
threshold, then the gauge RESETS and the threshold ESCALATES (ResistCorrectParam
per boss — after N activations the fill target is base*addRate_N + addPoint_N,
per the game's own field annotations). Cumulative buildup to each proc is the
running sum: Gladius bleed lands at ~5.6 / 17.6 / 39.8 hits — derived from the
formula, and independently close to the player's rough "first ~5, second ~20".
Procs are FRONT-LOADED: a fight lands only a few, not a steady stream.

Two proc shapes:
  * BURST (bleed, frost) — a one-shot % of max HP per proc. Damage over a fight
    = (procs reached) x burst.
  * DoT (poison, rot) — applies a damage-over-time that later procs REFRESH, so
    once the first proc lands the DoT is up for the rest of the fight (until its
    last application's duration runs out). Damage = uptime_seconds x tick_rate;
    uptime and the hits->seconds conversion use the weapon's class cadence.

Proc value calibration (2026-07-15):
  * bleed  — 15% max HP. LOCKED by a player-measured proc of 371 (day-3 troll)
    and the engine's canonical hemorrhage row (SpEffectParam 1612).
  * frost  — 5% (SpEffectParam 1611, structural twin of bleed). To confirm.
  * poison — DoT 40s, 1.3s ticks, 10 HP + 0.10% max HP per tick. Structural.
  * rot    — DoT 40s, 1.3s ticks, 15 HP + 0.15% per tick. Structural.
  * sleep / madness / curse — no damage term (control / human-only / niche).
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

#: proc models: ("burst", fraction_of_maxHP)
#:           or ("dot", duration_s, tick_interval_s, flat_per_tick, hp_fraction_per_tick)
PROC = {
    "bleed": ("burst", 0.15),
    "frost": ("burst", 0.05),
    "poison": ("dot", 40.0, 1.3, 10.0, 0.0010),
    "rot": ("dot", 40.0, 1.3, 15.0, 0.0015),
}

#: frost proc also applies "damage taken x1.15 for 30s" (SpEffectParam family
#: of 195 rows, stateInfo 260); near-permanent uptime once procced.
FROST_DEBUFF = 1.15


def is_dot(status):
    return (PROC.get(status) or (None,))[0] == "dot"


def burst_damage(status, target_max_hp):
    """One burst proc's damage (0 for DoT / non-damage statuses)."""
    model = PROC.get(status)
    if not model or model[0] != "burst":
        return 0.0
    return model[1] * target_max_hp


def dot_rate(status, target_max_hp):
    """DoT damage per SECOND while active (0 for non-DoT)."""
    model = PROC.get(status)
    if not model or model[0] != "dot":
        return 0.0
    _kind, _dur, tick, flat, fraction = model
    return (flat + fraction * target_max_hp) / tick


def dot_duration(status):
    model = PROC.get(status)
    return model[1] if model and model[0] == "dot" else 0.0


def proc_damage(status, target_max_hp):
    """Damage of ONE proc — a burst for bleed/frost, a full DoT run otherwise
    (display/first-proc helper; the fight model uses uptime, not this)."""
    if is_dot(status):
        return dot_rate(status, target_max_hp) * dot_duration(status)
    return burst_damage(status, target_max_hp)


def _proc_count(total_buildup, thresholds):
    """Number of procs `total_buildup` reaches (escalating thresholds)."""
    n = 0
    for t in thresholds:
        if total_buildup >= t:
            n += 1
        else:
            return n
    step = (thresholds[-1] - thresholds[-2]) if len(thresholds) > 1 else thresholds[-1]
    if step > 0:
        n += int((total_buildup - thresholds[-1]) // step)
    return n


def _proc_hits(buildup, thresholds, max_hits):
    """Hit counts at which each proc lands, within `max_hits`. Beyond the listed
    thresholds the resistance keeps rising by the last increment."""
    hits = []
    step = (thresholds[-1] - thresholds[-2]) if len(thresholds) > 1 else thresholds[-1]
    k, t = 0, list(thresholds)
    while True:
        thr = t[k] if k < len(t) else t[-1] + step * (k - len(t) + 1)
        h = thr / buildup
        if h > max_hits:
            break
        hits.append(h)
        k += 1
        if k > 200:
            break
    return hits


def expected_per_hit(buildup, resistance, status, target_max_hp,
                     thresholds=None, fight_hits=None, cadence=1.0):
    """Expected extra damage per hit from `status`, amortized over the fight.

    BURST: (#procs reached) x burst / fight_hits.
    DoT: once the first proc lands, the DoT is up until the last proc's duration
    runs out (later procs refresh it); damage = uptime_s x tick_rate, per hit
    = that / fight_hits. Needs `cadence` (attacks/s) to convert hits<->seconds.
    Falls back to the naive first-proc rate only without escalation data.

    resistance >= 999 is immune."""
    if not buildup or not resistance or resistance >= 999:
        return 0.0

    if not (thresholds and fight_hits):  # no escalation data: first-proc rate
        return (buildup / resistance) * proc_damage(status, target_max_hp)

    hits = _proc_hits(buildup, thresholds, fight_hits)
    if not hits:
        return 0.0

    if is_dot(status):
        cad = cadence or 1.0
        first_s = hits[0] / cad
        last_s = hits[-1] / cad
        fight_s = fight_hits / cad
        # DoT active from the first proc until its coverage lapses or the fight
        # ends (consecutive procs are closer than the DoT duration -> continuous)
        active_s = max(0.0, min(fight_s, last_s + dot_duration(status)) - first_s)
        total = active_s * dot_rate(status, target_max_hp)
    else:
        total = len(hits) * burst_damage(status, target_max_hp)
    return total / fight_hits
