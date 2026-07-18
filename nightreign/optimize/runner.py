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
from nightreign.engine import sources as dmg_sources
from nightreign.optimize import affixes, aggregation, motion, pruning, scoring, search
from nightreign.optimize.context import Context
from nightreign.resources import constants, kits, weapon_types

HERO_ORDER = ["Wylder", "Guardian", "Ironeye", "Duchess", "Raider",
              "Revenant", "Recluse", "Executor", "Scholar", "Undertaker"]
WEAPON_RARITIES = ("[Common]", "[Uncommon]", "[Rare]", "[Legendary]")
NORMAL_TYPES = ("Relic", "UniqueRelic")
GENERIC = "__generic__"  # weapon-agnostic mode: relics good with ANY weapon


def load_data():
    def curated(name):
        return json.load(open(constants.DATA_CURATED / name))

    def raw(name):
        return json.load(open(constants.DATA_RAW / name))

    names = {e["ID"]: e["Entries"][0]
             for e in json.load(open(constants.NAMES / "EquipParamWeapon.json"))["Entries"]
             if e.get("Entries") and e["Entries"][0]}
    icons_path = constants.DATA_CURATED / "icons.json"
    icons = json.load(open(icons_path)) if icons_path.exists() else {"weapons": {}, "relics": {}}
    eff_icons_path = constants.DATA_CURATED / "effect_icons.json"
    effect_icons = json.load(open(eff_icons_path)) if eff_icons_path.exists() else {}
    data = {
        "icons": icons, "effect_icons": effect_icons,
        "relics": curated("relics.json"), "effects": curated("effects.json"),
        "vessels": curated("vessels.json"), "characters": curated("characters.json"),
        "nightlords": curated("nightlords.json"), "scaling": curated("mode_scaling.json"),
        "affixes": curated("weapon_affixes.json"),
        "magic": curated("magic.json"),
        "accessories": curated("accessories.json"),
        "goods": curated("goods.json"),
        "weapons": raw("weapons.json"), "npc_params": raw("npc_params.json"),
        "hero_stats": raw("hero_stats.json"), "weapon_names": names,
        "custom_weapons": raw("custom_weapons.json"),
        "motion": raw("motion_values.json"), "_mv_cache": {},
        "ar_tables": attack_rating.load_tables(),
    }
    # catalyst -> spells, split GUARANTEED vs ROLLED (verified 2026-07-17 on
    # the params + player drops): a catalyst MODEL's slot-1 spell is FIXED
    # (28/28 models constant — magicTableId_1, e.g. Lusat's always Stars of
    # Ruin), but slot-2 is a RANDOM roll at drop from a pool broader than our
    # custom instances capture (a player saw Lusat's carry Full Moon / Rykard
    # / Arc, none in our instance list). So we can only reliably recommend a
    # catalyst by its GUARANTEED slot-1; slot-2 is a bonus you hunt for. Base
    # weapons (equippedSpell_R1/R2) have both slots fixed.
    catalyst = {}
    for inst in data["custom_weapons"].values():
        wid = str(inst["weapon_id"])
        e = catalyst.setdefault(wid, {"fixed": set(), "pool": set()})
        sp = inst.get("spells") or []
        if sp:
            e["fixed"].add(sp[0]["id"])          # slot-1 = guaranteed per model
            for s in sp[1:]:
                e["pool"].add(s["id"])           # slot-2 = random roll
    for wid, w in data["weapons"].items():
        # base-weapon default loadout: R1 is the guaranteed slot-1; R2 is the
        # DEFAULT slot-2 (drops re-roll it, so it's part of the pool, not fixed)
        for f, key in (("equippedSpell_R1", "fixed"), ("equippedSpell_R2", "pool")):
            sid = w.get(f)
            if sid and sid > 0:
                catalyst.setdefault(wid, {"fixed": set(), "pool": set()})[key].add(sid)
    data["catalyst_spells"] = {wid: {"fixed": sorted(e["fixed"]),
                                     "pool": sorted(e["pool"] - e["fixed"])}
                               for wid, e in catalyst.items()}
    return data


