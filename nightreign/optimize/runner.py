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
from nightreign.optimize import aggregation, motion, pruning, scoring, search
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
        "custom_weapons": raw("custom_weapons.json"),
        "motion": raw("motion_values.json"), "_mv_cache": {},
        "ar_tables": attack_rating.load_tables(),
    }


def hero_stats_row(data, character, level):
    """Highest hero_stats row with totalLevel <= level (rows exist at 1/2/12/15)."""
    base = (HERO_ORDER.index(character) + 1) * 10000
    rows = [data["hero_stats"][str(base + i)] for i in range(8)
            if str(base + i) in data["hero_stats"]]
    eligible = [r for r in rows if r.get("totalLevel", 0) <= level] or rows[:1]
    return max(eligible, key=lambda r: r.get("totalLevel", 0))


def resolve_targets(data, boss, hp_scale=1.0):
    """[(name, npc_row, max_damage, max_hp, status_resistance)] — one
    Nightlord, or all of them (generalist). max_hp carries the Deep-of-Night
    HP scaling so status procs (% of max HP) stay honest."""
    lords = data["nightlords"]
    picked = ([b for b in lords if b.lower() == boss.lower()] if boss else list(lords))
    if boss and not picked:
        raise SystemExit(f"unknown boss '{boss}' — expected one of: {', '.join(lords)}")
    out = []
    for name in picked:
        lord = lords[name]
        row = data["npc_params"].get(str(lord["npc_id"]))
        if row:
            out.append((name, row, (lord.get("attacks") or {}).get("max_damage") or {},
                        (lord.get("hp") or 0) * hp_scale,
                        lord.get("status_resistance") or {}))
    return out


def weapon_candidates(data, wtype=None, max_level=25):
    """(weapon_id, level, display_name, type_label) for every DROPPABLE weapon.

    The pool is EquipParamCustomWeapon — the instances that actually spawn in
    a run, at their spawn weaponLevel — not the full EquipParamWeapon table
    (which holds engine-only variants no player can find). Hero starting
    weapons are excluded: they are a given, not a HUNT target."""
    best_level = {}
    for inst in data["custom_weapons"].values():
        wid, level = str(inst["weapon_id"]), inst.get("level") or 0
        if level > max_level or inst.get("is_cursed"):
            continue
        # weaponLevel 25 marks the renamed elemental variants ("Sacred
        # Dagger", ...) — absent from the in-game weapon list (player-checked
        # 2026-07-15), so they stay out until a decoded loot table proves they
        # drop. Their semantics are under investigation (ItemLotParam def
        # needed; byte-level scans give false positives).
        if level == 25:
            continue
        # every weapon is wieldable at character level 15: keep each weapon's
        # strongest droppable instance (weaponLevel clamps into the reinforce
        # ladder; its exact scaling semantics are still under investigation)
        best_level[wid] = max(best_level.get(wid, 0), level)
    out = []
    for wid, level in best_level.items():
        w = data["weapons"].get(wid)
        name = data["weapon_names"].get(int(wid)) if w else None
        if not w or not name or not name.startswith(WEAPON_RARITIES):
            continue
        label = weapon_types.weapon_type(w)
        if wtype and label != wtype:
            continue
        out.append((wid, level, name.split("] ", 1)[1], label))
    return out


def mv_profile(data, wid):
    """Cached per-weapon motion-value profile (optimize/motion.py)."""
    prof = data["_mv_cache"].get(wid)
    if prof is None:
        prof = motion.profile(data["weapons"].get(wid) or {}, data["motion"])
        data["_mv_cache"][wid] = prof
    return prof


