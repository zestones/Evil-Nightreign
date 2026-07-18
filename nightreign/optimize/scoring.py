#!/usr/bin/env python3
"""Build scoring: S = w * OFFENSE + (1 - w) * SURVIVAL (optimizer.md).

OFFENSE  — play-profile-weighted real damage vs the target. Each attack action
           a (melee, skill, crit, throwing knife, ...) has its own multiplier
           state: ungated effects apply to every action, action-gated effects
           only to theirs (decoded from the SpEffect sub-category / stateInfo
           gates — see resources/actions.py). With the play profile p:

               OFF = sum_a p_a * damage( AR * exp(Agg_* + Agg_a) )

           The default profile is the pure-melee benchmark p = {melee: 1.0},
           so crit-only or throwing-knife-only relics count for nothing unless
           the player declares those actions (--play).
SURVIVAL — one-shot margin proxy: (vigor x maxHpRate multipliers) divided by
           the target's biggest hit after character negation, relic damage-cut
           multipliers and Deep-of-Night attack scaling. Exact HP pools are
           deferred (optimizer.md): ranking uses the raw stats.

Both axes are normalized by the relic-less baseline, so S is dimensionless and
S = 1 means "no better than an empty vessel". Stat-boosting relics feed back
into AR inside the marginal step (optimizer_mathematical_formulation.md §6.5)
via a memoized AR recomputation — the only non-submodular coupling, handled
exactly. The per-action mixture is a weighted sum of exponentials: monotone,
not submodular — the regime §4 already assigns to beam + exhaustive checks.
"""
import math

from nightreign.engine import attack_rating, damage
from nightreign.optimize import aggregation
from nightreign.resources import actions, statuses
from nightreign.resources import constants as constants_module

# nightlords.json INCOMING max_damage keys -> engine damage types. These are
# ALREADY engine-typed (phys/mag/fire/thunder/dark — datagen/nightlords.py
# _ATK_ELEMENTS), so they must map to themselves; the magic/lightning/holy
# aliases cover the weakness-schema names should they ever appear. Before this,
# mag/thunder/dark fell through get()->None and the whole magic/lightning/holy
# incoming hit was silently dropped from survival (5 of 8 Nightlords lost their
# biggest hit; pure-magic Gnoster fell back to biggest_hit=1).
TARGET_TYPE_TO_ENGINE = {
    "phys": "phys", "slash": "slash", "blow": "blow", "thrust": "thrust",
    "mag": "mag", "fire": "fire", "thunder": "thunder", "dark": "dark",
    "magic": "mag", "lightning": "thunder", "holy": "dark",
}
# character negation naming -> engine damage types
NEGATION_TYPE_TO_ENGINE = {
    "phys": "phys", "slash": "slash", "blow": "blow", "thrust": "thrust",
    "magic": "mag", "fire": "fire", "thunder": "thunder", "dark": "dark",
}
AR_TYPES = ("phys", "mag", "fire", "thunder", "dark")


