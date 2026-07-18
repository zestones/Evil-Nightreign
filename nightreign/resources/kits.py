#!/usr/bin/env python3
"""Per-Nightfarer kit sheets: passives, skill paradigms, team buffs, archetypes.

Curated semantic layer over the params: the hidden skill/ultimate weapons
(characters.json) carry exact bases and scaling, but HOW a kit's mechanics
bind into the score is per-character knowledge. Doctrine identical to the
Deep-of-Night curses: every figure carries its source; anything unsourced is
`None` -> displayed, NEVER scored (research report 2026-07-17, docs/ROADMAP.md).

Skill paradigms (verified 2026-07-17 web research, multi-source):
  strike  — the hidden weapon IS the damage model (base+scaling exact).
  replay  — parasitic on recent damage (Duchess Restage: re-applies 50% of
            the damage nearby enemies took in the last 3s; 60% with her
            exclusive relic). Modeled as a burst-window multiplier.
  utility — no damage component worth scoring (still shown).

`multipliers` values are dimensionless factors with an explicit gate; a gate
of None means "always on is WRONG" — they apply only when the matching
toggle/profile element is engaged, mirroring context.effect_active.
"""

# source shorthand used below:
#   wiki  = Fextralife/wiki.gg mechanical description (cross-checked)
#   patch = official Bandai Namco patch notes
#   datamined = extracted params (exact)
KITS = {
    "Wylder": {
        "passive": {"name": "Sixth Sense", "effect": "one cheat-death per grace",
                    "value": None, "source": "wiki"},   # survival value unmodeled
        "skill_paradigm": "strike",       # Claw Shot: mobility + small hit
        "ultimate_paradigm": "strike",    # Onslaught Stake 205 phys + 205 fire (datamined)
        "favored_sources": ["melee"],
        "archetypes": [
            {"name": "Versatile colossus", "play": {"melee": 1.0}},
            {"name": "Skill-weaver", "play": {"melee": 0.7, "char_skill": 0.2,
                                              "ultimate_art": 0.1}},
        ],
    },
    "Guardian": {
        "passive": {"name": "Steel Guard", "effect": "guard boost ×5 while braced",
                    "value": 5.0, "gate": "guarding", "source": "wiki ×5 (multi-source)"},
        "skill_paradigm": "strike",       # Whirlwind 150 phys (datamined)
        "ultimate_paradigm": "utility",   # Wings of Salvation: rez + immunity aura
        "favored_sources": ["melee", "guard"],
        "archetypes": [
            {"name": "Bulwark", "play": {"melee": 1.0},
             "toggles": ["situational"], "weapon": "Halberd"},
            {"name": "Whirlwind", "play": {"melee": 0.75, "char_skill": 0.25},
             "weapon": "Halberd"},
        ],
    },
    "Ironeye": {
        "passive": {"name": "Eagle Eye", "effect": "+30 discovery (team)",
                    "value": None, "source": "wiki"},   # economy, out of combat axes
        "skill_paradigm": "strike",       # Marking dash 70 phys (datamined)
        "ultimate_paradigm": "strike",    # Single Shot 280 phys STR/DEX (datamined)
        "team_buffs": [
            {"name": "Marking", "effect": "target takes more damage",
             "factor": 1.10, "duration_s": 17.5, "scope": "team",
             "gate": "char_skill", "source": "wiki +10% (3+ independent sources)"},
        ],
        "favored_sources": ["ranged", "status"],
        "archetypes": [
            {"name": "Archer", "play": {"melee": 1.0},
             "toggles": ["status_build"], "weapon": "Bow"},
            {"name": "Marked burst", "play": {"melee": 0.6, "char_skill": 0.2,
                                              "ultimate_art": 0.2}, "weapon": "Bow"},
        ],
    },
    "Duchess": {
        "passive": {"name": "Magnificent Poise", "effect": "chained dodges, cheaper stamina",
                    "value": None, "source": "wiki"},
        "skill_paradigm": "replay",
        "replay": {"share": 0.50, "share_with_relic": 0.60, "window_s": 3.0,
                   "cooldown_s": 12.0, "source": "wiki (verbatim, multi-source)"},
        "ultimate_paradigm": "utility",   # Finale: invisibility, zero damage
        "favored_sources": ["melee", "status", "spells"],
        "archetypes": [
            # NB: named for the weapon/playstyle, NOT a promised status — the
            # optimizer ranks daggers by damage and won't guarantee bleed (the
            # status_build toggle still biases toward it when a bleed dagger wins).
            {"name": "Speed daggers", "play": {"melee": 0.8, "char_skill": 0.2},
             "toggles": ["status_build"], "weapon": "Dagger"},
            {"name": "INT caster", "play": {"sorcery_any": 0.6, "melee": 0.4},
             "weapon": "Staff"},
        ],
    },
    "Raider": {
        "passive": {"name": "Fighter's Resolve", "effect": "+50% attack below 25% HP",
                    "value": 1.5, "gate": "low_hp", "source": "wiki (charged variant disputed: +50% wiki vs +24% dummy-test — calibration item)"},
        "skill_paradigm": "strike",       # Retaliate 90 phys STR80 (datamined)
        "ultimate_paradigm": "strike",    # Totem Stela 360 phys (datamined)
        "team_buffs": [
            {"name": "Totem Stela", "effect": "physical attack up near the totem",
             "factor": 1.15, "duration_s": 20.0, "scope": "team-physical",
             "gate": "ultimate_art", "source": "wiki +15% (multi-source)"},
        ],
        "favored_sources": ["melee"],
        "archetypes": [
            {"name": "STR colossals", "play": {"melee": 0.8, "char_skill": 0.2}},
            {"name": "Low-HP berserk", "play": {"melee": 1.0}, "toggles": ["low_hp"]},
        ],
    },
    "Revenant": {
        "passive": {"name": "Necromancy", "effect": "slain foes rise as phantoms",
                    "value": None, "source": "wiki"},
        "skill_paradigm": "utility",      # spirits are FIXED-power minions
        "spirits_note": "fixed-power, excluded from gear optimization (community consensus)",
        "ultimate_paradigm": "utility",   # Immortal March: 1-HP floor + revive
        "favored_sources": ["incantations"],
        "archetypes": [
            {"name": "FAI incantations", "play": {"incant_any": 0.7, "melee": 0.3},
             "toggles": ["caster"], "weapon": "Sacred Seal"},
        ],
    },
    "Recluse": {
        "passive": {"name": "Elemental Defense", "effect": "residues restore FP",
                    "value": None, "source": "wiki"},
        "skill_paradigm": "strike",       # Magic Cocktail 25 mag INT100 (datamined; outputs table-driven)
        "ultimate_paradigm": "strike",    # Soulblood Song marks (114 initial, wiki)
        "team_buffs": [
            {"name": "Soulblood Song", "effect": "marked enemies take more damage",
             "factor": None,             # +15% phys/+14% magic wiki-stated, un-datamined
             "scope": "team", "gate": "ultimate_art",
             "source": "wiki (unconfirmed split — displayed, not scored)"},
        ],
        "favored_sources": ["sorceries"],
        "archetypes": [
            {"name": "Glintstone caster", "play": {"sorcery_any": 0.8, "melee": 0.2},
             "toggles": ["caster"], "weapon": "Staff"},
            {"name": "Cocktail hybrid", "play": {"sorcery_any": 0.5, "char_skill": 0.3,
                                                  "melee": 0.2}, "toggles": ["caster"], "weapon": "Staff"},
        ],
    },
    "Executor": {
        "passive": {"name": "Tenacity", "effect": "+20% attack for 20s on self status proc",
                    "value": 1.2, "gate": "status_build",
                    "source": "wiki +20% (multi-source)"},
        "skill_paradigm": "strike",       # Cursed Sword: level-scaled table (wiki 137→396)
        "ultimate_paradigm": "utility",   # Beast transformation (weapon id -1)
        "favored_sources": ["melee", "status"],
        "archetypes": [
            {"name": "Katana duelist", "play": {"melee": 0.8, "char_skill": 0.2},
             "toggles": ["status_build"], "weapon": "Katana"},
            {"name": "Deflector", "play": {"melee": 0.6, "char_skill": 0.4},
             "toggles": ["status_build"], "weapon": "Katana"},
        ],
    },
    "Scholar": {
        "passive": {"name": "Bagcraft", "effect": "consumable stacks + tiered effects",
                    "value": None, "source": "official reveal"},
        "skill_paradigm": "utility",      # Analyze: tiered debuffs/buffs, no flat number
        "ultimate_paradigm": "utility",   # Communion: ~20% damage sharing (qualitative)
        "favored_sources": ["status", "throwing"],
        "archetypes": [
            {"name": "Piercing status", "play": {"melee": 1.0},
             "toggles": ["status_build"]},
            {"name": "Alchemist", "play": {"melee": 0.7, "throwing_pot": 0.3},
             "toggles": ["status_build"]},
        ],
    },
    "Undertaker": {
        "passive": {"name": "Confluence", "effect": "free ultimate when an ally ults",
                    "value": None, "source": "official reveal"},
        "skill_paradigm": "strike",       # Trance: consecutive-hit attack boosts
        "ultimate_paradigm": "strike",    # Loathsome Hex 315 phys (datamined)
        "favored_sources": ["melee", "incantations"],
        "archetypes": [
            {"name": "STR/FAI hammers", "play": {"melee": 0.85, "ultimate_art": 0.15}},
            {"name": "Faith hybrid", "play": {"melee": 0.6, "incant_any": 0.4},
             "toggles": ["caster"]},
        ],
    },
}


