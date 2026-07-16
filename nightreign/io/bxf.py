#!/usr/bin/env python3
"""Read a split BXF4 archive (BHF4 header + BDF4 data) — FromSoft's `.tpfbhd` /
`.tpfbdt` menu texture bundles.

Same entry layout as a BND4, but the file data lives in the paired data file
instead of after the header. We return each packed file's raw bytes by name
(usually a `.tpf.dcx`). Stdlib only.

Validated against Nightreign `/menu/00_solo_h.tpfbhd` (1247 entries: character
renders, scenario illustrations, knowledge art).
"""
import struct


def read_bxf4(bhf, bdt):
    """{entry_name: file_bytes} from a BHF4 header (`bhf`) + BDF4 data (`bdt`)."""
    if bhf[:4] != b"BHF4":
        raise ValueError("not a BHF4 header")
    count = struct.unpack_from("<i", bhf, 0x0C)[0]
    file_header_size = struct.unpack_from("<q", bhf, 0x20)[0]
    out = {}
    for i in range(count):
        p = 0x40 + i * file_header_size
        compressed = struct.unpack_from("<q", bhf, p + 0x08)[0]
        uncompressed = struct.unpack_from("<q", bhf, p + 0x10)[0]
        data_offset = struct.unpack_from("<I", bhf, p + 0x18)[0]
        name_offset = struct.unpack_from("<I", bhf, p + 0x20)[0]
        end = name_offset
        while bhf[end:end + 2] != b"\x00\x00":
            end += 2
        name = bhf[name_offset:end].decode("utf-16-le", "ignore")
        size = compressed or uncompressed
        out[name] = bytes(bdt[data_offset:data_offset + size])
    return out