class Scorer:
    """Scores a parsed-relic set for one context (weapon, targets, weights)."""

    def __init__(self, weapon_id, hero_stats, char_defense, targets,
                 weight=0.5, don_attack_scale=1.0, ar_tables=None, play=None,
                 reinforce=3, off_baseline=None, weapon_status=None,
                 weapon_mv=None, cadence=1.0, sources=None, fp_pool=None,
                 phys_subtype=None, weapon_flat=None, weak_point=False):
        """targets: list of (name, npc_row, attacks_max_damage_dict).
        play: normalized {action: weight} — default pure-melee benchmark.
        off_baseline: offense normalizer shared by every weapon of a type (the
        type's bare-best weapon), so S ranks ABSOLUTE damage within the type —
        normalizing each weapon by its own bare damage would crown weak-bare
        weapons on inflated ratios. None = this weapon's own bare damage.
        reinforce: weapon upgrade level, clamped per weapon (Nightreign caps
        at +3) — +0 sits in the harshest zone of the defense curve and
        distorts weapon rankings, so the endgame level is the default.
        sources: {action: engine.sources.DamageSource} — actions with their
        OWN attack-power base (spells, character skill/ult, arts). Empty/None
        keeps every action on the weapon-AR path, bit-identical to before.
        fp_pool: max FP available; with FP-costed sources it pre-clamps the
        play profile to what the pool sustains (clamp_play_for_fp). None =
        constraint inert (the Mind->FP curve is not yet anchored)."""
        self.weapon_id = str(weapon_id)
        self.reinforce = reinforce
        self.weapon_status = weapon_status or {}
        self.weapon_mv = weapon_mv or {}
        self.cadence = cadence
        self.phys_subtype = phys_subtype
        self.weapon_flat = weapon_flat or {}
        self.weak_point = weak_point
        self.base_stats = dict(hero_stats)
        self.negation = {NEGATION_TYPE_TO_ENGINE[k]: v
                         for k, v in (char_defense.get("negation") or {}).items()
                         if k in NEGATION_TYPE_TO_ENGINE}
        self.targets = targets
        self.weight = weight
        self.play = play or {"melee": 1.0}
        self.sources = sources or {}
        self.don_attack_scale = don_attack_scale
        self.tables = ar_tables or attack_rating.load_tables()
        self._ar_cache = {}
        self._source_cache = {}
        self._fp_clamp_info = {}
        self._fp_pool = fp_pool
        if self.sources and fp_pool is not None:
            # FP clamp against the REAL fight length: requested-profile bare
            # offense -> actions to kill the targets -> sustainable cast share
            agg0 = aggregation.aggregate([])
            off_req = offense(self._ar(agg0), agg0, self.play, self.targets,
                              self.weapon_status, self.weapon_mv, self.cadence,
                              source_power=self._source_power(agg0),
                              phys_subtype=self.phys_subtype, weapon_flat=self.weapon_flat, weak_point=self.weak_point)
            nominal = estimate_fight_actions(off_req, self.targets)
            self.play, self._fp_clamp_info = clamp_play_for_fp(
                self.play, self.sources, fp_pool, nominal)
        # profile-blended tempo: DoT uptime math must run at the declared
        # mix's pace, not the raw weapon-class cadence (matrix finding #5)
        self.cadence = effective_cadence(self.cadence, self.play, self.sources)
        self._baseline = None
        off0, surv0 = self._axes(aggregation.aggregate([]))
        self._baseline = (off_baseline or off0, surv0)

    # ---- stat feedback (memoized on the relic stat-bonus key) ----
    def _stat_bonus_key(self, agg):
        return tuple(sorted((f, agg.get(("stat", f), 0.0))
                            for f in aggregation.STAT_ADD_FIELDS.values()))

    def _effective_stats(self, bonuses):
        stats = dict(self.base_stats)
        for field, add in bonuses:
            stats[field] = stats.get(field, 0) + add
        return stats

    def _ar(self, agg):
        """Weapon AR with relic stat bonuses folded in (memoized)."""
        bonuses = self._stat_bonus_key(agg)
        cached = self._ar_cache.get(bonuses)
        if cached is None:
            cached = attack_rating.attack_rating(
                self.weapon_id, self.reinforce, self._effective_stats(bonuses), self.tables)
            self._ar_cache[bonuses] = cached
        return cached

    def _source_power(self, agg):
        """{action: {dtype: power}} for sourced actions, stat-fed like _ar —
        a +Int relic updates weapon AR AND spell/skill bases in one pass
        (the §6.5 fixed point, second instance). {} when no sources."""
        if not self.sources:
            return {}
        bonuses = self._stat_bonus_key(agg)
        cached = self._source_cache.get(bonuses)
        if cached is None:
            stats_eff = self._effective_stats(bonuses)
            cached = {a: s.compute(stats_eff) for a, s in self.sources.items()}
            self._source_cache[bonuses] = cached
        return cached

    def _axes(self, agg):
        """(offense, survival) raw values for an aggregated state."""
        off_total = offense(self._ar(agg), agg, self.play, self.targets,
                            self.weapon_status, self.weapon_mv, self.cadence,
                            source_power=self._source_power(agg),
                            phys_subtype=self.phys_subtype, weapon_flat=self.weapon_flat, weak_point=self.weak_point)
        surv_total = 0.0
        vigor = self.base_stats.get("statVigor", 0) + agg.get(("stat", "statVigor"), 0.0)
        hp_proxy = vigor * math.exp(agg.get(("hp",), 0.0))
        for _name, _npc, max_damage, _hp, _res, _esc in self.targets:
            surv_total += hp_proxy / self._biggest_hit(agg, max_damage)
        return off_total, surv_total / max(len(self.targets), 1)

    def status_report(self, parsed_relics):
        """{status: {buildup, proc, first_hits, fight_procs}} over the targets.

        first_hits = hits to the FIRST proc; fight_procs = expected procs over
        the whole fight (the threshold escalates after each — ResistCorrectParam)."""
        agg = aggregation.aggregate(parsed_relics)
        ar = self._ar(agg)
        # same weapon-hit share as offense(): sourced actions don't carry the
        # weapon's innate buildup — keeps the DISPLAYED proc estimates in
        # agreement with what is actually scored (matrix audit finding #1)
        sp = self._source_power(agg)
        hitting_share = sum(p for a, p in self.play.items()
                            if a not in sp and self._attack_for_action(agg, ar, a))
        out = {}
        for status in statuses.PROC:
            buildup = (self.weapon_status.get(status, 0) * hitting_share
                       + agg.get(("stbuild", status), 0.0))
            if not buildup:
                continue
            procvals, firsts, fprocs = [], [], []
            for _n, npc, _md, max_hp, resists, escal in self.targets:
                resist = (resists or {}).get(status, 0)
                if not (resist and resist < 999 and max_hp):
                    continue
                procvals.append(statuses.proc_damage(status, max_hp))
                firsts.append(resist / buildup)
                direct = sum(p * damage.damage_vs_enemy(
                    self._attack_for_action(agg, ar, a), npc,
                    phys_subtype=self.phys_subtype if a not in sp else None)[0]
                    for a, p in self.play.items())
                fh = min(300.0, max(8.0, max_hp / direct)) if direct else 30.0
                thr = (escal or {}).get(status)
                fprocs.append(statuses._proc_count(fh * buildup, thr) if thr else fh * buildup / resist)
            if procvals:
                out[status] = {"buildup": buildup,
                               "proc": sum(procvals) / len(procvals),
                               "first_hits": sum(firsts) / len(firsts),
                               "fight_procs": sum(fprocs) / len(fprocs)}
        return out

    def _attack_for_action(self, agg, ar, action):
        classes = actions.classes_applying_to(action)
        base = self._source_power(agg).get(action)
        if base is None:
            if action.startswith(("sorcery_", "incant_")) \
                    or action in actions.NON_WEAPON_ACTIONS:
                base = {}   # no resolved source -> the action deals nothing
            else:
                mv = self.weapon_mv.get(action, 1.0)
                flat = self.weapon_flat.get(action) or {}
                base = {t: ar.get(t, 0.0) * mv + flat.get(t, 0.0)
                        for t in AR_TYPES if ar.get(t, 0.0) > 0 or flat.get(t, 0.0) > 0}
        return {t: p * math.exp(sum(agg.get(("atk", t, c), 0.0) for c in classes))
                for t, p in base.items() if p > 0}

    def _biggest_hit(self, agg, max_damage):
        """Largest incoming hit after negation, relic cuts and DoN scaling."""
        worst = 0.0
        for ttype, dmg in (max_damage or {}).items():
            etype = TARGET_TYPE_TO_ENGINE.get(ttype)
            if etype is None or not dmg:
                continue
            taken = dmg * self.negation.get(etype, 1.0) * self.don_attack_scale
            taken *= math.exp(-agg.get(("cut", etype), 0.0))
            # untyped ("neutral") relic cuts apply to physical sub-types too
            if etype in ("slash", "blow", "thrust"):
                taken *= math.exp(-agg.get(("cut", "phys"), 0.0))
            worst = max(worst, taken)
        return worst or 1.0

    # ---- public ----
    def score(self, parsed_relics):
        off, surv = self._axes(aggregation.aggregate(parsed_relics))
        off0, surv0 = self._baseline
        w = self.weight
        return w * (off / off0 if off0 else 0.0) + (1 - w) * (surv / surv0 if surv0 else 0.0)

    def breakdown(self, parsed_relics):
        """Human-readable summary of a build's score."""
        agg = aggregation.aggregate(parsed_relics)
        off, surv = self._axes(agg)
        off0, surv0 = self._baseline
        ar = self._ar(agg)
        primary = max(ar, key=ar.get, default="phys")
        counted, ignored = _per_key_actions(parsed_relics, primary, self.play)
        mults = {t: sum(p * math.exp(agg.get(("atk", t, "*"), 0.0)
                                     + agg.get(("atk", t, a), 0.0))
                        for a, p in self.play.items())
                 for t in AR_TYPES}
        return {
            "score": self.weight * (off / off0 if off0 else 0.0)
                     + (1 - self.weight) * (surv / surv0 if surv0 else 0.0),
            "offense": off, "offense_ratio": off / off0 if off0 else 0.0,
            "survival_ratio": surv / surv0 if surv0 else 0.0,
            "attack_multipliers": mults,
            "stat_bonuses": {f: agg.get(("stat", f), 0.0)
                             for f in aggregation.STAT_ADD_FIELDS.values()
                             if agg.get(("stat", f), 0.0)},
            "top_effects": counted[:5],
            "ignored_effects": ignored[:3],
            "status": self.status_report(parsed_relics),
            "actions_hit": {a: offense(ar, agg, {a: 1.0}, self.targets,
                                       self.weapon_status, self.weapon_mv, self.cadence,
                                       source_power=self._source_power(agg),
                                       phys_subtype=self.phys_subtype, weapon_flat=self.weapon_flat, weak_point=self.weak_point)
                            for a in self.play},
            "sources": {a: {"label": s.label, "fp_cost": s.fp_cost,
                            "confidence": s.meta.get("confidence"),
                            "guaranteed": s.meta.get("guaranteed", True),
                            "spell_factor_calibrated": constants_module.SPELL_FACTOR_CALIBRATED}
                        for a, s in self.sources.items()},
            "fp": self._fp_clamp_info,
            "fp_pool": self._fp_pool,
            "play": dict(self.play),   # EFFECTIVE profile (post FP clamp)
        }


