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

# nightlords.json attack / damage_multiplier naming -> engine damage types
TARGET_TYPE_TO_ENGINE = {
    "phys": "phys", "slash": "slash", "blow": "blow", "thrust": "thrust",
    "magic": "mag", "fire": "fire", "lightning": "thunder", "holy": "dark",
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
                 weapon_mv=None):
        """targets: list of (name, npc_row, attacks_max_damage_dict).
        play: normalized {action: weight} — default pure-melee benchmark.
        off_baseline: offense normalizer shared by every weapon of a type (the
        type's bare-best weapon), so S ranks ABSOLUTE damage within the type —
        normalizing each weapon by its own bare damage would crown weak-bare
        weapons on inflated ratios. None = this weapon's own bare damage.
        reinforce: weapon upgrade level, clamped per weapon (Nightreign caps
        at +3) — +0 sits in the harshest zone of the defense curve and
        distorts weapon rankings, so the endgame level is the default."""
        self.weapon_id = str(weapon_id)
        self.reinforce = reinforce
        self.weapon_status = weapon_status or {}
        self.weapon_mv = weapon_mv or {}
        self.base_stats = dict(hero_stats)
        self.negation = {NEGATION_TYPE_TO_ENGINE[k]: v
                         for k, v in (char_defense.get("negation") or {}).items()
                         if k in NEGATION_TYPE_TO_ENGINE}
        self.targets = targets
        self.weight = weight
        self.play = play or {"melee": 1.0}
        self.don_attack_scale = don_attack_scale
        self.tables = ar_tables or attack_rating.load_tables()
        self._ar_cache = {}
        self._baseline = None
        off0, surv0 = self._axes(aggregation.aggregate([]))
        self._baseline = (off_baseline or off0, surv0)

    # ---- axes ----
    def _ar(self, agg):
        """Weapon AR with relic stat bonuses folded in (memoized)."""
        bonuses = tuple(sorted((f, agg.get(("stat", f), 0.0))
                               for f in aggregation.STAT_ADD_FIELDS.values()))
        cached = self._ar_cache.get(bonuses)
        if cached is None:
            stats = dict(self.base_stats)
            for field, add in bonuses:
                stats[field] = stats.get(field, 0) + add
            cached = attack_rating.attack_rating(self.weapon_id, self.reinforce, stats, self.tables)
            self._ar_cache[bonuses] = cached
        return cached

    def _axes(self, agg):
        """(offense, survival) raw values for an aggregated state."""
        off_total = offense(self._ar(agg), agg, self.play, self.targets,
                            self.weapon_status, self.weapon_mv)
        surv_total = 0.0
        vigor = self.base_stats.get("statVigor", 0) + agg.get(("stat", "statVigor"), 0.0)
        hp_proxy = vigor * math.exp(agg.get(("hp",), 0.0))
        for _name, _npc, max_damage, _hp, _res in self.targets:
            surv_total += hp_proxy / self._biggest_hit(agg, max_damage)
        return off_total, surv_total / max(len(self.targets), 1)

    def status_report(self, parsed_relics):
        """{status: {buildup, proc, hits_per_proc}} averaged over the targets."""
        agg = aggregation.aggregate(parsed_relics)
        out = {}
        for status in statuses.PROC:
            buildup = self.weapon_status.get(status, 0) + agg.get(("stbuild", status), 0.0)
            if not buildup:
                continue
            procs, hits = [], []
            for _n, _npc, _md, max_hp, resists in self.targets:
                resist = (resists or {}).get(status, 0)
                if resist and resist < 999 and max_hp:
                    procs.append(statuses.proc_damage(status, max_hp))
                    hits.append(resist / buildup)
            if procs:
                out[status] = {"buildup": buildup,
                               "proc": sum(procs) / len(procs),
                               "hits_per_proc": sum(hits) / len(hits)}
        return out

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
                                       self.weapon_status, self.weapon_mv)
                            for a in self.play},
        }


def offense(ar, agg, play, targets, weapon_status=None, weapon_mv=None):
    """Play-profile-weighted average damage of a weapon AR under an Agg state.

    Shared by the Scorer and the weapon re-pick of the coordinate ascent: the
    same formula ranks relic sets for a weapon and weapons for a relic set.
    Adds the expected STATUS damage per hit: (weapon buildup + relic on-hit
    buildup) / target resistance x proc damage (statuses.py, game-calibrated).
    Targets: (name, npc_row, max_damage, max_hp, status_resistance).
    """
    attacks = {}
    weapon_mv = weapon_mv or {}
    for action in play:
        classes = actions.classes_applying_to(action)
        mv = weapon_mv.get(action, 1.0)   # motion value of this action's hits
        attacks[action] = {
            t: ar.get(t, 0.0) * mv
               * math.exp(sum(agg.get(("atk", t, c), 0.0) for c in classes))
            for t in AR_TYPES if ar.get(t, 0.0) > 0}
    weapon_status = weapon_status or {}
    total = 0.0
    for _name, npc, _max_damage, max_hp, resists in targets:
        t_total = sum(p * damage.damage_vs_enemy(attacks[a], npc)[0]
                      for a, p in play.items())
        for status in statuses.PROC:
            buildup = weapon_status.get(status, 0) + agg.get(("stbuild", status), 0.0)
            if buildup and max_hp:
                t_total += statuses.expected_per_hit(
                    buildup, (resists or {}).get(status, 0), status, max_hp)
        # frost also debuffs the target: damage taken x1.15 while procced
        # (30s duration >> proc cycle -> near-permanent uptime)
        frost = weapon_status.get("frost", 0) + agg.get(("stbuild", "frost"), 0.0)
        if frost and 0 < (resists or {}).get("frost", 0) < 999:
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