def hero_stats_row(data, character, level):
    """Character stats at a level, LINEARLY INTERPOLATED between the four
    breakpoints the params store (totalLevel 1/2/12/15).

    Verified 2026-07-17: linear stat growth reproduces the in-game Glintstone
    Pebble/Arc damage curve for Recluse across ALL 15 levels to <1 damage.
    The previous "highest breakpoint <= level" behavior scored e.g. a level-11
    caster with level-2 stats (INT frozen at 15 instead of ~42) — ~30 damage
    low. Levels at an exact breakpoint (incl. the level-15 default) return that
    row unchanged, so the default use case is untouched."""
    base = (HERO_ORDER.index(character) + 1) * 10000
    rows = sorted((data["hero_stats"][str(base + i)] for i in range(8)
                   if str(base + i) in data["hero_stats"]),
                  key=lambda r: r.get("totalLevel", 0))
    if not rows:
        raise SystemExit(f"no hero_stats rows for {character}")
    lo = rows[0]
    hi = None
    for row in rows:
        tl = row.get("totalLevel", 0)
        if tl == level:
            return row
        if tl > level:
            hi = row
            break
        lo = row
    if hi is None or hi is lo:              # at/above the last breakpoint
        return lo if level <= lo.get("totalLevel", 0) else rows[-1]
    l0, l1 = lo.get("totalLevel", 0), hi.get("totalLevel", 0)
    t = (level - l0) / (l1 - l0)
    out = dict(lo)
    for k, v in lo.items():
        w = hi.get(k)
        if isinstance(v, (int, float)) and isinstance(w, (int, float)):
            out[k] = v + (w - v) * t
    out["totalLevel"] = level
    return out


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
                        lord.get("status_resistance") or {},
                        lord.get("status_escalation") or {}))
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


def flat_profile(data, wid):
    """Cached per-weapon flat-damage profile (ranged shots' isAddBaseAtk)."""
    cache = data.setdefault("_flat_cache", {})
    prof = cache.get(wid)
    if prof is None:
        prof = motion.flat_profile(data["weapons"].get(wid) or {}, data["motion"])
        cache[wid] = prof
    return prof


def _wants_sources(play):
    """True when the profile declares any action with its own damage base —
    the signal that weapon ranking must go through offense() for EVERY
    candidate (a cast on a non-catalyst scores 0, never raw AR), or physical
    weapons win rankings they should lose under a caster profile."""
    return any(a.startswith(("sorcery_", "incant_"))
               or a in ("char_skill", "ultimate_art",
                        "throwing_pot", "throwing_knife", "perfume")
               for a in (play or {}))


def _best_spell_of(data, spell_ids, action):
    """Best-damage spell in `spell_ids` matching the declared cast action
    (exact school, or the sorcery_any/incant_any umbrella). None if no match."""
    best, best_total = None, -1.0
    for sid in spell_ids:
        m = data["magic"].get(str(sid))
        if not m or "damage" not in m:
            continue
        fits = (m["action"] == action
                or (action == "sorcery_any" and not m["incant"])
                or (action == "incant_any" and m["incant"]))
        if not fits:
            continue
        # rank by the spell's STRONGEST playable mode — the same selection
        # spell_source() makes (channel per-second > charged > normal)
        total = sum(m["damage"].values())
        channel = m.get("channel") or {}
        if channel.get("confidence") == "params" and channel.get("damage_per_s"):
            total = max(total, sum(channel["damage_per_s"].values()))
        charged = m.get("charged") or {}
        if charged.get("damage"):
            total = max(total, sum(charged["damage"].values()))
        if total > best_total:
            best, best_total = (sid, m), total
    return best


def _match_spell(data, entry, action):
    """The catalyst's spell for a declared cast action, preferring the
    GUARANTEED slot-1 spell over a slot-2 ROLL. Returns (spell_id, spell,
    guaranteed) or None — `guaranteed=False` means it needs the right slot-2
    roll at drop (the UI warns), so a caster hunts by the reliable slot-1."""
    entry = entry or {"fixed": [], "pool": []}
    hit = _best_spell_of(data, entry.get("fixed", []), action)
    if hit:
        return (*hit, True)
    hit = _best_spell_of(data, entry.get("pool", []), action)
    if hit:
        return (*hit, False)
    return None


