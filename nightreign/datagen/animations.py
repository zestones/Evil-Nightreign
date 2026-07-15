#!/usr/bin/env python3
"""Extract player attack-animation durations from the game archives.

Reads /chr/c0000.anibnd.dcx straight out of the encrypted dvdbnd (io/archive +
io/dcx + io/tae), then records, per TAE category, each animation's play length
in seconds. This is the raw cadence signal: attack duration by animation id.

Output: data/raw/animation_durations.json  {category: {anim_id: seconds}}
        (category = the .tae stem, e.g. "a00", "a03"; anim ids are the
         moveset animation ids referenced by BehaviorParam.)

Requires a copy of the game (data0-3.bhd/.bdt). Run: nr data animations.
"""
import json

from nightreign.io import archive, dcx, tae
from nightreign.io.regulation import parse_bnd4
from nightreign.resources import constants

PLAYER_ANIBND = "/chr/c0000.anibnd.dcx"


def run():
    constants.DATA_RAW.mkdir(parents=True, exist_ok=True)
    try:
        constants.game_root()
    except SystemExit:
        print("  animations: game archives not found — skipped "
              "(run with the game installed to extract)")
        return
    arc = archive.DataArchive()
    anibnd = parse_bnd4(dcx.decompress(arc.get(PLAYER_ANIBND)))

    out = {}
    total = 0
    for name, data in anibnd.items():
        if not name.lower().endswith(".tae") or data[:4] != b"TAE ":
            continue
        cat = name[:-4]  # "a03.tae" -> "a03"
        durations = tae.animation_durations(data)
        if durations:
            out[cat] = {str(aid): round(sec, 4) for aid, sec in sorted(durations.items())}
            total += len(durations)

    json.dump(out, open(constants.DATA_RAW / "animation_durations.json", "w"))
    print(f"  animations: {len(out)} TAE categories, {total} animation durations")


if __name__ == "__main__":
    run()
