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


# UI acceptance list: FR label + concern group for every curse the save can carry.
# group in {"combat", "survie", "utilitaire"}; the acceptance list is grouped by
# it so concerns never mix. `spec()` tells whether a curse also weighs the score.
CURSE_META = {
    # combat — hurt damage / survival
    "lowerAttackWhenBelowMaxHP": ("Attaque réduite à PV bas", "combat"),
    "maxHPReducesAttackPower": ("Attaque réduite selon les PV max", "combat"),
    "moreDamageTakenAfterEvasion": ("+ dégâts subis après une esquive", "combat"),
    "repeatedEvasionsLowerDamageNegation": ("Négation réduite après esquives répétées", "combat"),
    "reducedDamageNegationForFlaskUsages": ("Négation réduite après une fiole", "combat"),
    "impairedAffinityDamageNegation": ("Négation d'affinité réduite", "combat"),
    "nearDeathReducesMaxHP": ("PV max réduits près de la mort", "combat"),
    "reducedStrengthAndIntelligence": ("Force et Intelligence réduites", "combat"),
    "reducedDexterityAndFaith": ("Dextérité et Foi réduites", "combat"),
    "reducedIntelligenceAndDexterity": ("Intelligence et Dextérité réduites", "combat"),
    "reducedFaithAndStrength": ("Foi et Force réduites", "combat"),
    "reducedVigorAndArcane": ("Vigueur et Arcane réduites", "combat"),
    "reducedVigor": ("Vigueur réduite", "combat"),
    "reducedEndurance": ("Endurance réduite", "combat"),
    "reducedMaximumHP": ("PV max réduits", "combat"),
    "reducedMaximumStamina": ("Endurance max réduite", "combat"),
    "reducedMaximumFP": ("PP max réduits", "combat"),
    "lowerStaminaImpairsDmgNegation": ("Négation réduite à faible endurance", "combat"),
    "nearDeathReducesArtGauge": ("Jauge d'Art réduite près de la mort", "combat"),
    "slowerArtGaugeWhenBelowMaxHP": ("Jauge d'Art plus lente à PV bas", "combat"),
    "attacksImpairedOnOccasion": ("Attaques parfois entravées", "combat"),
    "ailmentsCauseIncreasedDamage": ("Afflictions → dégâts subis accrus", "combat"),
    "nightsTideDamageIncreased": ("Dégâts subis accrus (marée nocturne)", "combat"),
    "damageIncreasedByNightsEncroachment": ("Dégâts subis accrus (nuit)", "combat"),
    # survie / statut — self-inflicted ailments & resistances
    "allResistancesDown": ("Toutes les résistances réduites", "survie"),
    "takingDamageCausesPoisonBuildup": ("Dégâts subis → poison sur soi", "survie"),
    "takingDamageCausesRotBuildup": ("Dégâts subis → pourriture sur soi", "survie"),
    "takingDamageCausesFrostBuildup": ("Dégâts subis → gel sur soi", "survie"),
    "takingDamageCausesBloodLossBuildup": ("Dégâts subis → hémorragie sur soi", "survie"),
    "takingDamageCausesMadnessBuildup": ("Dégâts subis → folie sur soi", "survie"),
    "takingDamageCausesSleepBuildup": ("Dégâts subis → sommeil sur soi", "survie"),
    "takingDamageCausesDeathBuildup": ("Dégâts subis → fléau mortel sur soi", "survie"),
    "poisonBuildupWhenBelowMaxHP": ("Poison sur soi à PV bas", "survie"),
    "rotBuildupWhenBelowMaxHP": ("Pourriture sur soi à PV bas", "survie"),
    "continuousHPLoss": ("Perte de PV continue", "survie"),
    "nearDeathSpillsFlask": ("Fiole renversée près de la mort", "survie"),
    "sleepBuildupForFlaskUsages": ("Sommeil sur soi après une fiole", "survie"),
    "madnessBuildupForFlaskUsages": ("Folie sur soi après une fiole", "survie"),
    # utilitaire — economy / stamina / gauges
    "reducedRuneAcquisition": ("Moins de runes par ennemi", "utilitaire"),
    "reducedFlaskHPRestoration": ("PV rendus par la fiole réduits", "utilitaire"),
    "ultimateArtChargingImpaired": ("Charge d'Art ultime réduite", "utilitaire"),
    "surgeSprintingDrainsMoreStamina": ("Sprint plus coûteux en endurance", "utilitaire"),
    "increasedDrainOnStaminaForEvasion": ("Esquive plus coûteuse en endurance", "utilitaire"),
}

_GROUP_ORDER = {"combat": 0, "survie": 1, "utilitaire": 2}


def display(key, fallback_text=None):
    """(label_fr, group) for a curse key; falls back to its raw text / 'utilitaire'."""
    if key in CURSE_META:
        return CURSE_META[key]
    return (fallback_text or key, "utilitaire")


def group_rank(group):
    return _GROUP_ORDER.get(group, 9)
