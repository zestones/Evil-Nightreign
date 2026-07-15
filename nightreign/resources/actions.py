#!/usr/bin/env python3
"""Attack-action taxonomy: which attacks a gated relic effect applies to.

Two engine mechanisms gate offensive relic effects to specific actions
(verified against the raw SpEffect rows, 2026-07-15):

  * `magicSubCategoryChange1/2/3` — the SpEffect's attack-rate fields only
    apply to attacks of that sub-category. Values are self-labeled by the
    effect keys that carry them (e.g. 120 only ever appears on
    improvedThrowingKnifeDamage*).
  * `stateInfo` — hardcoded engine behaviors; 367 is the critical-hit damage
    boost (game-verified: normal hits untouched, crits multiplied), 2100 is
    "3+ armaments of the type equipped" (a loadout STATE, not an action).

The optimizer counts an action-gated effect at the weight the player's play
profile gives that action (default: 100% melee).
"""

# attack sub-category -> action class of the play profile
SUBCATEGORY_ACTIONS = {
    130: "melee",
    119: "initial",           # first standard attack of a chain
    111: "skill", 112: "skill",
    103: "guard_counter",
    120: "throwing_knife",
    108: "throwing_pot",
    121: "glintstone_stones",
    109: "perfume",
    106: "roar_breath", 107: "roar_breath", 116: "roar_breath",
    104: "chain_finisher",    # Undertaker's chain-attack final blow
    124: "stance_break", 125: "stance_break",
    # sorcery / incantation schools
    2: "sorcery_carian", 3: "sorcery_glintblade", 4: "sorcery_stonedigger",
    5: "sorcery_crystalian", 9: "sorcery_thorn", 11: "sorcery_gravity",
    12: "sorcery_invisibility",
    20: "incant_godslayer", 21: "incant_giants_flame", 22: "incant_dragon_cult",
    23: "incant_bestial", 24: "incant_fundamentalist",
    25: "incant_dragon_communion", 26: "incant_frenzied_flame",
}

# stateInfo values that gate an effect to an action
STATEINFO_ACTIONS = {
    367: "crit",              # critical hits only — game-verified 2026-07-15
}

# stateInfo values that gate an effect behind a controllable STATE (a toggle)
STATEINFO_STATES = {
    2100: "triple_loadout",   # requires 3+ armaments of the boosted type
}

# generic spell buffs (exactly one of the SpEffect magParamChange /
# miracleParamChange flags): they apply to every school of their kind
SPELL_UMBRELLAS = ("sorcery_any", "incant_any")

#: every declarable action class (for CLI validation)
ACTION_CLASSES = sorted(set(SUBCATEGORY_ACTIONS.values())
                        | set(STATEINFO_ACTIONS.values()) | set(SPELL_UMBRELLAS))

#: an effect with no action gate applies to every action
ANY_ACTION = "*"


# actions performed WITH the melee weapon inherit melee buffs (sub-cat 130).
# Game-verified 2026-07-15: initial (first chain hit got x1.15 AND x1.06),
# skill (weapon art got x1.15 x x1.06 = x1.197 measured) and crit (backstab
# got exactly the melee ratio, and NOT the skill buff). guard_counter and
# chain_finisher are extrapolated (same melee-performed family, unmeasured).
MELEE_PERFORMED = {"initial", "skill", "crit", "guard_counter", "chain_finisher"}


def classes_applying_to(action):
    """Effect action classes whose buffs apply when performing `action`.

    A generic sorcery buff (sorcery_any) applies to every sorcery school;
    school buffs apply only to their school; melee-performed actions inherit
    the melee buffs (see MELEE_PERFORMED).
    """
    out = {ANY_ACTION, action}
    if action in MELEE_PERFORMED:
        out.add("melee")
    if action.startswith("sorcery_"):
        out.add("sorcery_any")
    if action.startswith("incant_"):
        out.add("incant_any")
    return out


def parse_play_profile(spec):
    """'melee=0.7,skill=0.2,crit=0.1' -> normalized {action: weight}.

    None/empty -> the default pure-melee benchmark profile.
    """
    if not spec:
        return {"melee": 1.0}
    profile = {}
    for part in spec.split(","):
        name, _, value = part.partition("=")
        name = name.strip()
        if name not in ACTION_CLASSES:
            raise SystemExit(f"unknown action '{name}' — known: {', '.join(ACTION_CLASSES)}")
        profile[name] = float(value) if value else 1.0
    total = sum(profile.values())
    if total <= 0:
        raise SystemExit("play profile weights must sum to a positive value")
    return {a: w / total for a, w in profile.items()}
