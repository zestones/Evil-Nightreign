#!/usr/bin/env python3
"""Runtime relic reference: id -> name/semantics maps, shipped as a snapshot.

`data/curated/relic_reference.json` is the committed snapshot of the relic
browser's resources (built once by `nr data reference`). It lets ANY player's
save be decoded server-side WITHOUT the developer's cloned browser repo:
  - items   : relic item id  -> {key, color, type}  (its keys are also the
              valid_item_ids validation set every save is scanned against)
  - effects : relic effect id -> {key, group, level, stacks, nightfarer}
  - text    : effect key -> English display text

`build_relics()` is the single transform (raw save records -> relics.json shape)
shared by the datagen (`datagen/relics.py`) and the web upload path
(`ui/server.py`), so a user's decoded collection is identical to the datagen
output for the same save.
"""
import json

from nightreign.resources import constants

# In-game inventory grid width (the relic browser uses 8).
GRID_WIDTH = 8


def load():
    """(effect_by_id, text_by_key, item_by_id) from the shipped snapshot."""
    ref = json.load(open(constants.DATA_CURATED / "relic_reference.json", encoding="utf-8"))
    effect_by_id = {int(k): v for k, v in ref["effects"].items()}
    item_by_id = {int(k): v for k, v in ref["items"].items()}
    return effect_by_id, ref["text"], item_by_id


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


def build_relics(records, effect_by_id, text_by_key, item_by_id):
    """Raw save records -> the relics.json schema (with grid coordinates).

    records: {record_id: (item_id, effect_ids, curse_ids, sort_key)} from
    `savefile.read_relic_records`. Buffs come first (slots 0..n), then the
    Deep-of-Night curses paired positionally to their buff slot. An unknown
    effect id degrades to text=str(id) rather than crashing.
    """
    def entry(e, **extra):
        meta = effect_by_id.get(e, {})
        return dict(
            id=e,
            key=meta.get("key"),
            text=text_by_key.get(meta.get("key"), str(e)),
            group=meta.get("group"),
            level=meta.get("level"),
            stacks=meta.get("stacks", False),
            nightfarer=meta.get("nightfarer"),
            **extra,
        )

    out = []
    for record_id, (item_id, effect_ids, curse_ids, sort_key) in records.items():
        item = item_by_id[item_id]
        effects = [entry(e) for e in effect_ids]
        for slot, c in enumerate(curse_ids):
            if c is None:
                continue
            effects.append(entry(c, is_curse=True, pair=slot))
        out.append(dict(
            record_id=record_id, item_id=item_id, name=item["key"],
            color=item["color"], type=item["type"], sort_key=sort_key,
            effects=effects,
        ))
    _assign_coordinates(out)
    return out
