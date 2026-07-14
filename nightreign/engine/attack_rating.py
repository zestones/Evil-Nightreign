#!/usr/bin/env python3
"""Compute a weapon's real Attack Rating (AR) from game params + character stats.

Elden Ring / Nightreign AR, per damage type (phys, mag, fire, thunder, dark):
  AR_T = AR_FACTOR * [ base_T*reinforceRate
                       + Σ_stat base_T*(correct/100*reinforceRate)*calcCorrect(stat)/100 ]

AR_FACTOR is a global multiplier on the total AR (see resources/constants.py),
calibrated and validated against in-game numbers across levels 1..15.
Data comes from data/raw/{weapons,reinforce_weapon,calc_correct_graph,attack_element_correct}.json
plus a character stat block from data/raw/hero_stats.json. Stdlib only.
"""
import json

from nightreign.resources import constants

# damage type -> (weapon base field, weapon correctType/graph field, reinforce base-rate field, element)
ELEMENTS = [
    ("phys", "attackBasePhysics", "correctType_Physics", "physicsAtkRate", "Physics"),
    ("mag", "attackBaseMagic", "correctType_Magic", "magicAtkRate", "Magic"),
    ("fire", "attackBaseFire", "correctType_Fire", "fireAtkRate", "Fire"),
    ("thunder", "attackBaseThunder", "correctType_Thunder", "thunderAtkRate", "Thunder"),
    ("dark", "attackBaseDark", "correctType_Dark", "darkAtkRate", "Dark"),
]

# scaling stat -> (hero_stats field, weapon correct field, reinforce rate field, AEC name)
STATS = [
    ("str", "statStrength", "correctStrength", "correctStrengthRate", "Strength"),
    ("dex", "statDexterity", "correctAgility", "correctAgilityRate", "Dexterity"),
    ("int", "statIntelligence", "correctMagic", "correctMagicRate", "Magic"),
    ("fai", "statFaith", "correctFaith", "correctFaithRate", "Faith"),
    ("arc", "statArcane", "correctLuck", "correctLuckRate", "Luck"),
]


def load_tables():
    def j(name):
        return json.load(open(constants.DATA_RAW / name))
    return (j("weapons.json"), j("reinforce_weapon.json"),
            j("calc_correct_graph.json"), j("attack_element_correct.json"))


def calc_correct(graph, value):
    """CalcCorrectGraph interpolation -> scaling percentage for a stat value."""
    xs = [graph[f"stageMaxVal{i}"] for i in range(5)]
    ys = [graph[f"stageMaxGrowVal{i}"] for i in range(5)]
    adj = [graph[f"adjPt_maxGrowVal{i}"] for i in range(5)]
    value = max(xs[0], min(value, xs[4]))
    for i in range(4):
        if xs[i] <= value <= xs[i + 1] and xs[i + 1] != xs[i]:
            ratio = (value - xs[i]) / (xs[i + 1] - xs[i])
            a = adj[i]
            if a > 0:
                ratio = ratio ** a
            elif a < 0:
                ratio = 1.0 - (1.0 - ratio) ** (-a)
            return ys[i] + (ys[i + 1] - ys[i]) * ratio
    return ys[4]


def attack_rating(weapon_id, level, stats, tables=None):
    """Return {damage_type: AR} for a weapon at an upgrade level and a stat block.

    stats: dict with statStrength/statDexterity/statIntelligence/statFaith/statArcane.
    """
    weapons, reinforces, graphs, aecs = tables or load_tables()
    w = weapons[str(weapon_id)]
    # reinforce row id = reinforceTypeId + level; clamp to the highest level available
    base_reinforce = w.get("reinforceTypeId") or 0
    r = {}
    for lvl in range(level, -1, -1):
        r = reinforces.get(str(base_reinforce + lvl))
        if r is not None:
            break
    r = r or {}
    aec = aecs.get(str(w.get("attackElementCorrectId") or 0), {})

    out = {}
    for dtype, base_field, graph_field, base_rate_field, elem in ELEMENTS:
        base = (w.get(base_field) or 0) * r.get(base_rate_field, 1.0)
        if base <= 0:
            continue
        graph = graphs.get(str(w.get(graph_field) or 0))
        ar = base
        if graph:
            for _skey, hero_field, wcorrect_field, rrate_field, aec_name in STATS:
                if not aec.get(f"is{aec_name}Correct_by{elem}"):
                    continue
                wcorrect = (w.get(wcorrect_field) or 0) * r.get(rrate_field, 1.0)
                if wcorrect == 0:
                    continue
                overwrite = aec.get(f"overwrite{aec_name}CorrectRate_by{elem}", -1)
                rate = (overwrite / 100.0) if overwrite is not None and overwrite >= 0 else (wcorrect / 100.0)
                softcap = calc_correct(graph, stats.get(hero_field, 0)) / 100.0
                ar += base * rate * softcap
        out[dtype] = ar * constants.AR_FACTOR
    return out
