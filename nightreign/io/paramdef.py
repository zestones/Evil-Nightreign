#!/usr/bin/env python3
"""PARAMDEF parser (Smithbox/Paramdex XML) + PARAM row decoder.

Nightreign PARAM format (validated against regulation.bin):
  - 0x40-byte header; rowCount at 0x0A (u16)
  - 24-byte row entries from 0x40: id (s64), dataOffset (s64), nameOffset (s64)
  - row payload decoded via the paramdef (ordered field layout)

Bitfields: a `dummy8 x:N` packs like a `u8` (reserved/padding bits sharing the
byte of the preceding `u8 y:1`). Without this, NpcParam was off by one byte.
Stdlib only.
"""
import re
import struct
import xml.etree.ElementTree as ET

TYPE_SIZE = {"s8": 1, "u8": 1, "dummy8": 1, "s16": 2, "u16": 2, "s32": 4,
             "u32": 4, "f32": 4, "angle32": 4, "f64": 8, "fixstr": 1, "fixstrW": 2}
INT_FMT = {"s8": "<b", "u8": "<B", "s16": "<h", "u16": "<H", "s32": "<i", "u32": "<I"}


def parse_def(xml_path):
    """Parse a paramdef -> (param_type, layout, total_size).

    layout is a list of fields: {type, name, array, bits, offset, bit_pos, eff}.
    total_size is the byte size implied by the def (may exceed the real row size
    when the def lists trailing legacy fields removed from the current game).
    """
    root = ET.parse(xml_path).getroot()
    param_type = root.findtext("ParamType")
    fields = []
    for field_elem in root.iter("Field"):
        definition = field_elem.get("Def").strip()
        # grammar: <type> <name>[<array>] : <bits> = <default>
        m = re.match(r"(\w+)\s+([A-Za-z0-9_]+)\s*(?:\[(\d+)\])?\s*(?::\s*(\d+))?\s*(?:=.*)?$", definition)
        if not m:
            raise ValueError(f"unparsed paramdef field: {definition!r}")
        typ, name, arr, bits = m.groups()
        fields.append(dict(type=typ, name=name,
                           array=int(arr) if arr else None,
                           bits=int(bits) if bits else None))

    layout = []
    offset = 0
    bit_type = None
    bit_pos = 0
    storage_offset = 0
    for f in fields:
        typ, bits = f["type"], f["bits"]
        # a dummy8 bitfield packs as a u8 (reserved bits)
        eff = "u8" if (bits is not None and typ == "dummy8") else typ
        if bits is not None and eff in INT_FMT:
            width = TYPE_SIZE[eff] * 8
            if bit_type != eff or bit_pos + bits > width:
                storage_offset = offset
                offset += TYPE_SIZE[eff]
                bit_type = eff
                bit_pos = 0
            layout.append(dict(**f, offset=storage_offset, bit_pos=bit_pos, eff=eff))
            bit_pos += bits
            continue
        bit_type = None
        bit_pos = 0
        layout.append(dict(**f, offset=offset, bit_pos=None, eff=typ))
        offset += TYPE_SIZE[typ] * (f["array"] or 1)
    return param_type, layout, offset


def read_field(data, f):
    """Read one field from a row's bytes (None for padding/strings)."""
    typ, offset = f["type"], f["offset"]
    if f["bits"] is not None:
        raw = struct.unpack_from(INT_FMT[f["eff"]], data, offset)[0]
        return (raw >> f["bit_pos"]) & ((1 << f["bits"]) - 1)
    if typ in INT_FMT:
        n = f["array"] or 1
        if n == 1:
            return struct.unpack_from(INT_FMT[typ], data, offset)[0]
        return [struct.unpack_from(INT_FMT[typ], data, offset + i * TYPE_SIZE[typ])[0] for i in range(n)]
    if typ in ("f32", "angle32"):
        return struct.unpack_from("<f", data, offset)[0]
    if typ == "f64":
        return struct.unpack_from("<d", data, offset)[0]
    return None  # dummy8 / fixstr / fixstrW: not relevant for simulation


def read_param_rows(param_bytes):
    """Return [(id, dataOffset)] from an in-memory PARAM file."""
    row_count = struct.unpack_from("<H", param_bytes, 0x0A)[0]
    rows = []
    for i in range(row_count):
        pos = 0x40 + i * 24
        row_id = struct.unpack_from("<q", param_bytes, pos)[0]
        data_offset = struct.unpack_from("<q", param_bytes, pos + 8)[0]
        rows.append((row_id, data_offset))
    return rows


def row_size(param_bytes, fallback=None):
    """Infer the payload size of one row from the gap between consecutive rows.

    Rows are stored contiguously, so the delta between successive dataOffsets is
    the real row size. This is derived from the data, never hardcoded.
    """
    rows = read_param_rows(param_bytes)
    if len(rows) >= 2:
        return rows[1][1] - rows[0][1]
    return fallback


def decode_param(param_bytes, layout, size=None):
    """Decode every row -> {id: {field: value}} (non-padding fields only).

    `size` bounds reads; if omitted it is inferred from the data. Fields whose
    end falls beyond `size` are skipped (handles defs with trailing legacy fields).
    """
    if size is None:
        size = row_size(param_bytes)
    rows = read_param_rows(param_bytes)
    usable = []
    for f in layout:
        if f["type"] in ("dummy8", "fixstr", "fixstrW"):
            continue
        width = TYPE_SIZE[f["eff"]] if f["bits"] is not None else TYPE_SIZE[f["type"]] * (f["array"] or 1)
        if f["offset"] + width <= size:
            usable.append(f)
    out = {}
    for row_id, offset in rows:
        data = param_bytes[offset:offset + size]
        if len(data) < size:
            continue
        out[row_id] = {f["name"]: read_field(data, f) for f in usable}
    return out
