#!/usr/bin/env python3
"""Snapshot the relic-browser reference into data/curated/relic_reference.json.

The relic browser's TypeScript resources (constants.BROWSER_SRC) map every relic
item id and effect id to names/colours/semantics. We parse them ONCE here and
commit the result so the runtime — the relics datagen AND the web save-upload
decode — never needs the cloned browser repo. Dev-only step: needs BROWSER_SRC
present (regenerate when the browser project updates for a game patch).
"""
import json
import re

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


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    effect_by_id, text_by_key, item_by_id = _load_reference_data()
    out = {
        "effects": {str(k): v for k, v in effect_by_id.items()},
        "text": text_by_key,
        "items": {str(k): v for k, v in item_by_id.items()},
    }
    json.dump(out, open(constants.DATA_CURATED / "relic_reference.json", "w"),
              ensure_ascii=False, indent=1)
    print(f"  reference: snapshotted {len(effect_by_id)} effects, "
          f"{len(item_by_id)} items, {len(text_by_key)} texts")


if __name__ == "__main__":
    run()
