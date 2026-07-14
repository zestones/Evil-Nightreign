#!/usr/bin/env python3
"""Matchup demo: for a fixed attack power, best damage type against each Nightlord.

Shows how the optimal element changes per boss (their damage cut rates differ).
Run: python examples/matchup_demo.py   (or `nr demo matchup`)
"""
import json

from nightreign.resources import constants

ELEMENTS = ["phys", "slash", "fire", "lightning", "magic", "holy"]
LABEL = {"phys": "Phys", "slash": "Slash", "fire": "Fire", "lightning": "Light",
         "magic": "Magic", "holy": "Holy"}
BASE_AR = 700.0


def main():
    nightlords = json.load(open(constants.DATA_CURATED / "nightlords.json"))
    print(f"Base AR {BASE_AR:.0f} — damage by type, best choice per boss:\n")
    print(f"{'Nightlord':10} | " + " ".join(f"{LABEL[t]:>6}" for t in ELEMENTS) + " | best")
    print("-" * 64)
    for name, boss in nightlords.items():
        dmg = {t: BASE_AR * boss["damage_multiplier"].get(t, 1.0) for t in ELEMENTS}
        best = max(dmg, key=dmg.get)
        cells = " ".join(f"{dmg[t]:6.0f}" for t in ELEMENTS)
        print(f"{name:10} | {cells} | {LABEL[best]} (x{boss['damage_multiplier'].get(best, 1.0):.2f})")


if __name__ == "__main__":
    main()
