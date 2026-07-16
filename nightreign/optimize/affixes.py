#!/usr/bin/env python3
"""Rank the in-run weapon affixes to hunt for, given a finished build.

Weapons you pick up mid-run roll affixes (weapon_affixes.json — same magnitude/
condition shape as relic effects: +X% fire, +status buildup, ...). Once the
relic loadout is fixed, this ranks every affix by the extra OFFENSE it would add
to that build against the target — the "which roll to keep" advice that pairs
with the weapon-type HUNT suggestion.

An affix's value is build-dependent: +12% fire is worthless on a physical build
and strong on a fire one, so the ranking uses the real scorer (AR x multipliers
x target weakness), not the raw magnitude.
"""
import math

from nightreign.optimize import aggregation


def _affix_contrib(affix):
    """An affix's per-key offense contribution, like a relic effect (offense +
    status only — the axes the hunt advice is about)."""
    magnitude = affix.get("magnitude") or {}
    contrib = {}
    for field, dtype in aggregation.ATTACK_RATE_FIELDS.items():
        v = magnitude.get(field)
        if isinstance(v, (int, float)) and v > 1:
            contrib[("atk", dtype, "*")] = math.log(v)
    for field, status in aggregation.STATUS_BUILDUP_FIELDS.items():
        v = magnitude.get(field)
        if isinstance(v, (int, float)) and v > 0:
            contrib[("stbuild", status)] = float(v)
    return contrib


def _active(affix, context):
    """Does the affix apply in this context? (weapon-type / character gates)."""
    cond = affix.get("condition")
    if not cond:
        return True
    dim = cond.get("dimension")
    if dim == "weapon_type":
        return cond.get("label") == context.weapon_type
    if dim == "character":
        return cond.get("label") == context.character
    return cond.get("dimension") in context.toggles


def _family(affix):
    """Affix family key (damage type or status) — the thing you hunt, ignoring
    tier. +9%/+12% fire are the same family; you keep the best roll of it."""
    return tuple(sorted(_affix_contrib(affix).keys()))


def rank(scorer, build_parsed, affixes, context, label_of, top=5):
    """[(affix_id, label, gain_ratio)] — the best affix of each FAMILY, ranked by
    offense gain on the build. build_parsed = the build's parsed relic list."""
    base = scorer.score(build_parsed)
    best = {}  # family -> (gain, aid, affix)
    for aid, affix in affixes.items():
        if not _active(affix, context):
            continue
        contrib = _affix_contrib(affix)
        if not contrib:
            continue
        synthetic_relic = [(f"affix:{aid}", True, contrib)]
        gain = scorer.score(build_parsed + [synthetic_relic]) - base
        if gain <= 1e-9:
            continue
        fam = _family(affix)
        if fam not in best or gain > best[fam][0]:
            best[fam] = (gain, aid, affix)
    ranked = sorted(best.values(), key=lambda x: -x[0])[:top]
    return [(aid, label_of(aid, affix), gain / base if base else 0.0)
            for gain, aid, affix in ranked]