def kit(character):
    """The character's kit sheet ({} when unknown)."""
    return KITS.get(character, {})


def offense_factor(character, toggles, play):
    """(factor, details) — the product of the kit mechanics that multiply the
    build's ABSOLUTE offense, with per-mechanic provenance.

    Every kit factor is CONSTANT within a context (character/toggles/profile
    fixed), so it never changes the relic argmax — the proven search is
    untouched; the factor corrects the displayed absolute numbers and the
    archetype comparison. Only sourced figures enter (None = display-only).
    """
    k = KITS.get(character) or {}
    factor, details = 1.0, {}
    passive = k.get("passive") or {}
    gate = passive.get("gate")
    if passive.get("value") and gate and gate != "guarding" and gate in toggles:
        # attack-side passives only (Steel Guard is a guard-axis factor,
        # for the future guard model, not the offense axis)
        factor *= passive["value"]
        details[passive["name"]] = {"factor": passive["value"],
                                    "source": passive.get("source")}
    for buff in k.get("team_buffs") or []:
        if buff.get("factor") and buff.get("gate") in play:
            factor *= buff["factor"]
            details[buff["name"]] = {"factor": buff["factor"],
                                     "source": buff.get("source")}
    # replay skills (Duchess Restage): re-applies `share` of the window's
    # damage every cooldown -> average offense multiplier 1 + share×(window/cd)
    rp = k.get("replay")
    if rp and k.get("skill_paradigm") == "replay" and "char_skill" in play:
        f = 1.0 + rp["share"] * (rp["window_s"] / rp["cooldown_s"])
        factor *= f
        details["replay"] = {"factor": round(f, 4), "source": rp.get("source")}
    return factor, details