def build_sources(data, character, play, weapon_id=None, weapon_level=0):
    """{action: DamageSource} for the play-profile actions with their OWN
    attack-power base. THE single choke point of the multi-source engine:
    returns {} for any weapon-family-only profile (melee default), which is
    what keeps every downstream call site bit-identical in that case.
    """
    out = {}
    play = play or {}
    char_row = data["characters"].get(character) or {}
    char_kit = kits.kit(character)
    # only STRIKE-paradigm skills get a hidden-weapon source; replay skills
    # (Restage) are a kit offense factor and utility skills score nothing
    if "char_skill" in play and char_row.get("skill_weapon") \
            and char_kit.get("skill_paradigm", "strike") == "strike":
        out["char_skill"] = dmg_sources.character_skill_source(char_row, data["ar_tables"])
    if "ultimate_art" in play and char_kit.get("ultimate_paradigm", "strike") == "strike":
        src = dmg_sources.ultimate_art_source(char_row, data["ar_tables"])
        if src:
            out["ultimate_art"] = src
    # throwables: the strongest resolved consumable of the declared action
    # (Goods->Bullet->AtkParam catalog; Scholar's Bagcraft tiers via kit)
    for action in play:
        if action in ("throwing_pot", "throwing_knife", "perfume") and action not in out:
            cands = [(gid, g) for gid, g in data["goods"].items()
                     if g.get("action") == action and g.get("damage")]
            if cands:
                gid, g = max(cands, key=lambda kv: sum(kv[1]["damage"].values()))
                src = dmg_sources.consumable_source(g, action, goods_id=gid)
                if src:
                    out[action] = src
    if weapon_id is not None:
        w = data["weapons"].get(str(weapon_id)) or {}
        wtype = weapon_types.weapon_type(w)
        if wtype in weapon_types.CATALYST_TYPES:
            entry = data["catalyst_spells"].get(str(weapon_id))
            for action in play:
                if not action.startswith(("sorcery_", "incant_")):
                    continue
                hit = _match_spell(data, entry, action)
                if hit:
                    sid, spell, guaranteed = hit
                    src = dmg_sources.spell_source(spell, weapon_id, weapon_level,
                                                   wtype, data["ar_tables"], spell_id=sid,
                                                   guaranteed=guaranteed)
                    if src:
                        out[action] = src
    return out


def pick_weapon(data, stats, targets, wtype=None, agg=None, play=None,
                max_level=25, character=None):
    """Best (weapon_id, level, name, type, alternatives) vs the targets.

    Candidates are the droppable instances at their spawn weaponLevel. With an
    aggregated relic state `agg` the ranking includes the build's per-type
    multipliers and stat bonuses — the coordinate-ascent step that lets an
    elemental weapon overtake a raw-AR one once the relics stack its element.
    alternatives = the runner-up weapons as (name, damage ratio).

    With `character` and a source-declaring profile, each candidate resolves
    its OWN sources (a catalyst instance ranks by ITS spells at the
    character's scaling — the pick a caster profile actually needs). The
    default (`character=None`) skips source construction entirely: the
    melee-only hot path is untouched.
    """
    agg = agg or {}
    play = play or {"melee": 1.0}
    stats_eff = dict(stats)
    for field in aggregation.STAT_ADD_FIELDS.values():
        stats_eff[field] = stats_eff.get(field, 0) + agg.get(("stat", field), 0.0)
    sourced = character is not None and _wants_sources(play)
    fp_pool = dmg_sources.max_fp(stats_eff) if sourced else None
    ranked = []
    for wid, level, name, label in weapon_candidates(data, wtype, max_level):
        ar = attack_rating.attack_rating(wid, level, stats_eff, data["ar_tables"])
        if not ar:
            continue
        cand_sources = build_sources(data, character, play, wid, level) if sourced else {}
        sp = {a: s.compute(stats_eff) for a, s in cand_sources.items()}
        w_status = data["weapons"][wid].get("status")
        mv = mv_profile(data, wid)
        cad = weapon_types.cadence(data["weapons"][wid])
        subtype = weapon_types.weapon_subtype(data["weapons"][wid])
        wflat = flat_profile(data, wid)
        off = scoring.offense(ar, agg, play, targets, w_status, mv, cad, source_power=sp,
                              phys_subtype=subtype, weapon_flat=wflat)
        # rank each candidate under the SAME clamp the Scorer will apply to
        # it: per-candidate spell FP cost, REAL fight length from the targets
        if cand_sources and fp_pool is not None:
            nominal = scoring.estimate_fight_actions(off, targets)
            cand_play, info = scoring.clamp_play_for_fp(play, cand_sources, fp_pool, nominal)
            if info:
                off = scoring.offense(ar, agg, cand_play, targets, w_status, mv, cad,
                                      source_power=sp, phys_subtype=subtype,
                                      weapon_flat=wflat)
        ranked.append((off, wid, level, name, label))
    if not ranked:
        raise SystemExit("no usable weapon candidate")
    ranked.sort(key=lambda x: -x[0])
    best = ranked[0]
    seen, alts = {best[3]}, []
    for dmg, _wid, _lvl, name, _label in ranked[1:]:
        if name not in seen:
            seen.add(name)
            alts.append((name, dmg / best[0], _wid))   # + weapon_id for its icon
        if len(alts) == 3:
            break
    return best[1], best[2], best[3], best[4], alts


