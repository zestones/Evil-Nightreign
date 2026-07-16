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
    #     moot — the ceiling is the same for all. ---
    "moreDamageTakenAfterEvasion": {"gate": None, "follow_cycle": False},
    "repeatedEvasionsLowerDamageNegation": {"gate": None, "follow_cycle": True},
    # --- scored, other transient windows (situational toggle only) ---
    "reducedDamageNegationForFlaskUsages": {"gate": "situational", "follow_cycle": False},
    "nearDeathReducesMaxHP": {"gate": "situational", "follow_cycle": True},
}


def spec(key):
    """Scoring spec for a curse key, or None if the curse is display-only."""
    return CURSE_SPEC.get(key)
