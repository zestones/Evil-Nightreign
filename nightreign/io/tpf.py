#!/usr/bin/env python3
"""Minimal TPF (texture package) reader — FromSoft's menu texture container.

A TPF packs several textures (each a standalone DDS blob) behind a small header.
We return each texture's raw DDS bytes by name; the pixel decode (BC7/BC1 ...)
is done build-side in `datagen/icons.py` via Pillow, so this stays stdlib only.

Validated against Nightreign `/menu/01_common_h.tpf` (26 BC7 atlas pages, PC
platform, flag2=3, UTF-16 names). Header: "TPF\\0", dataSize(4), count(4),
platform(1), flag2(1), encoding(1), pad(1); then `count` 20-byte entries of
fileOffset(4), fileSize(4), format/type/mips/flags(4), nameOffset(4), unk(4).
"""
import struct


def parse_tpf(data):
    """{texture_name: dds_bytes} for every texture packed in the TPF."""
    if data[:4] != b"TPF\x00":
        raise ValueError("not a TPF container")
    count = struct.unpack_from("<I", data, 8)[0]
    encoding = data[14]  # 1 = UTF-16LE names, else ASCII/ShiftJIS
    codec = "utf-16-le" if encoding == 1 else "ascii"
    out = {}
    pos = 16
    for _ in range(count):
        file_offset, file_size, name_offset = struct.unpack_from("<II4xI", data, pos)
        pos += 20
        end = data.find(b"\x00\x00", name_offset)
        if (end - name_offset) % 2:
            end += 1
        name = data[name_offset:end].decode(codec, "replace")
        out[name] = data[file_offset:file_offset + file_size]
    return out
