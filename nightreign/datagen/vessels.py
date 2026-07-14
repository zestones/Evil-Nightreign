#!/usr/bin/env python3
"""Extract the vessels (chalices) and their coloured relic slots per character.

A build = relics placed into a vessel's slots, each slot constraining the relic
colour (Red/Blue/Yellow/Green, or Any). This is THE constraint the optimizer
respects. The data is game knowledge, taken from the cloned relic-browser's
Vessels.ts (each `<char>Vessels` list already includes the shared "anyone"
vessels via a spread, which we re-append here).

Output: data/curated/vessels.json  ->  {Character: [{name, slots:[colours]}]}
"""
import json
import re

from nightreign.resources import constants


def _parse_entries(block):
    """All {name, slots:[colours]} vessel entries inside a TS array block."""
    out = []
    for m in re.finditer(r'name:\s*"([^"]+)",\s*slots:\s*\[([^\]]*)\]', block):
        name, slots = m.group(1), m.group(2)
        colours = re.findall(r"RelicSlotColor\.(\w+)", slots)
        out.append({"name": name, "slots": colours})
    return out


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    text = open(constants.BROWSER_SRC / "utils" / "Vessels.ts", encoding="utf-8").read()

    # Split into `export const <name>Vessels = [...]` blocks.
    blocks = {}
    parts = re.split(r"export const (\w+)Vessels\b", text)
    for i in range(1, len(parts), 2):
        blocks[parts[i]] = _parse_entries(parts[i + 1])

    anyone = blocks.pop("anyone", [])
    vessels = {}
    for const_name, entries in blocks.items():
        character = const_name[0].upper() + const_name[1:]
        vessels[character] = entries + anyone  # TS spreads ...anyoneVessels

    json.dump(vessels, open(constants.DATA_CURATED / "vessels.json", "w"),
              ensure_ascii=False, indent=1)
    total = sum(len(v) for v in vessels.values())
    print(f"  vessels: {len(vessels)} characters, {total} vessels (incl. {len(anyone)} shared each)")