def pick_weapon(data, stats, targets, wtype=None, agg=None, play=None,
                max_level=25):
    """Best (weapon_id, level, name, type, alternatives) vs the targets.

    Candidates are the droppable instances at their spawn weaponLevel. With an
    aggregated relic state `agg` the ranking includes the build's per-type
    multipliers and stat bonuses — the coordinate-ascent step that lets an
    elemental weapon overtake a raw-AR one once the relics stack its element.
    alternatives = the runner-up weapons as (name, damage ratio).
    """
    agg = agg or {}
    play = play or {"melee": 1.0}
    stats_eff = dict(stats)
    for field in aggregation.STAT_ADD_FIELDS.values():
        stats_eff[field] = stats_eff.get(field, 0) + agg.get(("stat", field), 0.0)
    ranked = []
    for wid, level, name, label in weapon_candidates(data, wtype, max_level):
        ar = attack_rating.attack_rating(wid, level, stats_eff, data["ar_tables"])
        if not ar:
            continue
        ranked.append((scoring.offense(ar, agg, play, targets,
                                       data["weapons"][wid].get("status"),
                                       mv_profile(data, wid)),
                       wid, level, name, label))
    if not ranked:
        raise SystemExit("no usable weapon candidate")
    ranked.sort(key=lambda x: -x[0])
    best = ranked[0]
    seen, alts = {best[3]}, []
    for dmg, _wid, _lvl, name, _label in ranked[1:]:
        if name not in seen:
            seen.add(name)
            alts.append((name, dmg / best[0]))
        if len(alts) == 3:
            break
    return best[1], best[2], best[3], best[4], alts


def best_weapon_types(data, stats, targets, count=3, max_level=25):
    """The `count` weapon types with the strongest single weapon vs the targets."""
    per_type = {}
    for wid, level, name, label in weapon_candidates(data, None, max_level):
        if label is None:
            continue
        ar = attack_rating.attack_rating(wid, level, stats, data["ar_tables"])
        if not ar:
            continue
        dmg = sum(damage.damage_vs_enemy(ar, npc)[0] for _n, npc, _m, _hp, _res in targets)
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


def weak_element(targets):
    """The engine damage type the targets take the most extra damage from
    (None when nothing beats neutral by 5%+)."""
    best, best_rate = None, 1.05
    for etype in ("mag", "fire", "thunder", "dark"):
        rate = sum(damage.enemy_cut_rate(npc, etype) for _n, npc, _m, _hp, _res in targets) \
               / max(len(targets), 1)
        if rate > best_rate:
            best, best_rate = etype, rate
    return best


def pick_weapon_elemental(data, stats, targets, wtype, element, play, max_level=25):
    """Best droppable weapon of the type leaning on `element` (>= 30% of AR).

    Second start of the coordinate ascent: the phys-heavy basin never explores
    elemental weapons on its own, because relics adapt to the starting weapon.
    """
    best = None
    for wid, level, name, label in weapon_candidates(data, wtype, max_level):
        ar = attack_rating.attack_rating(wid, level, stats, data["ar_tables"])
        total = sum(ar.values())
        if not total or ar.get(element, 0.0) < 0.3 * total:
            continue
        dmg = scoring.offense(ar, {}, play, targets, data["weapons"][wid].get("status"),
                              mv_profile(data, wid))
        if best is None or dmg > best[0]:
            best = (dmg, wid, level, name, label)
    return None if best is None else (best[1], best[2], best[3], best[4], [])


