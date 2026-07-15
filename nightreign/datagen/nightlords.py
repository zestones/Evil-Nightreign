#!/usr/bin/env python3
"""Build the Nightlord roster (data/curated/nightlords.json).

Each of the 8 Nightlords (resources/nightlords.NIGHTLORDS) mapped to its main-boss
combat profile: per-element damage multipliers (incl. slash/blow/thrust), status
buildup resistances, and the weak-point multiplier.
"""
import json

from nightreign.resources import constants
from nightreign.resources.nightlords import NIGHTLORDS

# Damage multipliers (>1 weakness, <1 resistance), including physical sub-types.
CUT_RATE = {"phys": "neutralDamageCutRate", "slash": "slashDamageCutRate",
            "blow": "blowDamageCutRate", "thrust": "thrustDamageCutRate",
            "magic": "magicDamageCutRate", "fire": "fireDamageCutRate",
            "lightning": "thunderDamageCutRate", "holy": "darkDamageCutRate"}

# Status buildup resistances: THRESHOLDS, so lower = more vulnerable, 999 = immune.
RESIST = {"poison": "resist_poison", "bleed": "resist_blood", "frost": "resist_freeze",
          "sleep": "resist_sleep", "madness": "resist_madness", "rot": "resist_desease",
          "curse": "resist_curse"}


def status_label(value):
    if value is None:
        return "?"
    if value >= 999:
        return "immune"
    if value <= 200:
        return "weak"
    if value <= 400:
        return "moderate"
    return "resistant"


def load_npc_names():
    entries = json.load(open(constants.NAMES / "NpcParam.json"))["Entries"]
    return {e["ID"]: e["Entries"][0] for e in entries if e.get("Entries") and e["Entries"][0]}


def profile(row, names, npc_id):
    """Combat profile for one enemy row."""
    status = {s: row.get(f) for s, f in RESIST.items() if f in row}
    return dict(
        npc_id=npc_id,
        name=names.get(npc_id, str(npc_id)),
        hp=row.get("hp"),
        damage_multiplier={t: row.get(f, 1.0) for t, f in CUT_RATE.items()},
        weak_point_multiplier=row.get("weakPartsDamageRate", 1.0),
        status_resistance=status,
        status_reading={k: status_label(v) for k, v in status.items()},
    )


_ATK_ELEMENTS = [("phys", "atkPhys"), ("mag", "atkMag"), ("fire", "atkFire"),
                 ("thunder", "atkThun"), ("dark", "atkDark")]


def _attack_index(behaviors):
    """variationId -> list of AtkParam_Npc ids it triggers (refType 1 = attack)."""
    index = {}
    for b in behaviors.values():
        if b.get("refType") == 1 and b.get("refId", -1) > 0:
            index.setdefault(b.get("variationId"), []).append(b["refId"])
    return index


def resolve_attacks(variation_id, attack_index, attacks):
    """An enemy's attack profile: peak damage per element + peak poise damage."""
    max_damage, poise, count = {}, 0, 0
    for ref_id in attack_index.get(variation_id, []):
        atk = attacks.get(str(ref_id))
        if not atk:
            continue
        count += 1
        for elem, field in _ATK_ELEMENTS:
            if atk.get(field):
                max_damage[elem] = max(max_damage.get(elem, 0), atk[field])
        poise = max(poise, atk.get("atkSuperArmor", 0) or 0)
    return {"max_damage": max_damage, "poise": poise, "attack_count": count}


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    npc = json.load(open(constants.DATA_RAW / "npc_params.json"))
    names = load_npc_names()
    behaviors = json.load(open(constants.DATA_RAW / "behavior.json"))
    attacks = json.load(open(constants.DATA_RAW / "atk_npc.json"))
    attack_index = _attack_index(behaviors)

    roster = {}
    for nightlord, npc_id in NIGHTLORDS.items():
        row = npc.get(str(npc_id))
        if not row:
            print(f"  nightlords: WARNING {nightlord} (npc {npc_id}) missing")
            continue
        entry = profile(row, names, npc_id)
        entry["attacks"] = resolve_attacks(row.get("behaviorVariationId"), attack_index, attacks)
        roster[nightlord] = entry

    json.dump(roster, open(constants.DATA_CURATED / "nightlords.json", "w"),
              ensure_ascii=False, indent=1)
    print(f"  nightlords: wrote {len(roster)} bosses")
