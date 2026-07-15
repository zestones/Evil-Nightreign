#!/usr/bin/env python3
"""Extract vessels (chalices) and their coloured slots from the game.

Source of truth: AntiqueStandParam. Each chalice has THREE normal relic slots and
THREE separate Deep-of-Night slots, and their colours can differ - so a build is
3 normal relics + 3 deep relics, each matching its slot's colour. (The relic-
browser flattened these into one list of 6, losing the normal/deep split.)

heroType 1..10 = the Nightfarers; heroType 11 = shared chalices usable by anyone
(appended to every character). Output: data/curated/vessels.json.

Ownership: purchased vessels live in the save's goods inventory (item id
0x40000000|goodsId); default urns (unlockFlag == 0) never enter it — they are
granted with the character. The "X's Chalice" rows exist fully wired in the
params (names, slots, unlockFlag, goodsId) but have no unlock path in the
current game version (none owned even with every bazaar purchase done, verified
2026-07-15) — they carry `owned: false` and the optimizer must skip them.
"""
import json
import re
import struct

from nightreign.io import paramdef, regulation, savefile
from nightreign.resources import constants

# Verified in-game against Wylder's full vessel list (FR "Rôdeur", 2026-07-15):
# all 9 vessels match slot-for-slot, in display order, under this mapping —
# e.g. Urn [0,0,1]=[R,R,B], Decrepit Goblet [1,3,2]=[B,G,Y], Forgotten Goblet
# deep [0,3,4]=[R,G,Any]. The rare value 4 (one per Chalice normal + Forgotten
# Goblet deep) is the colorless "Any" slot; the Grails are mono-color
# (Erdtree=Yellow, Spirit Shelter=Green, Giant's Cradle=Blue, Scadutree=Red).
COLOR = {0: "Red", 1: "Blue", 2: "Yellow", 3: "Green", 4: "Any"}
HERO = {1: "Wylder", 2: "Guardian", 3: "Ironeye", 4: "Duchess", 5: "Raider",
        6: "Revenant", 7: "Recluse", 8: "Executor", 9: "Scholar", 10: "Undertaker"}
SHARED = 11  # heroType for chalices any character can use
GOODS_CATEGORY = 0x40000000  # goods item ids in the save carry this category bit


def _names():
    entries = json.load(open(constants.NAMES / "AntiqueStandParam.json"))["Entries"]
    return {e["ID"]: e["Entries"][0] for e in entries if e.get("Entries") and e["Entries"][0]}


def _owned_goods(goods_ids):
    """The subset of goods_ids present in the save's goods inventory."""
    patterns = {g: struct.pack("<I", GOODS_CATEGORY | g) for g in goods_ids}
    owned = set()
    for _, buf in savefile.decrypt_slots():
        for g, pat in patterns.items():
            if g not in owned and buf.find(pat) != -1:
                owned.add(g)
    return owned


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    params = regulation.load_params()
    _, layout, _ = paramdef.parse_def(constants.DEFS / "AntiqueStandParam.xml")
    rows = paramdef.decode_param(params["AntiqueStandParam"], layout)
    names = _names()

    def slots(row, prefix):
        return [COLOR.get(row.get(f"{prefix}{i}"), "Any") for i in (1, 2, 3)]

    kept = [(rid, row) for rid, row in rows.items()
            if row.get("heroType") in HERO or row.get("heroType") == SHARED]
    owned_goods = _owned_goods({row["goodsId"] for _, row in kept})

    per_hero, shared = {name: [] for name in HERO.values()}, []
    for rid, row in kept:
        hero_type = row["heroType"]
        vessel = {
            "name": re.sub(r"^\[.*?\]\s*", "", names.get(rid, str(rid))),
            "normal_slots": slots(row, "relicSlot"),
            "deep_slots": slots(row, "deepRelicSlot"),
            "goods_id": row["goodsId"],
            "owned": row["goodsId"] in owned_goods,
            "default": row.get("unlockFlag") == 0,
        }
        (shared if hero_type == SHARED else per_hero[HERO[hero_type]]).append(vessel)

    # A default urn (unlockFlag == 0) never enters the goods inventory: mark it
    # owned iff the character is actually played (owns any purchasable vessel).
    for name, entries in per_hero.items():
        active = any(v["owned"] for v in entries)
        for v in entries:
            if v["default"] and active:
                v["owned"] = True

    vessels = {name: entries + shared for name, entries in per_hero.items()}
    json.dump(vessels, open(constants.DATA_CURATED / "vessels.json", "w"),
              ensure_ascii=False, indent=1)
    total = sum(len(v) for v in vessels.values())
    n_owned = sum(v["owned"] for arr in vessels.values() for v in arr)
    print(f"  vessels: {len(vessels)} characters, {total} chalices "
          f"(3 normal + 3 deep slots each, incl. {len(shared)} shared), "
          f"{n_owned} owned")


if __name__ == "__main__":
    run()
