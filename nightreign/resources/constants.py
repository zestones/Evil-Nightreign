#!/usr/bin/env python3
"""Central constants and paths for the whole project.

Everything (keys, factors, file locations) lives here so nothing is hardcoded
in more than one place. Paths are derived from this file's location, so the
project works wherever it is checked out.
"""
from pathlib import Path

# --- Layout ---
PACKAGE = Path(__file__).resolve().parents[1]   # .../nightreign
ROOT = Path(__file__).resolve().parents[2]       # project root

INPUTS = ROOT / "inputs"                          # local working copies (gitignored)
DATA_RAW = ROOT / "data" / "raw"                  # big regenerable intermediates
DATA_CURATED = ROOT / "data" / "curated"          # small useful deliverables

DEFS = PACKAGE / "io" / "defs"                    # PARAMDEF XMLs
NAMES = PACKAGE / "resources" / "names"           # Smithbox row-name tables

SAVE = INPUTS / "NR0000.sl2"                       # save backup (working copy)
REGULATION = INPUTS / "regulation.bin"             # game params (working copy)

# Reference database for translating relic effect/item ids (cloned sibling repo).
BROWSER_SRC = ROOT.parent / "nightreign-relic-browser" / "src"

# Candidate locations of the game's `Game/` folder, tried in order by `nr setup`
# when no path is given. Override with: `nr setup "/path/to/.../Game"`.
_GAME = "steamapps/common/ELDEN RING NIGHTREIGN/Game"
STEAM_GAME_DIRS = [
    Path(f"/mnt/d/SteamLibrary/{_GAME}"),                     # WSL, secondary library on D:
    Path(f"/mnt/c/Program Files (x86)/Steam/{_GAME}"),        # WSL, default library on C:
    Path.home() / ".steam/steam" / _GAME,                     # native Linux / Proton
    Path.home() / ".local/share/Steam" / _GAME,               # native Linux (alt)
]


def game_root(override=None):
    """First existing game Game/ dir (or the override). Holds data0-3.bhd/.bdt."""
    from pathlib import Path as _P
    cands = [_P(override)] if override else STEAM_GAME_DIRS
    for d in cands:
        if (d / "data0.bhd").exists():
            return d
    raise SystemExit("game archives (data0.bhd) not found; pass the Game/ dir explicitly")

# --- Cryptography (validated by successful decryption, not guessed) ---
SAVE_KEY = "18F6326605BD178A5524523AC0A0C609"                                    # AES-128 (save)
REGULATION_KEY = "9A8EE90C4C01A43168A17D9D75E4A7D02107EBCF43D5ACB0554F941601B57918"  # AES-256 (regulation)

# --- Damage model ---
# Global Attack Rating factor on the TOTAL AR per element. Calibrated against the
# Duchess Dagger measured at every level 1..15 plus Reduvia/Black Knife (<0.4% drift).
# See tests/test_attack_rating.py for the ground-truth fixtures.
AR_FACTOR = 0.596

# Spell-attack factor (engine/attack_rating.spell_attack). CALIBRATED
# 2026-07-17 by a mono-hit in-game measure (Glintstone Arc through the base
# Glintstone Staff, Recluse 15, no relics): 141 displayed = 148 base ×
# 1.59 displayed scaling × 0.599 — the spell constant IS the weapon AR_FACTOR.
# Cross-checked: Stars of Ruin 480 ⇒ 12 connected stars, Rancorcall 342 ⇒ ~6
# hits, both consistent at this factor (data/ground_truth/spell_scaling.json).
SPELL_FACTOR = AR_FACTOR
SPELL_FACTOR_CALIBRATED = True

# Residual correction of our internal stat-scaling term for spells. CALIBRATED
# over the FULL INT range 2026-07-17: a Recluse Glintstone Pebble/Arc damage
# curve measured at every level 1..15 (INT 5->51, no relics) gives a FLAT
# least-squares constant 0.9027 (the "correction needed" stays 0.896..0.906
# across all levels — so our softcap curve, calcCorrectGraph, is CORRECT; only
# this flat multiplier was off). Full curve reproduced to <1 damage at all 15
# levels once stats are linearly interpolated (see runner.hero_stats_row).
SPELL_SCALING_CORRECTION = 0.9027

# Max FP from Mind. Derived by exact linear fit on four independent
# community-reported level-15 pools (Duchess 180 @ Mind 27, Revenant 200 @ 31,
# Recluse 195 @ 30, Wylder 140 @ 19) — over-determined and consistent. One
# in-game menu reading during the calibration session will confirm it.
FP_BASE = 45
FP_PER_MIND = 5

# Max Stamina from Endurance. Stamina = 48 + 2*Endurance — CONFIRMED 2026-07-17
# (two Nightreign sources + game8 per-character table: Duchess 84 @ END18,
# Recluse 94 @ 23, Raider 122 @ 37, Guardian 124 @ 38, all exact). Per-attack
# stamina COSTS are extracted per weapon (motion.stamina_costs, from
# BehaviorParam: dagger R1 9, greatsword 15, colossal/greataxe 20). The one
# missing piece for a full sustain constraint is the REGEN rate (no reliable
# online source; one in-game chrono needed) — until then stamina is surfaced
# as info (hits-per-bar), not scored.
STAMINA_BASE = 48
STAMINA_PER_END = 2
