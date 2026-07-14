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

# --- Cryptography (validated by successful decryption, not guessed) ---
SAVE_KEY = "18F6326605BD178A5524523AC0A0C609"                                    # AES-128 (save)
REGULATION_KEY = "9A8EE90C4C01A43168A17D9D75E4A7D02107EBCF43D5ACB0554F941601B57918"  # AES-256 (regulation)

# --- Damage model ---
# Global Attack Rating factor on the TOTAL AR per element. Calibrated against the
# Duchess Dagger measured at every level 1..15 plus Reduvia/Black Knife (<0.4% drift).
# See tests/test_attack_rating.py for the ground-truth fixtures.
AR_FACTOR = 0.596
