#!/usr/bin/env python3
"""Extract owned relics from the local save copy into data/curated/relics.json.

Effect/item names are resolved from the cloned nightreign-relic-browser project's
TypeScript resources (constants.BROWSER_SRC). We only read the local save copy.
"""
import json
import re

from nightreign.io import savefile
from nightreign.resources import constants


def _load_reference_data():
    """Parse the browser's TS resources -> (effect_by_id, text_by_key, item_by_id)."""
    def read(rel):
        return open(constants.BROWSER_SRC / rel, encoding="utf-8").read()

    array = read("resources/effects.ts").split("export const effectsArray = [", 1)[1]
    effect_by_id = {}
    for m in re.finditer(r"key:\s*EffectKey\.(\w+),(.*?)(?=key:\s*EffectKey\.|\Z)", array, re.S):
        key, body = m.group(1), m.group(2)
        ids_match = re.search(r"ids:\s*\[([^\]]*)\]", body)
        if not ids_match:
            continue
        group = re.search(r"group:\s*EffectGroup\.(\w+)", body)
        level = re.search(r"level:\s*(\d+)", body)
        nightfarer = re.search(r"nightfarer:\s*Nightfarer\.(\w+)", body)
        stacks = "stacks: true" in body
        for i in re.findall(r"\d+", ids_match.group(1)):
            effect_by_id[int(i)] = dict(
                key=key,
                group=group.group(1) if group else None,
                level=int(level.group(1)) if level else None,
                stacks=stacks,
                nightfarer=nightfarer.group(1) if nightfarer else None,
            )

    text_by_key = dict(re.findall(r'\[EffectKey\.(\w+)\]:\s*\n?\s*"([^"]*)"', read("i18n.ts")))

    item_by_id = {}
    for m in re.finditer(
        r'key:\s*"(\w+)",\s*color:\s*(RelicSlotColor\.\w+|null),\s*ids:\s*\[([^\]]*)\],\s*type:\s*ItemType\.(\w+)',
        read("resources/items.ts"),
    ):
        key, color, ids, type_ = m.groups()
        color = color.split(".")[-1] if color != "null" else None
        for i in re.findall(r"\d+", ids):
            item_by_id[int(i)] = dict(key=key, color=color, type=type_)

    return effect_by_id, text_by_key, item_by_id


# In-game inventory grid width used for row/column. The relic-browser uses 8;
# adjust if your in-game grid differs (then re-run `nr data relics`).
GRID_WIDTH = 8


def _assign_coordinates(relics):
    """Set grid (row, col) and per-colour (row, col), matching the in-game order.

    Normal relics and Deep Relics are separate inventory tabs, so each is laid
    out independently; within each, relics are ordered by their sort_key.
    """
    for group in ("normal", "deep"):
        members = [r for r in relics if (r["type"] == "DeepRelic") == (group == "deep")]
        members.sort(key=lambda r: -(r["sort_key"] or 0))
        by_colour = {}
        for i, r in enumerate(members):
            r["grid"] = [i // GRID_WIDTH, i % GRID_WIDTH]
            n = by_colour.get(r["color"], 0)
            r["grid_by_color"] = [n // GRID_WIDTH, n % GRID_WIDTH]
            by_colour[r["color"]] = n + 1


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    effect_by_id, text_by_key, item_by_id = _load_reference_data()
    print(f"  relics: reference data ({len(effect_by_id)} effects, {len(item_by_id)} items)")

    records = savefile.read_relic_records(set(item_by_id))
    out = []
    for record_id, (item_id, effect_ids, sort_key) in records.items():
        item = item_by_id[item_id]
        out.append(dict(
            record_id=record_id, item_id=item_id, name=item["key"],
            color=item["color"], type=item["type"], sort_key=sort_key,
            effects=[dict(
                id=e,
                key=effect_by_id.get(e, {}).get("key"),
                text=text_by_key.get(effect_by_id.get(e, {}).get("key"), str(e)),
                group=effect_by_id.get(e, {}).get("group"),
                level=effect_by_id.get(e, {}).get("level"),
                stacks=effect_by_id.get(e, {}).get("stacks", False),
                nightfarer=effect_by_id.get(e, {}).get("nightfarer"),
            ) for e in effect_ids],
        ))
    _assign_coordinates(out)
    json.dump(out, open(constants.DATA_CURATED / "relics.json", "w"), ensure_ascii=False, indent=1)
    print(f"  relics: extracted {len(out)} relics (with grid coordinates)")
