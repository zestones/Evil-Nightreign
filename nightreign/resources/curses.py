#!/usr/bin/env python3
"""Deep of Night relic curses (debuffs) — explicit scoring/gating spec.

Curses live in the relic save record's SECOND effect array (offsets 56/60/64),
paired positionally to the buffs at 16/20/24 (buff@16 <-> curse@56, ...). Each
is inseparable from its buff: equipping the relic applies both. Verified against
the in-game display (the curse is the blue line under its buff).

Only a subset maps onto the optimizer's two axes (offense, survival); the rest
are out-of-axis BY DEFINITION (player status resistance, rune/flask/ultimate
economy, continuous chip) and are surfaced in the UI but never scored — this is
a modelling boundary, not a data gap.

CURSE_SPEC keys the SCORED curses by effect key:
  gate         : dimension gating the malus (see context.effect_active).
                 None          = always counted. Worst-case posture: a downside
                                 whose trigger is near-universal in combat — below
                                 85% HP, or the post-dodge window (everyone dodges)
                                 — is never discounted, so a cursed relic is never
                                 over-ranked. Its positive twin stays gated
                                 (asymmetric, deliberate).
                 "situational" = other transient windows (post-flask, near-death)
                                 whose uptime is not in the data — gated on the
                                 "situational" toggle; we gate, never invent uptime.
  follow_cycle : the real magnitude lives one hop down a cycleOccurrenceSpEffectId
                 chain (periodic-tick curses) and must be resolved from there.

Curses absent from this table are display-only (out of axis) — shown, not scored.
All magnitudes are the game's real values (data/raw/effect_params.json); nothing
is invented. Per-relic the exact variant (severe 68xxxxx / mild 88xxxxx) is the
attach id actually stored in the save, so the resolved magnitude is per-relic.
"""

CURSE_SPEC = {
    # --- scored, always counted (worst-case / unconditional) ---
    "lowerAttackWhenBelowMaxHP": {"gate": None, "follow_cycle": False},
    "impairedAffinityDamageNegation": {"gate": None, "follow_cycle": False},
    "reducedStrengthAndIntelligence": {"gate": None, "follow_cycle": False},
    "reducedDexterityAndFaith": {"gate": None, "follow_cycle": False},
    "reducedIntelligenceAndDexterity": {"gate": None, "follow_cycle": False},
    "reducedFaithAndStrength": {"gate": None, "follow_cycle": False},
    "reducedVigorAndArcane": {"gate": None, "follow_cycle": False},
    # --- scored, always counted (worst-case): every character dodges, so the
    #     evasion-window malus applies to everyone. Dodge FREQUENCY is not in the
    #     data (Duchess just dodges more), but under a worst-case posture that is
    #     moot — the ceiling is the same for all. Both are also in the acceptance
    #     list, so a player who won't tolerate them can veto the relic. ---
    "moreDamageTakenAfterEvasion": {"gate": None, "follow_cycle": False},
    "repeatedEvasionsLowerDamageNegation": {"gate": None, "follow_cycle": True},
    # NB: post-flask and near-death curses are intentionally NOT scored — their
    # window correlates with safety/rarity and we don't invent an uptime. They
    # are display-only and handled purely through the acceptance list (veto).
}


def spec(key):
    """Scoring spec for a curse key, or None if the curse is display-only."""
    return CURSE_SPEC.get(key)


