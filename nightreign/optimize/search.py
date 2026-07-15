#!/usr/bin/env python3
"""Slot-filling search: beam (production) and exhaustive (verification).

Beam search keeps the top-k partial builds per slot. §5.3 of the math doc
measures why: every static-order myopic greedy drops below the optimum on some
coupled vessel (matching artifact or sigma=0 coverage overlap), while beam
k=12 reached the exhaustive optimum in every swept context. The exhaustive
enumerator stays here for regression tests, exactly as in the experiments.

A pool maps (pool_kind, color) -> pruned candidates [(relic, parsed, profile)].
Slots are (pool_kind, slot_color) pairs; a slot may stay empty when no
candidate remains (relic-less slots contribute nothing).
"""
import itertools


def candidates_for(pools, pool_kind, slot_color):
    out = []
    for (kind, color), entries in pools.items():
        if kind == pool_kind and (slot_color == "Any" or slot_color == color):
            out.extend(entries)
    return out


def beam_search(slots, pools, score_fn, k=12):
    """Fill `slots` [(pool_kind, color), ...] -> (best_score, [(slot, relic), ...])."""
    beams = [([], set())]  # (picks [(slot, relic, parsed)], used record_ids)
    for slot in slots:
        cands = candidates_for(pools, *slot)
        if not cands:
            continue
        expanded = []
        for picks, used in beams:
            base = [p[2] for p in picks]
            for relic, parsed, _prof in cands:
                rid = relic["record_id"]
                if rid in used:
                    continue
                expanded.append((score_fn(base + [parsed]),
                                 picks + [(slot, relic, parsed)],
                                 used | {rid}))
        if not expanded:
            continue
        expanded.sort(key=lambda x: -x[0])
        beams = [(picks, used) for _s, picks, used in expanded[:k]]
    best_picks, _ = max(beams, key=lambda b: score_fn([p[2] for p in b[0]]))
    return (score_fn([p[2] for p in best_picks]),
            [(slot, relic) for slot, relic, _ in best_picks])


def exhaustive_search(slots, pools, score_fn):
    """Ground-truth optimum by full enumeration (tests only — exponential)."""
    slot_cands = []
    for slot in slots:
        cands = candidates_for(pools, *slot)
        if cands:
            slot_cands.append([(slot, c) for c in cands])
    best, best_picks = score_fn([]), []
    for combo in itertools.product(*slot_cands):
        rids = [c[1][0]["record_id"] for c in combo]
        if len(set(rids)) != len(rids):
            continue
        s = score_fn([c[1][1] for c in combo])
        if s > best:
            best, best_picks = s, [(slot, c[0]) for slot, c in combo]
    return best, best_picks