def best_weapon_types(data, stats, targets, count=3, max_level=25, play=None,
                      character=None):
    """The `count` weapon types with the strongest single weapon vs the targets.

    Under a source-declaring profile EVERY candidate is evaluated through
    offense() — catalysts with their spells, non-catalysts with 0 on the cast
    share — or a raw-AR weapon wins type rankings it should lose under a
    caster profile (the comparison must be apples-to-apples).

    The shortlist ranks by DPS (per-action damage × class cadence), the SAME
    criterion the final free-exploration ranking uses — otherwise slow
    big-hit types (Ballista 0.3 atk/s) crowd the types_count slots out of
    per-hit numbers and starve the types that actually win.
    """
    play = play or {"melee": 1.0}
    sourced = character is not None and _wants_sources(play)
    fp_pool = dmg_sources.max_fp(stats) if sourced else None
    per_type = {}
    for wid, level, name, label in weapon_candidates(data, None, max_level):
        if label is None:
            continue
        ar = attack_rating.attack_rating(wid, level, stats, data["ar_tables"])
        if not ar:
            continue
        if sourced:
            cand_sources = build_sources(data, character, play, wid, level)
            sp = {a: s.compute(stats) for a, s in cand_sources.items()}
            w_status = data["weapons"][wid].get("status")
            mv = mv_profile(data, wid)
            cad = weapon_types.cadence(data["weapons"][wid])
            subtype = weapon_types.weapon_subtype(data["weapons"][wid])
            wflat = flat_profile(data, wid)
            dmg = scoring.offense(ar, {}, play, targets, w_status, mv, cad, source_power=sp,
                                  phys_subtype=subtype, weapon_flat=wflat)
            if cand_sources and fp_pool is not None:
                nominal = scoring.estimate_fight_actions(dmg, targets)
                cand_play, info = scoring.clamp_play_for_fp(play, cand_sources, fp_pool, nominal)
                if info:
                    dmg = scoring.offense(ar, {}, cand_play, targets, w_status, mv, cad,
                                          source_power=sp, phys_subtype=subtype,
                                          weapon_flat=wflat)
        else:
            dmg = sum(damage.damage_vs_enemy(ar, npc)[0] for _n, npc, _m, _hp, _res, _e in targets)
        dps = dmg * weapon_types.cadence(data["weapons"][wid])
        if dps > per_type.get(label, 0.0):
            per_type[label] = dps
    return sorted(per_type, key=per_type.get, reverse=True)[:count]


def build_pools(data, context, include_deep):
    """(pool_kind, color) -> [(relic, parsed, profile), ...] for active relics."""
    pools = {}
    for relic in data["relics"]:
        kind = "deep" if relic["type"] == "DeepRelic" else "normal"
        if kind == "deep" and not include_deep:
            continue
        if context.relic_vetoed(relic):     # player refused a curse it carries
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
        rate = sum(damage.enemy_cut_rate(npc, etype) for _n, npc, _m, _hp, _res, _e in targets) \
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
                              mv_profile(data, wid), weapon_types.cadence(data["weapons"][wid]),
                              phys_subtype=weapon_types.weapon_subtype(data["weapons"][wid]),
                              weapon_flat=flat_profile(data, wid))
        if best is None or dmg > best[0]:
            best = (dmg, wid, level, name, label)
    return None if best is None else (best[1], best[2], best[3], best[4], [])



_DTYPE_FR = {"phys": "Physique", "mag": "Magie", "fire": "Feu", "thunder": "Foudre", "dark": "Sacré"}
_STATUS_FR = {"bleed": "Saignement", "poison": "Poison", "rot": "Écarlate", "frost": "Gel"}


