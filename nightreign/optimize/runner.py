#!/usr/bin/env python3
"""End-to-end optimization: the engine loop of optimizer.md.

    for each weapon type (fixed by the user, or the best few by base damage)
        activate the conditional effects (weapon + toggles)
        prune dominated relics (s_c-aware, per vessel)
        beam-search the vessel slots to maximize S
    -> the best gameplans

Only vessels the save actually owns are searched (`owned` in vessels.json).
Deep slots join the search when a Deep-of-Night level is set (deep relics only
apply there). Weapon choice = best real damage vs the target among owned-type
candidates at the character's stats — that pick is also the HUNT advice.
"""
import json

from nightreign.engine import attack_rating, damage
from nightreign.optimize import aggregation, pruning, scoring, search
from nightreign.optimize.context import Context
from nightreign.resources import constants, weapon_types

HERO_ORDER = ["Wylder", "Guardian", "Ironeye", "Duchess", "Raider",
              "Revenant", "Recluse", "Executor", "Scholar", "Undertaker"]
WEAPON_RARITIES = ("[Common]", "[Uncommon]", "[Rare]", "[Legendary]")
NORMAL_TYPES = ("Relic", "UniqueRelic")


def load_data():
    def curated(name):
        return json.load(open(constants.DATA_CURATED / name))

    def raw(name):
        return json.load(open(constants.DATA_RAW / name))

    names = {e["ID"]: e["Entries"][0]
             for e in json.load(open(constants.NAMES / "EquipParamWeapon.json"))["Entries"]
             if e.get("Entries") and e["Entries"][0]}
    return {
        "relics": curated("relics.json"), "effects": curated("effects.json"),
        "vessels": curated("vessels.json"), "characters": curated("characters.json"),
        "nightlords": curated("nightlords.json"), "scaling": curated("mode_scaling.json"),
        "weapons": raw("weapons.json"), "npc_params": raw("npc_params.json"),
        "hero_stats": raw("hero_stats.json"), "weapon_names": names,
        "ar_tables": attack_rating.load_tables(),
    }


def hero_stats_row(data, character, level):
    """Highest hero_stats row with totalLevel <= level (rows exist at 1/2/12/15)."""
    base = (HERO_ORDER.index(character) + 1) * 10000
    rows = [data["hero_stats"][str(base + i)] for i in range(8)
            if str(base + i) in data["hero_stats"]]
    eligible = [r for r in rows if r.get("totalLevel", 0) <= level] or rows[:1]
    return max(eligible, key=lambda r: r.get("totalLevel", 0))


def resolve_targets(data, boss):
    """[(name, npc_row, max_damage)] — one Nightlord, or all of them (generalist)."""
    lords = data["nightlords"]
    picked = ([b for b in lords if b.lower() == boss.lower()] if boss else list(lords))
    if boss and not picked:
        raise SystemExit(f"unknown boss '{boss}' — expected one of: {', '.join(lords)}")
    out = []
    for name in picked:
        row = data["npc_params"].get(str(lords[name]["npc_id"]))
        if row:
            out.append((name, row, (lords[name].get("attacks") or {}).get("max_damage") or {}))
    return out


def weapon_candidates(data, wtype=None):
    """(weapon_id, display_name, type_label) for every real, named weapon."""
    out = []
    for wid, w in data["weapons"].items():
        name = data["weapon_names"].get(int(wid))
        if not name or not name.startswith(WEAPON_RARITIES):
            continue
        label = weapon_types.weapon_type(w)
        if wtype and label != wtype:
            continue
        out.append((wid, name.split("] ", 1)[1], label))
    return out


def pick_weapon(data, stats, targets, wtype=None, agg=None, play=None):
    """Best (weapon_id, name, type, alternatives) vs the targets.

    With an aggregated relic state `agg` the ranking includes the build's
    per-type multipliers and stat bonuses — the coordinate-ascent step that
    lets an elemental weapon overtake a raw-AR one once the relics stack its
    element. alternatives = the runner-up weapons as (name, damage ratio).
    """
    agg = agg or {}
    play = play or {"melee": 1.0}
    stats_eff = dict(stats)
    for field in aggregation.STAT_ADD_FIELDS.values():
        stats_eff[field] = stats_eff.get(field, 0) + agg.get(("stat", field), 0.0)
    ranked = []
    for wid, name, label in weapon_candidates(data, wtype):
        ar = attack_rating.attack_rating(wid, 0, stats_eff, data["ar_tables"])
        if not ar:
            continue
        ranked.append((scoring.offense(ar, agg, play, targets), wid, name, label))
    if not ranked:
        raise SystemExit("no usable weapon candidate")
    ranked.sort(key=lambda x: -x[0])
    best = ranked[0]
    seen, alts = {best[2]}, []
    for dmg, _wid, name, _label in ranked[1:]:
        if name not in seen:
            seen.add(name)
            alts.append((name, dmg / best[0]))
        if len(alts) == 3:
            break
    return best[1], best[2], best[3], alts