# Fallback fight length for the FP sustain pre-clamp when no target-derived
# estimate is available. Kept for API stability; every engine call site now
# derives the REAL fight length from the targets (estimate_fight_actions) —
# a fixed 150 was melee-calibrated and over-clamped casters ~5× (a Nightlord
# fight is ~10-20 actions at real damage), crushing expensive spells and
# handing weapon rankings to cheap-spell or raw-AR candidates (user-caught
# 2026-07-17).
NOMINAL_FIGHT_HITS = 150.0


def estimate_fight_actions(per_action_offense, targets):
    """Mean fight length in ACTIONS across the targets, from real HP pools —
    the same [8, 300] band offense() uses per target. per_action_offense: the
    profile's average damage per action (bare relics, requested profile);
    if the requested profile is FP-unsustainable this is optimistic, making
    the estimate short and the clamp LENIENT — the conservative direction
    (never over-clamps a sustainable profile)."""
    if not per_action_offense or per_action_offense <= 0:
        return NOMINAL_FIGHT_HITS
    lengths = [min(300.0, max(8.0, (t[3] or 0) / per_action_offense))
               for t in targets if t[3]]
    return sum(lengths) / len(lengths) if lengths else NOMINAL_FIGHT_HITS


def effective_cadence(weapon_cadence, play, sources):
    """Play-weighted uses/second for the cross-type DPS ranking.

    Weapon-family actions keep the class cadence; sourced actions use their
    own rate_hz. Unknown rates (None — e.g. ultimate arts, uncalibrated cast
    times) are EXCLUDED and the mixture renormalizes over what is known —
    conservative, never a silent invented rate. Reduces to weapon_cadence
    exactly when sources is empty (the melee default)."""
    if not sources:
        return weapon_cadence
    weapon_weight = sum(p for a, p in play.items() if a not in sources)
    known = [(weapon_weight, weapon_cadence)] if weapon_weight > 0 else []
    known += [(play[a], s.rate_hz) for a, s in sources.items()
              if a in play and s.rate_hz]
    total_p = sum(p for p, _r in known)
    if not total_p:
        return weapon_cadence
    return sum(p * r for p, r in known) / total_p