def affix_label(aid, affix):
    """Human label for an affix, e.g. '+12% Feu', '+31% Attaque (tous types)'."""
    m = affix.get("magnitude") or {}
    boosted = [dt for field, dt in aggregation.ATTACK_RATE_FIELDS.items() if m.get(field, 1) > 1]
    if boosted:
        pct = affix.get("display_value", 0)
        if len(boosted) >= 5:
            return f"+{pct}% Attaque (tous types)"
        return f"+{pct}% {' / '.join(_DTYPE_FR.get(dt, dt) for dt in boosted)}"
    for field, st in aggregation.STATUS_BUILDUP_FIELDS.items():
        if m.get(field, 0) > 0:
            return f"+{_STATUS_FR.get(st, st)}"
    cond = affix.get("condition") or {}
    return cond.get("label") or f"affixe {aid}"



def _optimize_generic(data, character, stats, targets, weight, don, don_scale,
                      include_deep, toggles, play, beam_k, top, max_weapon_level,
                      count_debuffs=True, refused_curses=()):
    """Weapon-agnostic: optimize the relics you EQUIP with NO weapon type, so
    only generic effects score (type-gated ones like 'Improved Greatsword' stay
    off) — the loadout is robust to whatever weapon drops. A representative
    physical weapon supplies the AR baseline (relic multipliers, the thing being
    ranked, are weapon-independent). Output: relics + the affixes to hunt."""
    context = Context(character, None, frozenset(toggles), max(don, 1), count_debuffs,
                      frozenset(refused_curses))
    pools = build_pools(data, context, include_deep)
    # weapon-agnostic mode still carries the character's OWN sources
    # (skill/ultimate) — they exist whatever weapon drops; spells don't
    # (they need a catalyst), so cast actions stay unresolved here.
    generic_sources = build_sources(data, character, play)
    fp_pool = dmg_sources.max_fp(stats)
    # reference weapon = the character's STARTING weapon ("arme de base"): a real
    # weapon you always have, so the absolute dmg/coup & dmg/s are concrete. The
    # relic MULTIPLIERS (the weapon-agnostic quantity being ranked) don't depend
    # on this choice; only the absolute numbers do.
    sw = str(data["characters"][character].get("starting_weapon"))
    w = data["weapons"].get(sw)
    ref_name = (data["weapon_names"].get(int(sw), "arme de départ").split("] ", 1)[-1]
                if w else "arme de départ")
    ref = (sw, 0, ref_name, weapon_types.weapon_type(w) if w else None)
    ref_cad = weapon_types.cadence(w) if w else 1.0
    scorer = scoring.Scorer(ref[0], stats, data["characters"][character]["defense"],
                            targets, weight, don_scale, data["ar_tables"], play=play,
                            reinforce=ref[1], weapon_status=data["weapons"][ref[0]].get("status"),
                            weapon_mv=mv_profile(data, ref[0]), cadence=ref_cad,
                            sources=generic_sources, fp_pool=fp_pool,
                            phys_subtype=weapon_types.weapon_subtype(data["weapons"].get(ref[0]) or {}),
                            weapon_flat=flat_profile(data, ref[0]),
                            weak_point="weak_point" in toggles)
    kit_factor, kit_details = kits.offense_factor(character, toggles, play)
    results = []
    for vessel in vessels_available(data, character):
        slots = [("normal", c) for c in vessel["normal_slots"]]
        if include_deep:
            slots += [("deep", c) for c in vessel["deep_slots"]]
        pruned = {}
        for (kind, color), entries in pools.items():
            vslots = vessel["normal_slots"] if kind == "normal" else vessel["deep_slots"]
            s_c = pruning.slots_accepting(vslots, color)
            if s_c:
                pruned[(kind, color)] = pruning.prune_pool(entries, s_c)
        score, picks = search.beam_search(slots, pruned, scorer.score, beam_k)
        build_parsed = [_parsed_of(pools, r) for _slot, r in picks]
        breakdown = scorer.breakdown(build_parsed)
        results.append({
            "score": score, "character": character, "weapon_type": "toute arme",
            "weapon": "Générique — n'importe quelle arme", "weapon_id": ref[0],
            "weapon_alternatives": [], "vessel": vessel["name"], "picks": picks,
            "breakdown": breakdown,
            "absolute_offense": breakdown["offense"] * kit_factor,
            "cadence": ref_cad,
            "absolute_dps": breakdown["offense"] * kit_factor * ref_cad,
            "kit": {"factor": kit_factor, "details": kit_details} if kit_details else None,
            "ref_weapon": ref[2],
            "targets": [t[0] for t in targets], "generic": True,
            "_scorer": scorer, "_parsed": build_parsed, "_context": context,
        })
    # keep the best distinct relic set
    results.sort(key=lambda r: -r["score"])
    seen, unique = set(), []
    for r in results:
        key = frozenset(relic["record_id"] for _s, relic in r["picks"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return _finalize(unique[:top], data)


def vessels_available(data, character):
    """Vessels the optimizer may search for a character. Default policy: ALL
    obtainable vessels (the "all vessels unlocked" universe), so the tool works
    for any player without decoding per-save vessel ownership. Excludes only the
    phantom "<Nightfarer>'s Chalice" rows (obtainable=False in vessels.json)."""
    return [v for v in data["vessels"].get(character, []) if v.get("obtainable")]


def optimize(character, boss=None, weapon_type=None, level=15, weight=0.5,
             don=0, toggles=(), beam_k=12, top=3, play=None, types_count=5,
             max_weapon_level=25, data=None, count_debuffs=True, refused_curses=()):
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
    vessels = vessels_available(data, character)
    fp_pool = dmg_sources.max_fp(stats)
    wants_casts = any(a.startswith(("sorcery_", "incant_")) for a in play)

    if weapon_type == GENERIC:
        return _optimize_generic(data, character, stats, targets, weight, don, don_scale,
                                 include_deep, toggles, play, beam_k, top, max_weapon_level,
                                 count_debuffs, refused_curses)

    types_to_try = [weapon_type] if weapon_type else \
        best_weapon_types(data, stats, targets, types_count, max_weapon_level,
                          play=play, character=character)
    # guardrail: a cast-declaring profile with a fixed NON-catalyst type would
    # silently fall back to weapon AR — refuse the silence, warn loudly.
    if wants_casts and weapon_type and weapon_type not in weapon_types.CATALYST_TYPES:
        print(f"WARNING: play profile declares spell casts but weapon type "
              f"'{weapon_type}' is not a catalyst (Staff/Sacred Seal) — "
              f"cast actions will deal no spell damage on this weapon.")
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
        context = Context(character, wtype, frozenset(toggles), max(don, 1), count_debuffs,
                          frozenset(refused_curses))
        pools = build_pools(data, context, include_deep)
        starts = [pick_weapon(data, stats, targets, wtype, play=play,
                              max_level=max_weapon_level, character=character)]
        # every weapon of the type shares the same offense normalizer: the
        # type's bare-best weapon (S then ranks absolute damage in-type).
        # Its sources are included so a caster type isn't normalized by its
        # (negligible) bare melee AR — and the SAME FP clamp the Scorer will
        # apply is applied here, or the offense ratio would compare a clamped
        # numerator against an unclamped baseline.
        ref_sources = build_sources(data, character, play, starts[0][0], starts[0][1])
        ref_ar = attack_rating.attack_rating(starts[0][0], starts[0][1], stats,
                                             data["ar_tables"])
        ref_sp = {a: s.compute(stats) for a, s in ref_sources.items()}
        ref_status = data["weapons"][starts[0][0]].get("status")
        ref_mv = mv_profile(data, starts[0][0])
        ref_cad = weapon_types.cadence(data["weapons"][starts[0][0]])
        ref_subtype = weapon_types.weapon_subtype(data["weapons"][starts[0][0]])
        ref_flat = flat_profile(data, starts[0][0])
        type_ref_off = scoring.offense(ref_ar, {}, play, targets, ref_status,
                                       ref_mv, ref_cad, source_power=ref_sp,
                                       phys_subtype=ref_subtype, weapon_flat=ref_flat)
        if ref_sources:
            nominal = scoring.estimate_fight_actions(type_ref_off, targets)
            ref_play, info = scoring.clamp_play_for_fp(play, ref_sources, fp_pool, nominal)
            if info:
                type_ref_off = scoring.offense(ref_ar, {}, ref_play, targets, ref_status,
                                               ref_mv, ref_cad, source_power=ref_sp,
                                               phys_subtype=ref_subtype, weapon_flat=ref_flat)
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
                                        weapon_mv=mv_profile(data, weapon_id),
                                        cadence=weapon_types.cadence(data["weapons"][weapon_id]),
                                        sources=build_sources(data, character, play,
                                                              weapon_id, weapon_level),
                                        fp_pool=fp_pool,
                                        phys_subtype=weapon_types.weapon_subtype(data["weapons"][weapon_id]),
                                        weapon_flat=flat_profile(data, weapon_id),
                                        weak_point="weak_point" in toggles)
                vessel_results = search_vessels(scorer, pools)
                # coordinate ascent: re-rank the type's weapons under the best
                # build's multipliers; a changed pick re-runs the relic search
                best_picks = max(vessel_results, key=lambda x: x[0])[2]
                best_agg = aggregation.aggregate(
                    [_parsed_of(pools, relic) for _slot, relic in best_picks])
                new_id, new_lvl, new_name, _lbl, alts = pick_weapon(
                    data, stats, targets, wtype, agg=best_agg, play=play,
                    max_level=max_weapon_level, character=character)
                if (new_id, new_lvl) == (weapon_id, weapon_level):
                    break
                weapon_id, weapon_level, weapon_name = new_id, new_lvl, new_name
            kit_factor, kit_details = kits.offense_factor(character, toggles, play)
            for score, vessel, picks in vessel_results:
                breakdown = scorer.breakdown([p for _slot, r in picks
                                              for p in [_parsed_of(pools, r)]])
                cad = scoring.effective_cadence(
                    weapon_types.cadence(data["weapons"][weapon_id]),
                    scorer.play, scorer.sources)
                build_parsed = [_parsed_of(pools, r) for _slot, r in picks]
                results.append({
                    "score": score, "character": character, "weapon_type": wlabel,
                    "weapon": weapon_name, "weapon_id": weapon_id,
                    "weapon_alternatives": alts,
                    "vessel": vessel["name"], "picks": picks,
                    "breakdown": breakdown,
                    # kit factors are context-constant: they scale the ABSOLUTE
                    # numbers (and archetype comparisons), never the relic argmax
                    "absolute_offense": breakdown["offense"] * kit_factor,
                    "cadence": cad,
                    "absolute_dps": breakdown["offense"] * kit_factor * cad,
                    "kit": {"factor": kit_factor, "details": kit_details} if kit_details else None,
                    "targets": [t[0] for t in targets],
                    "_scorer": scorer, "_parsed": build_parsed, "_context": context,
                })
    # S is the improvement over the type's own bare weapon: comparable within a
    # type, NOT across types. Fixed type: top builds by S. Free exploration:
    # the best build of EACH type, ranked by DPS = per-hit damage x class
    # cadence (weapon_types.CADENCE), so slow big-hit weapons no longer top it.
    if weapon_type:
        results.sort(key=lambda r: -r["score"])
        seen, unique = set(), []
        for r in results:  # several vessels often reach the same gameplan
            key = (r["weapon_id"],
                   frozenset(relic["record_id"] for _s, relic in r["picks"]))
            if key not in seen:
                seen.add(key)
                unique.append(r)
        return _finalize(unique[:top], data)
    champions = {}
    for r in results:
        cur = champions.get(r["weapon_type"])
        if cur is None or r["score"] > cur["score"]:
            champions[r["weapon_type"]] = r
    ranked = sorted(champions.values(), key=lambda r: -r["absolute_dps"])
    return _finalize(ranked[:top], data)



def _accessory_contrib(magnitude):
    """A talisman's SpEffect magnitude -> one pseudo-parsed-relic entry,
    through the SAME field taxonomy the relic aggregation uses — so its
    marginal value is scored by the exact engine, zero new math."""
    import math as _math
    contrib = {}
    for f, dtype in aggregation.ATTACK_RATE_FIELDS.items():
        v = magnitude.get(f)
        if isinstance(v, (int, float)) and v > 0 and v != 1:
            contrib[("atk", dtype, "*")] = _math.log(v)
    for f, dtype in aggregation.CUT_RATE_FIELDS.items():
        v = magnitude.get(f)
        if isinstance(v, (int, float)) and v > 0 and v != 1:
            contrib[("cut", dtype)] = -_math.log(v)
    v = magnitude.get(aggregation.MAX_HP_FIELD)
    if isinstance(v, (int, float)) and v > 0 and v != 1:
        contrib[("hp",)] = _math.log(v)
    for f, field in aggregation.STAT_ADD_FIELDS.items():
        v = magnitude.get(f)
        if isinstance(v, (int, float)) and v:
            contrib[("stat", field)] = float(v)
    for f, status in aggregation.STATUS_BUILDUP_FIELDS.items():
        v = magnitude.get(f)
        if isinstance(v, (int, float)) and v > 0:
            contrib[("stbuild", status)] = float(v)
    return contrib


def recommend_accessories(data, scorer, build_parsed, top_n=5):
    """Top droppable talismans by MARGINAL score gain on the final build.

    Recommendation only — the in-game accessory slot count is unverified
    (calibration checklist), so talismans are advised, not searched."""
    base = scorer.score(build_parsed)
    ranked = []
    for aid, acc in data["accessories"].items():
        if not acc.get("is_drop") or not acc.get("magnitude"):
            continue
        if acc.get("name", "").startswith("talisman "):
            continue  # unresolved name (fallback "talisman <id>") — never
            # recommend a talisman we can't even name to the player.
        if acc.get("conditional"):
            # gated buff (weapon subcategory / state / HP threshold) whose gate
            # the flat magnitude drops — crediting it as a universal multiplier
            # over-ranks it (Roar Medallion boosts only roars/breaths, Dagger
            # Talisman only crits, etc.). Excluded until the gate is modelled;
            # honest under-count beats a misleading generic "+X%".
            continue
        contrib = _accessory_contrib(acc["magnitude"])
        if not contrib:
            continue
        pseudo = [(f"accessory:{aid}", False, contrib)]
        gain = scorer.score(build_parsed + [pseudo]) - base
        if gain > 1e-9:
            ranked.append({"id": aid, "name": acc["name"],
                           "gain": round(gain / base, 4) if base else 0.0})
    ranked.sort(key=lambda a: -a["gain"])
    return ranked[:top_n]


def _stamina_info(data, scorer):
    """Stamina economy of the build's weapon: pool (48+2*END), the R1 cost,
    and how many R1 hits a full bar buys. INFO ONLY — not scored (the regen
    rate, the missing piece for a sustain constraint, isn't measured yet).
    Surfaces why heavy weapons are awkward on low-Endurance characters."""
    pool = dmg_sources.max_stamina(scorer.base_stats)
    cost = (scorer.weapon_mv or {})  # motion profile doesn't carry cost; recompute
    weapon = data["weapons"].get(str(scorer.weapon_id)) or {}
    costs = motion.stamina_costs(weapon, data["motion"])
    r1 = costs.get("melee")
    if not pool or not r1:
        return None
    return {"pool": round(pool), "r1_cost": round(r1, 1),
            "hits_per_bar": round(pool / r1, 1)}


def _finalize(results, data):
    """Attach hunt advice (talismans; affixes disabled) and drop transients."""
    for r in results:
        scorer, parsed = r.get("_scorer"), r.get("_parsed")
        r["accessory_hunt"] = (recommend_accessories(data, scorer, parsed)
                               if scorer is not None and parsed is not None else [])
        r["stamina"] = _stamina_info(data, scorer) if scorer is not None else None
        r.pop("_scorer", None); r.pop("_parsed", None); r.pop("_context", None)
        # affix hunt DISABLED: the extracted affix pool (weapon_affixes.json)
        # mixes innate weapon properties (e.g. Coded Sword's +31%) and upgrade
        # effects with real rolls, and doesn't match what players see in game
        # (verified 2026-07-16). Needs the correct player-visible affix source
        # before it can advise reliably. Kept: optimize/affixes.py + the data.
        r["affix_hunt"] = []
    return results


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
                     f"~{r.get('absolute_offense', b['offense']):.0f} dmg/hit"
                     + (f", ~{r['absolute_dps']:.0f} dmg/s" if 'absolute_dps' in r else "") + ")")
        cad = f"  [DPS = per-hit x {r['cadence']:.2f} atk/s class cadence]" if r.get("cadence") else ""
        lines.append(f"    HUNT : {r['weapon']} ({r['weapon_type']})   "
                     f"vs {', '.join(r['targets'])}{cad}")
        if r.get("weapon_alternatives"):
            lines.append("    alt  : " + "  ".join(
                f"{name} ({100 * (ratio - 1):+.1f}%)"
                for name, ratio, *_ in r["weapon_alternatives"]))
        if r.get("affix_hunt"):
            lines.append("    AFFIXES à chercher : " + "  ".join(
                f"{a['label']} (+{100*a['gain']:.1f}%)" for a in r["affix_hunt"]))
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
                         f"(1er à ~{info['first_hits']:.0f} touches, ~{info['fight_procs']:.1f} "
                         f"procs/combat — le seuil monte à chaque proc)")
        lines.append("")
    return "\n".join(lines)