# UI acceptance list: label + concern group for every curse the save can carry.
# group in {"combat", "survie", "utilitaire"} (keys are internal identifiers);
# the acceptance list is grouped by it so concerns never mix. `spec()` tells
# whether a curse also weighs the score.
CURSE_META = {
    # combat — hurt damage / survival
    "lowerAttackWhenBelowMaxHP": ("Attack lowered at low HP", "combat"),
    "maxHPReducesAttackPower": ("Attack lowered by max HP", "combat"),
    "moreDamageTakenAfterEvasion": ("+ damage taken after a dodge", "combat"),
    "repeatedEvasionsLowerDamageNegation": ("Negation lowered after repeated dodges", "combat"),
    "reducedDamageNegationForFlaskUsages": ("Negation lowered after a flask", "combat"),
    "impairedAffinityDamageNegation": ("Affinity negation impaired", "combat"),
    "nearDeathReducesMaxHP": ("Max HP lowered near death", "combat"),
    "reducedStrengthAndIntelligence": ("Strength and Intelligence lowered", "combat"),
    "reducedDexterityAndFaith": ("Dexterity and Faith lowered", "combat"),
    "reducedIntelligenceAndDexterity": ("Intelligence and Dexterity lowered", "combat"),
    "reducedFaithAndStrength": ("Faith and Strength lowered", "combat"),
    "reducedVigorAndArcane": ("Vigor and Arcane lowered", "combat"),
    "reducedVigor": ("Vigor lowered", "combat"),
    "reducedEndurance": ("Endurance lowered", "combat"),
    "reducedMaximumHP": ("Max HP lowered", "combat"),
    "reducedMaximumStamina": ("Max Stamina lowered", "combat"),
    "reducedMaximumFP": ("Max FP lowered", "combat"),
    "lowerStaminaImpairsDmgNegation": ("Negation lowered at low stamina", "combat"),
    "nearDeathReducesArtGauge": ("Art gauge lowered near death", "combat"),
    "slowerArtGaugeWhenBelowMaxHP": ("Slower Art gauge at low HP", "combat"),
    "attacksImpairedOnOccasion": ("Attacks occasionally impaired", "combat"),
    "ailmentsCauseIncreasedDamage": ("Ailments → increased damage taken", "combat"),
    "nightsTideDamageIncreased": ("Increased damage taken (night's tide)", "combat"),
    "damageIncreasedByNightsEncroachment": ("Increased damage taken (night)", "combat"),
    # survival / status — self-inflicted ailments & resistances
    "allResistancesDown": ("All resistances lowered", "survie"),
    "takingDamageCausesPoisonBuildup": ("Damage taken → self poison", "survie"),
    "takingDamageCausesRotBuildup": ("Damage taken → self rot", "survie"),
    "takingDamageCausesFrostBuildup": ("Damage taken → self frost", "survie"),
    "takingDamageCausesBloodLossBuildup": ("Damage taken → self bleed", "survie"),
    "takingDamageCausesMadnessBuildup": ("Damage taken → self madness", "survie"),
    "takingDamageCausesSleepBuildup": ("Damage taken → self sleep", "survie"),
    "takingDamageCausesDeathBuildup": ("Damage taken → self death blight", "survie"),
    "poisonBuildupWhenBelowMaxHP": ("Self poison at low HP", "survie"),
    "rotBuildupWhenBelowMaxHP": ("Self rot at low HP", "survie"),
    "continuousHPLoss": ("Continuous HP loss", "survie"),
    "nearDeathSpillsFlask": ("Flask spilled near death", "survie"),
    "sleepBuildupForFlaskUsages": ("Self sleep after a flask", "survie"),
    "madnessBuildupForFlaskUsages": ("Self madness after a flask", "survie"),
    # utility — economy / stamina / gauges
    "reducedRuneAcquisition": ("Fewer runes per enemy", "utilitaire"),
    "reducedFlaskHPRestoration": ("Flask HP restoration lowered", "utilitaire"),
    "ultimateArtChargingImpaired": ("Ultimate Art charging impaired", "utilitaire"),
    "surgeSprintingDrainsMoreStamina": ("Sprinting costs more stamina", "utilitaire"),
    "increasedDrainOnStaminaForEvasion": ("Dodging costs more stamina", "utilitaire"),
}

_GROUP_ORDER = {"combat": 0, "survie": 1, "utilitaire": 2}


def display(key, fallback_text=None):
    """(label_fr, group) for a curse key; falls back to its raw text / 'utilitaire'."""
    if key in CURSE_META:
        return CURSE_META[key]
    return (fallback_text or key, "utilitaire")


def group_rank(group):
    return _GROUP_ORDER.get(group, 9)