def clamp_play_for_fp(play, sources, fp_pool, nominal_fight_hits=NOMINAL_FIGHT_HITS):
    """Cap each FP-costed action's declared weight at what fp_pool sustains
    over a nominal fight (NO passive FP regen in Nightreign — verified).
    Freed weight falls back onto MELEE (added if absent): an FP-dry caster
    swings the weapon — that is the real gameplay, not idle time. Returns
    (clamped_play, info) with info[action] = {requested, sustainable}
    ({} = nothing capped). Runs ONCE at Scorer construction — never inside
    the beam loop."""
    info = {}
    capped = dict(play)
    freed = 0.0
    for action, p in play.items():
        src = sources.get(action)
        cost = src.fp_cost if src else 0.0
        if not cost:
            continue
        max_casts = fp_pool / cost
        wanted_casts = p * nominal_fight_hits
        if wanted_casts > max_casts:
            p_max = max_casts / nominal_fight_hits
            info[action] = {"requested": round(p, 4), "sustainable": round(p_max, 4)}
            freed += p - p_max
            capped[action] = p_max
    if freed and info:
        capped["melee"] = capped.get("melee", 0.0) + freed
    return capped, info


def offense(ar, agg, play, targets, weapon_status=None, weapon_mv=None, cadence=1.0,
            source_power=None, phys_subtype=None, weapon_flat=None, weak_point=False):
    """Play-profile-weighted average damage of a weapon AR under an Agg state.

    Shared by the Scorer and the weapon re-pick of the coordinate ascent: the
    same formula ranks relic sets for a weapon and weapons for a relic set.
    Adds the expected STATUS damage per hit: (weapon buildup + relic on-hit
    buildup) / target resistance x proc damage (statuses.py, game-calibrated).
    Targets: (name, npc_row, max_damage, max_hp, status_resistance).

    source_power: optional {action: {dtype: power}} — resolved, stat-fed
    attack power for actions with their OWN base (spells, character skills,
    arts). An action absent from it keeps the weapon-AR × motion-value
    formula verbatim, so every existing call site (which passes nothing)
    remains bit-identical.
    """
    attacks = {}
    weapon_mv = weapon_mv or {}
    source_power = source_power or {}
    for action in play:
        classes = actions.classes_applying_to(action)
        base = source_power.get(action)
        if base is None:
            if action.startswith(("sorcery_", "incant_")) \
                    or action in actions.NON_WEAPON_ACTIONS:
                # no resolved source -> deals NOTHING. A cast needs a catalyst
                # carrying the spell; a pot/knife/perfume/roar is not a weapon
                # swing (matrix audit finding #3) — weapon-AR fallback here
                # scored a Ballista as a "caster" and a pot as a melee hit.
                base = {}
            else:
                mv = weapon_mv.get(action, 1.0)   # motion value of this action's hits
                flat = (weapon_flat or {}).get(action) or {}
                base = {t: ar.get(t, 0.0) * mv + flat.get(t, 0.0)
                        for t in AR_TYPES if ar.get(t, 0.0) > 0 or flat.get(t, 0.0) > 0}
        attacks[action] = {
            t: p * math.exp(sum(agg.get(("atk", t, c), 0.0) for c in classes))
            for t, p in base.items() if p > 0}
    weapon_status = weapon_status or {}
    # status buildup rides on WEAPON HITS: only the play share whose action
    # both lands damage AND swings the equipped weapon applies it. Sourced
    # actions (spells, character skill/ult) deal their own damage but do NOT
    # carry the weapon's innate buildup (matrix audit finding #1 — an 80/20
    # melee/skill profile applies katana bleed at x0.8, not x1.0).
    hitting_share = sum(p for a, p in play.items()
                        if attacks.get(a) and a not in source_power)
    total = 0.0
    for tgt in targets:
        npc, max_hp, resists, escal = tgt[1], tgt[3], tgt[4] or {}, (tgt[5] if len(tgt) > 5 else {}) or {}
        # the weapon's physical sub-type (slash/blow/thrust) applies to its
        # OWN swings only — sourced actions (spells/skills) hit neutral
        direct = sum(p * damage.damage_vs_enemy(
                        attacks[a], npc,
                        phys_subtype=phys_subtype if a not in source_power else None,
                        weak_point=weak_point)[0]
                     for a, p in play.items())
        # fight length: hits to deplete HP at the direct rate (status is
        # front-loaded, so amortizing over the whole fight is what matters)
        fight_hits = min(300.0, max(8.0, max_hp / direct)) if (max_hp and direct) else None
        t_total = direct
        for status in statuses.PROC:
            buildup = (weapon_status.get(status, 0) * hitting_share
                       + agg.get(("stbuild", status), 0.0))
            if buildup and max_hp and direct:
                t_total += statuses.expected_per_hit(
                    buildup, resists.get(status, 0), status, max_hp,
                    escal.get(status), fight_hits, cadence)
        # frost also debuffs the target: damage taken x1.15 while procced
        frost = (weapon_status.get("frost", 0) * hitting_share
                 + agg.get(("stbuild", "frost"), 0.0))
        if frost and 0 < resists.get("frost", 0) < 999:
            t_total *= statuses.FROST_DEBUFF
        total += t_total
    return total / max(len(targets), 1)


def _per_key_actions(parsed_relics, dtype, play):
    """Per-key offense contributions on `dtype`, split counted / gated-out.

    Returns two lists of (key, multiplier, action), sorted by multiplier desc.
    """
    per = {}
    for copies in parsed_relics:
        for key, stacks, contrib in copies:
            for dim, v in contrib.items():
                if len(dim) != 3 or dim[0] != "atk" or dim[1] != dtype:
                    continue
                action = dim[2]
                slot = (key, action)
                if stacks:
                    per[slot] = per.get(slot, 0.0) + v
                else:
                    per[slot] = max(per.get(slot, 0.0), v)
    covered = set()
    for declared in play:
        covered |= actions.classes_applying_to(declared)
    counted, ignored = [], []
    for (key, action), v in per.items():
        entry = (key, math.exp(v), action)
        (counted if action in covered else ignored).append(entry)
    counted.sort(key=lambda e: -e[1])
    ignored.sort(key=lambda e: -e[1])
    return counted, ignored
