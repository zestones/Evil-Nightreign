#!/usr/bin/env python3
"""Extract vessels (chalices) and their coloured slots from the game.

Source of truth: AntiqueStandParam. Each chalice has THREE normal relic slots and
THREE separate Deep-of-Night slots, and their colours can differ - so a build is
3 normal relics + 3 deep relics, each matching its slot's colour. (The relic-
browser flattened these into one list of 6, losing the normal/deep split.)

heroType 1..10 = the Nightfarers; heroType 11 = shared chalices usable by anyone
(appended to every character). Output: data/curated/vessels.json.
"""
import json
import re

from nightreign.io import paramdef, regulation
from nightreign.resources import constants

COLOR = {0: "Any", 1: "Red", 2: "Blue", 3: "Yellow", 4: "Green"}
HERO = {1: "Wylder", 2: "Guardian", 3: "Ironeye", 4: "Duchess", 5: "Raider",
        6: "Revenant", 7: "Recluse", 8: "Executor", 9: "Scholar", 10: "Undertaker"}
SHARED = 11  # heroType for chalices any character can use


def _names():
    entries = json.load(open(constants.NAMES / "AntiqueStandParam.json"))["Entries"]
    return {e["ID"]: e["Entries"][0] for e in entries if e.get("Entries") and e["Entries"][0]}


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    params = regulation.load_params()
    _, layout, _ = paramdef.parse_def(constants.DEFS / "AntiqueStandParam.xml")
    rows = paramdef.decode_param(params["AntiqueStandParam"], layout)
    names = _names()

    def slots(row, prefix):
        return [COLOR.get(row.get(f"{prefix}{i}"), "Any") for i in (1, 2, 3)]

    per_hero, shared = {name: [] for name in HERO.values()}, []
    for rid, row in rows.items():
        hero_type = row.get("heroType")
        if hero_type not in HERO and hero_type != SHARED:
            continue
        vessel = {
            "name": re.sub(r"^\[.*?\]\s*", "", names.get(rid, str(rid))),
            "normal_slots": slots(row, "relicSlot"),
            "deep_slots": slots(row, "deepRelicSlot"),
        }
        (shared if hero_type == SHARED else per_hero[HERO[hero_type]]).append(vessel)

    vessels = {name: entries + shared for name, entries in per_hero.items()}
    json.dump(vessels, open(constants.DATA_CURATED / "vessels.json", "w"),
              ensure_ascii=False, indent=1)
    total = sum(len(v) for v in vessels.values())
    print(f"  vessels: {len(vessels)} characters, {total} chalices "
          f"(3 normal + 3 deep slots each, incl. {len(shared)} shared)")


if __name__ == "__main__":
    run()
