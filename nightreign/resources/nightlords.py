#!/usr/bin/env python3
"""The 8 Nightlords and their canonical main-boss NpcParam row ids.

This is knowledge (a mapping we established), not generated data, so it lives in
code as the single source of truth. datagen/nightlords.py turns it into the
data/curated/nightlords.json roster with full combat stats.
"""

# Nightlord -> main "(Boss)" NpcParam row id.
NIGHTLORDS = {
    "Gladius": 75000020,   # Beast of Night
    "Adel": 75100020,      # Baron of Night
    "Gnoster": 75200020,   # Wisdom of Night
    "Maris": 75400020,     # Fathom of Night
    "Libra": 75600020,     # Creature of Night
    "Fulghor": 76000010,   # Champion of Nightglow
    "Caligo": 49000010,    # Miasma of Night
    "Heolstor": 75800000,  # Shape of Night (final boss)
}
