#!/usr/bin/env python3
"""Extract owned relics from the local save copy into data/curated/relics.json.

Names/semantics come from the committed relic reference snapshot
(`nr data reference` → resources/relic_reference.py) — the SAME maps and the
SAME `build_relics` transform the web save-upload path uses, so the datagen and
the server produce identical relics for a given save. We only read the local
save copy.
"""
import json

from nightreign.io import savefile
from nightreign.resources import constants, relic_reference


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    effect_by_id, text_by_key, item_by_id = relic_reference.load()
    print(f"  relics: reference ({len(effect_by_id)} effects, {len(item_by_id)} items)")

    records = savefile.read_relic_records(set(item_by_id))
    out = relic_reference.build_relics(records, effect_by_id, text_by_key, item_by_id)
    n_curses = sum(1 for r in out for e in r["effects"] if e.get("is_curse"))

    json.dump(out, open(constants.DATA_CURATED / "relics.json", "w"), ensure_ascii=False, indent=1)
    print(f"  relics: extracted {len(out)} relics (with grid coordinates), "
          f"{n_curses} Deep-of-Night curses paired")


if __name__ == "__main__":
    run()
