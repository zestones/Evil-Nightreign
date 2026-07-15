#!/usr/bin/env python3
"""Minimal TAE (TimeAct) reader for ER/Nightreign — per-animation durations.

A TAE holds many animations; each references a pool of float timestamps (event
times, in seconds). The animation's play length is the max finite timestamp
(FLT_MAX entries are "infinite/until-cancel" sentinels and are skipped). Layout
per TKGP's SoulsFormats TAE.cs / Animation.cs, SDT/ER 64-bit variant (0x1000D).

Validated 2026-07-15: the R1 chain in the sword category comes out at
~0.97/1.8/2.8s (rising through the combo), matching the in-game feel.
"""
import struct

_FLT_MAX = 1e30  # sentinel guard (real FLT_MAX ~3.4e38)


def animation_durations(tae):
    """{anim_id: play_length_seconds} for one TAE file's bytes."""
    if tae[:4] != b"TAE ":
        raise ValueError("not a TAE")
    version = struct.unpack_from("<i", tae, 8)[0]
    if version != 0x1000D:
        raise ValueError(f"unsupported TAE version {version:#x}")
    anim_count = struct.unpack_from("<i", tae, 0x54)[0]
    anims_offset = struct.unpack_from("<q", tae, 0x58)[0]
    out = {}
    for i in range(anim_count):
        p = anims_offset + i * 16
        anim_id = struct.unpack_from("<q", tae, p)[0]
        offset = struct.unpack_from("<q", tae, p + 8)[0]
        # anim subheader (ER): +0x10 timesOffset (i64), +0x28 timesCount (i32)
        times_offset = struct.unpack_from("<q", tae, offset + 0x10)[0]
        times_count = struct.unpack_from("<i", tae, offset + 0x28)[0]
        if times_count <= 0:
            continue
        times = [t for t in struct.unpack_from(f"<{times_count}f", tae, times_offset)
                 if 0 <= t < _FLT_MAX]
        if times:
            out[anim_id] = max(times)
    return out
