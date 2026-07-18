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


def _reinforce_row(w, reinforces, level):
    """Reinforce row for a weapon at a level, clamped to the highest available."""
    base_reinforce = w.get("reinforceTypeId") or 0
    for lvl in range(level, -1, -1):
        r = reinforces.get(str(base_reinforce + lvl))
        if r is not None:
            return r
    return {}


def _scaling_factor(w, r, aec, graphs, stats, element_row):
    """1 + Σ_stat (correction rate × soft-capped stat curve) for one element.

    The multiplicative stat-scaling term shared by weapon AR (where it
    multiplies the weapon's own base) and spell attack (where it multiplies
    the SPELL's flat base, with the CATALYST providing w/r/aec — the
    community-established catalyst "Sorcery/Incantation Scaling" shape).
    """
    _dtype, _base_field, graph_field, _base_rate_field, elem = element_row
    graph = graphs.get(str(w.get(graph_field) or 0))
    factor = 1.0
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
            factor += rate * softcap
    return factor


def attack_rating(weapon_id, level, stats, tables=None):
    """Return {damage_type: AR} for a weapon at an upgrade level and a stat block.

    stats: dict with statStrength/statDexterity/statIntelligence/statFaith/statArcane.
    """
    weapons, reinforces, graphs, aecs = tables or load_tables()
    w = weapons[str(weapon_id)]
    r = _reinforce_row(w, reinforces, level)
    aec = aecs.get(str(w.get("attackElementCorrectId") or 0), {})

    out = {}
    for element_row in ELEMENTS:
        dtype, base_field, _graph_field, base_rate_field, _elem = element_row
        base = (w.get(base_field) or 0) * r.get(base_rate_field, 1.0)
        if base <= 0:
            continue
        ar = base * _scaling_factor(w, r, aec, graphs, stats, element_row)
        out[dtype] = ar * constants.AR_FACTOR
    return out


# Catalyst spell-scaling element per catalyst family: a staff's "Sorcery
# Scaling" derives from its Magic-element corrections, a seal's "Incantation
# Scaling" from its Dark(Holy)-element corrections — the single displayed
# scaling that multiplies EVERY damage type of the cast spell (base ER
# community formula; SPELL_FACTOR calibration pending, see ground_truth).
_SPELL_SCALING_ELEMENT = {"Sacred Seal": "dark"}
_DEFAULT_SPELL_ELEMENT = "mag"


def spell_attack(spell_damage, catalyst_id, level, stats, tables=None,
                 catalyst_type=None):
    """Per-type attack of a spell cast through a catalyst.

    spell_damage: the spell's flat AtkParam base per type (data/curated/
    magic.json "damage"). The catalyst contributes ONLY its scaling factor:
    attack[t] = spell_base[t] × scaling(catalyst element corrections, stats)
    × SPELL_FACTOR. SPELL_FACTOR is provisionally AR_FACTOR — flagged "to
    calibrate" (ROADMAP phase E) until the single-session measurements land.
    """
    weapons, reinforces, graphs, aecs = tables or load_tables()
    w = weapons[str(catalyst_id)]
    r = _reinforce_row(w, reinforces, level)
    aec = aecs.get(str(w.get("attackElementCorrectId") or 0), {})
    scaling_elem = _SPELL_SCALING_ELEMENT.get(catalyst_type, _DEFAULT_SPELL_ELEMENT)
    element_row = next(e for e in ELEMENTS if e[0] == scaling_elem)
    factor = _scaling_factor(w, r, aec, graphs, stats, element_row)
    # correctSpellScalingRate: the PER-CATALYST spell-power multiplier carried
    # by the reinforce ladder row — THE driver of the displayed Sorcery/Incant
    # Scaling differences between catalysts. Ground-truthed 2026-07-17 on
    # three user readings (Recluse 135 / Prince of Death 211 / Lusat's 223 at
    # identical correctMagic=100): rates 0.85 / 1.3248 / 1.4016 reproduce the
    # displayed ratios to the third decimal. The residual absolute constant
    # stays under SPELL_FACTOR (calibration pending, Pebble measure).
    factor *= r.get("correctSpellScalingRate", 1.0)
    factor *= constants.SPELL_SCALING_CORRECTION
    return {t: base * factor * constants.SPELL_FACTOR
            for t, base in spell_damage.items() if base > 0}
