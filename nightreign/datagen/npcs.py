#!/usr/bin/env python3
"""Build the full enemy combat database (data/curated/npcs.json).

Beyond the 8 Nightlords, expeditions (especially Deep of Night, boss unknown)
throw field bosses at you. This dedupes enemies by base name, keeps their
vulnerability profiles, tags importance, and reports a generalist aggregate.
"""
import json
import re

from nightreign.datagen import nightlords as nl
from nightreign.resources import constants
from nightreign.resources.nightlords import NIGHTLORDS

MIN_HP = 500  # below this: trash that dies regardless of build


def base_name(name):
    name = re.sub(r"\s*[\(\[].*", "", name)
    name = re.sub(r"\s*-\s*(Boss|Random Encounter|Raid|Dummied|Field|Everdark|Enhanced|Phase).*",
                  "", name, flags=re.I)
    return name.strip()


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    npc = json.load(open(constants.DATA_RAW / "npc_params.json"))
    names = nl.load_npc_names()
    nightlord_ids = set(NIGHTLORDS.values())
    nightlord_names = tuple(NIGHTLORDS)

    # Dedupe by base name; keep the highest-HP representative variant.
    best = {}
    for k, row in npc.items():
        nid = int(k)
        name = names.get(nid, "")
        hp = row.get("hp") or 0
        if not name or hp < MIN_HP or any(w in name.lower() for w in ("training", "dummy", "helper")):
            continue
        base = base_name(name)
        if base not in best or hp > best[base][1]:
            best[base] = (nid, hp, name, row)

    database = {}
    for base, (nid, hp, name, row) in best.items():
        if nid in nightlord_ids or name.startswith(nightlord_names):
            category = "nightlord"
        elif hp >= 1500:
            category = "field_boss"
        else:
            category = "enemy"
        entry = nl.profile(row, names, nid)
        entry.pop("status_reading", None)
        entry["category"] = category
        database[base] = entry

    json.dump(database, open(constants.DATA_CURATED / "npcs.json", "w"), ensure_ascii=False, indent=1)
    cats = {}
    for e in database.values():
        cats[e["category"]] = cats.get(e["category"], 0) + 1
    print(f"  npcs: wrote {len(database)} unique enemies {cats}")