def best_weapon_types(data, stats, targets, count=3):
    """The `count` weapon types with the strongest single weapon vs the targets."""
    per_type = {}
    for wid, name, label in weapon_candidates(data):
        if label is None:
            continue
        ar = attack_rating.attack_rating(wid, 0, stats, data["ar_tables"])
        if not ar:
            continue
        dmg = sum(damage.damage_vs_enemy(ar, npc)[0] for _n, npc, _m in targets)
        if dmg > per_type.get(label, 0.0):
            per_type[label] = dmg
    return sorted(per_type, key=per_type.get, reverse=True)[:count]


def build_pools(data, context, include_deep):
    """(pool_kind, color) -> [(relic, parsed, profile), ...] for active relics."""
    pools = {}
    for relic in data["relics"]:
        kind = "deep" if relic["type"] == "DeepRelic" else "normal"
        if kind == "deep" and not include_deep:
            continue
        parsed = aggregation.parse_relic(relic, data["effects"], context)
        if not parsed:
            continue
        pools.setdefault((kind, relic["color"]), []).append(
            (relic, parsed, aggregation.profile(parsed)))
    return pools


def optimize(character, boss=None, weapon_type=None, level=15, weight=0.5,
             don=0, toggles=(), beam_k=12, top=3, play=None, types_count=5,
             data=None):
    """Run the full engine loop; returns the `top` best gameplans (dicts).

    play: normalized {action: weight} play profile (resources/actions.py);
    None = the pure-melee benchmark. Per weapon type the weapon choice and the
    relic search run in coordinate ascent: search relics for the bare-best
    weapon, re-rank every weapon of the type under the found build's
    multipliers, and repeat once if the pick changed.
    """
    data = data or load_data()
    play = play or {"melee": 1.0}
    character = next((h for h in HERO_ORDER if h.lower() == character.lower()), None)
    if character is None:
        raise SystemExit(f"unknown character — expected one of: {', '.join(HERO_ORDER)}")
    stats = hero_stats_row(data, character, level)
    targets = resolve_targets(data, boss)
    include_deep = don >= 1
    don_scale = (data["scaling"]["deep_of_night"].get(str(don), {}).get("attack", 1.0)
                 if include_deep else 1.0)
    vessels = [v for v in data["vessels"].get(character, []) if v.get("owned")]
    types_to_try = [weapon_type] if weapon_type else \
        best_weapon_types(data, stats, targets, types_count)
    # Offense normalizer. Exploring several types: the best BARE weapon overall,
    # so S ranks absolute damage across types. Type fixed by the user: that
    # type's own bare baseline — they asked for the best gameplan of THIS
    # style, not a verdict on the style's single-hit strength.
    ref_off = None
    if not weapon_type:
        ref_id, _rn, _rl, _ra = pick_weapon(data, stats, targets, play=play)
        ref_off = scoring.offense(
            attack_rating.attack_rating(ref_id, 0, stats, data["ar_tables"]),
            {}, play, targets)

    def search_vessels(scorer, pools):
        out = []
        for vessel in vessels:
            slots = [("normal", c) for c in vessel["normal_slots"]]
            if include_deep:
                slots += [("deep", c) for c in vessel["deep_slots"]]
            pruned = {}
            for (kind, color), entries in pools.items():
                vessel_slots = vessel["normal_slots"] if kind == "normal" else vessel["deep_slots"]
                s_c = pruning.slots_accepting(vessel_slots, color)
                if s_c:
                    pruned[(kind, color)] = pruning.prune_pool(entries, s_c)
            score, picks = search.beam_search(slots, pruned, scorer.score, beam_k)
            out.append((score, vessel, picks))
        return out

    results = []
    for wtype in types_to_try:
        context = Context(character, wtype, frozenset(toggles), max(don, 1))
        pools = build_pools(data, context, include_deep)
        weapon_id, weapon_name, wlabel, alts = pick_weapon(data, stats, targets, wtype,
                                                           play=play)
        vessel_results = []
        for _ascent_pass in range(2):
            scorer = scoring.Scorer(weapon_id, stats,
                                    data["characters"][character]["defense"],
                                    targets, weight, don_scale, data["ar_tables"],
                                    play=play, off_baseline=ref_off)
            vessel_results = search_vessels(scorer, pools)
            # coordinate ascent: re-rank the type's weapons under the best
            # build's multipliers; a changed pick re-runs the relic search
            best_picks = max(vessel_results, key=lambda x: x[0])[2]
            best_agg = aggregation.aggregate(
                [_parsed_of(pools, relic) for _slot, relic in best_picks])
            new_id, new_name, _lbl, alts = pick_weapon(data, stats, targets, wtype,
                                                       agg=best_agg, play=play)
            if new_id == weapon_id:
                break
            weapon_id, weapon_name = new_id, new_name
        for score, vessel, picks in vessel_results:
            results.append({
                "score": score, "character": character, "weapon_type": wlabel,
                "weapon": weapon_name, "weapon_id": weapon_id,
                "weapon_alternatives": alts,
                "vessel": vessel["name"], "picks": picks,
                "breakdown": scorer.breakdown([p for _slot, r in picks
                                               for p in [_parsed_of(pools, r)]]),
                "targets": [t[0] for t in targets],
            })
    results.sort(key=lambda r: -r["score"])
    # several vessels often reach the same relic set — keep the first of each
    seen, unique = set(), []
    for r in results:
        key = frozenset(relic["record_id"] for _s, relic in r["picks"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique[:top]


def _parsed_of(pools, relic):
    for entries in pools.values():
        for r, parsed, _prof in entries:
            if r["record_id"] == relic["record_id"]:
                return parsed
    return []


def pretty_name(camel):
    out = []
    for ch in camel:
        if ch.isupper() and out and not out[-1].isspace():
            out.append(" ")
        out.append(ch)
    return "".join(out).title()


def format_report(results, weight):
    lines = []
    for i, r in enumerate(results, 1):
        b = r["breakdown"]
        lines.append(f"#{i}  S={r['score']:.4f}  (offense x{b['offense_ratio']:.3f}, "
                     f"survival x{b['survival_ratio']:.3f}, w={weight})")
        lines.append(f"    HUNT : {r['weapon']} ({r['weapon_type']})   "
                     f"vs {', '.join(r['targets'])}   [biggest single hit — "
                     f"attack speed/DPS not modeled yet; fix a type with --weapon-type]")
        if r.get("weapon_alternatives"):
            lines.append("    alt  : " + "  ".join(
                f"{name} ({100 * (ratio - 1):+.1f}%)"
                for name, ratio in r["weapon_alternatives"]))
        lines.append(f"    EQUIP: {r['vessel']}")
        for (kind, color), relic in r["picks"]:
            grid = relic.get("grid_by_color") or relic.get("grid") or ["?", "?"]
            lines.append(f"      [{kind:6}|{color:6}] {pretty_name(relic['name']):34} "
                         f"(grille {color.lower()} l{grid[0] + 1} c{grid[1] + 1})")
        mults = {t: m for t, m in b["attack_multipliers"].items() if m > 1.0}
        if mults:
            lines.append("    STACK: " + "  ".join(f"{t} x{m:.3f}" for t, m in mults.items()))
        if b["stat_bonuses"]:
            lines.append("    STATS: " + "  ".join(f"{f.replace('stat', '')} +{v:.0f}"
                                                   for f, v in b["stat_bonuses"].items()))
        if b.get("top_effects"):
            lines.append("    PLAY : counted — " + "  ".join(
                f"{pretty_name(k)} (x{m:.2f}{'' if a == '*' else ', ' + a})"
                for k, m, a in b["top_effects"]))
        if b.get("ignored_effects"):
            lines.append("    NOTE : gated out by your play profile — " + "  ".join(
                f"{pretty_name(k)} (x{m:.2f}, {a})" for k, m, a in b["ignored_effects"]))
        lines.append("")
    return "\n".join(lines)
