#!/usr/bin/env python3
"""Context-aware dominance pruning — Theorem 2 of optimizer-math.md §3.

A relic may be dropped only if at least s_c DISTINCT relics strictly dominate
it, where s_c is the number of vessel slots accepting its color in its pool
(an "Any" slot accepts every color). The single-dominator shortcut is lossy as
soon as two slots share a color: a dominated relic can complement its dominator
through stacking (sigma=1) keys — mono-color Grails make s_c = 3 real.

Profiles are epsilon-aware: epsilon-equal profiles are ties and are always
kept (two epsilon-equal relics must not discard each other).
"""
from nightreign.optimize import aggregation


def slots_accepting(slots, color):
    """s_c: how many of these slots a relic of `color` can occupy."""
    return sum(1 for s in slots if s == "Any" or s == color)


def prune_pool(candidates, s_c, eps=1e-12):
    """Filter a same-(color, pool) candidate list [(relic, parsed, profile), ...].

    Keeps every relic that has fewer than s_c strict dominators. `profile`
    entries are the per-key dominance profiles of aggregation.profile().
    """
    if s_c <= 0:
        return []
    kept = []
    for i, (relic, parsed, prof) in enumerate(candidates):
        dominators = 0
        for j, (_r, _p, other) in enumerate(candidates):
            if j == i:
                continue
            if aggregation.dominates(other, prof, eps) and not _profiles_equal(other, prof, eps):
                dominators += 1
                if dominators >= s_c:
                    break
        if dominators < s_c:
            kept.append((relic, parsed, prof))
    return kept


def _profiles_equal(a, b, eps):
    keys = set(a) | set(b)
    return all(abs(a.get(k, 0.0) - b.get(k, 0.0)) <= eps for k in keys)