def optimize(character, boss=None, weapon_type=None, level=15, weight=0.5,
             don=0, toggles=(), beam_k=12, top=3, play=None, types_count=5,
             max_weapon_level=25, data=None):
    """Run the full engine loop; returns the `top` best gameplans (dicts).

    play: normalized {action: weight} play profile (resources/actions.py);
    None = the pure-melee benchmark. Per weapon type the weapon choice and the
    relic search run in coordinate ascent — from the bare-best weapon AND,
    when the target has an elemental weakness, from the best weapon leaning on
    that element (two basins: relics adapt to the weapon, so a single start
    can lock into physical). max_weapon_level caps the droppable instances
    considered (in-run progression: weapons unlock by level during a run).
    """
    data = data or load_data()
    play = play or {"melee": 1.0}
    character = next((h for h in HERO_ORDER if h.lower() == character.lower()), None)
    if character is None:
        raise SystemExit(f"unknown character — expected one of: {', '.join(HERO_ORDER)}")
    stats = hero_stats_row(data, character, level)
    include_deep = don >= 1
    don_row = data["scaling"]["deep_of_night"].get(str(don), {}) if include_deep else {}
    don_scale = don_row.get("attack", 1.0)
    targets = resolve_targets(data, boss, don_row.get("hp", 1.0))
    vessels = [v for v in data["vessels"].get(character, []) if v.get("owned")]
    types_to_try = [weapon_type] if weapon_type else \
        best_weapon_types(data, stats, targets, types_count, max_weapon_level)
    elem = weak_element(targets)

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
        starts = [pick_weapon(data, stats, targets, wtype, play=play,
                              max_level=max_weapon_level)]
        # every weapon of the type shares the same offense normalizer: the
        # type's bare-best weapon (S then ranks absolute damage in-type)
        type_ref_off = scoring.offense(
            attack_rating.attack_rating(starts[0][0], starts[0][1], stats,
                                        data["ar_tables"]), {}, play, targets,
            data["weapons"][starts[0][0]].get("status"),
            mv_profile(data, starts[0][0]))
        if elem:
            alt_start = pick_weapon_elemental(data, stats, targets, wtype, elem,
                                              play, max_weapon_level)
            if alt_start and alt_start[0] != starts[0][0]:
                starts.append(alt_start)
        for weapon_id, weapon_level, weapon_name, wlabel, alts in starts:
            vessel_results = []
            for _ascent_pass in range(2):
                scorer = scoring.Scorer(weapon_id, stats,
                                        data["characters"][character]["defense"],
                                        targets, weight, don_scale, data["ar_tables"],
                                        play=play, reinforce=weapon_level,
                                        off_baseline=type_ref_off,
                                        weapon_status=data["weapons"][weapon_id].get("status"),
                                        weapon_mv=mv_profile(data, weapon_id))
                vessel_results = search_vessels(scorer, pools)
                # coordinate ascent: re-rank the type's weapons under the best
                # build's multipliers; a changed pick re-runs the relic search
                best_picks = max(vessel_results, key=lambda x: x[0])[2]
                best_agg = aggregation.aggregate(
                    [_parsed_of(pools, relic) for _slot, relic in best_picks])
                new_id, new_lvl, new_name, _lbl, alts = pick_weapon(
                    data, stats, targets, wtype, agg=best_agg, play=play,
                    max_level=max_weapon_level)
                if (new_id, new_lvl) == (weapon_id, weapon_level):
                    break
                weapon_id, weapon_level, weapon_name = new_id, new_lvl, new_name
            for score, vessel, picks in vessel_results:
                breakdown = scorer.breakdown([p for _slot, r in picks
                                              for p in [_parsed_of(pools, r)]])
                results.append({
                    "score": score, "character": character, "weapon_type": wlabel,
                    "weapon": weapon_name, "weapon_id": weapon_id,
                    "weapon_alternatives": alts,
                    "vessel": vessel["name"], "picks": picks,
                    "breakdown": breakdown,
                    "absolute_offense": breakdown["offense"],
                    "targets": [t[0] for t in targets],
                })
    # S is the improvement over the type's own bare weapon: comparable within a
    # type, NOT across types. Fixed type: top builds by S. Free exploration:
    # the best build of EACH type, ordered by absolute per-hit damage (stated
    # as such — attack speed is not modeled, so this is a single-hit index).
    if weapon_type:
        results.sort(key=lambda r: -r["score"])
        seen, unique = set(), []
        for r in results:  # several vessels often reach the same gameplan
            key = (r["weapon_id"],
                   frozenset(relic["record_id"] for _s, relic in r["picks"]))
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return unique[:top]
    champions = {}
    for r in results:
        cur = champions.get(r["weapon_type"])
        if cur is None or r["score"] > cur["score"]:
            champions[r["weapon_type"]] = r
    ranked = sorted(champions.values(), key=lambda r: -r["absolute_offense"])
    return ranked[:top]


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


STATUS_FR = {"bleed": "saignement", "poison": "poison", "rot": "écarlate",
             "frost": "gel"}


def format_report(results, weight):
    lines = []
    for i, r in enumerate(results, 1):
        b = r["breakdown"]
        lines.append(f"#{i}  S={r['score']:.4f}  (offense x{b['offense_ratio']:.3f}, "
                     f"survival x{b['survival_ratio']:.3f}, w={weight}, "
                     f"~{r.get('absolute_offense', b['offense']):.0f} dmg/hit)")
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
        acts = b.get("actions_hit") or {}
        if len(acts) > 1 or "skill" in acts:
            lines.append("    ACTIONS: " + "  ".join(
                f"{a} ~{v:.0f}/coup" for a, v in acts.items()))
        for st, info in (b.get("status") or {}).items():
            lines.append(f"    STATUT: {STATUS_FR.get(st, st)} — proc ~{info['proc']:.0f} "
                         f"toutes les ~{info['hits_per_proc']:.1f} touches "
                         f"(buildup {info['buildup']:.0f}/coup)")
        lines.append("")
    return "\n".join(lines)
