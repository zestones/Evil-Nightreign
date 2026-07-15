#!/usr/bin/env python3
"""DCX container decompression (FromSoft), ZSTD and Oodle Kraken.

A DCX wraps one compressed blob. Codec is named at DCP+4:
  * ZSTD — used by regulation.bin (handled with system libzstd).
  * KRAK — Oodle Kraken, used by the packed archives (chr, map, ...). The
    payload is ONE Oodle stream of independent 0x40000-output blocks; we
    decode block by block through libooz (built from powzix/ooz — see
    io/oodle/). ooz's own multi-block loop mis-resets decoder state on the
    large chr anibnds, so we drive the per-block step ourselves.

Validated 2026-07-15: /chr/c0000.anibnd.dcx -> 57.6 MB BND4, 220 blocks,
523 TAE files with intact magic.
"""
import ctypes
import struct
from pathlib import Path

from nightreign.io import regulation  # reuse the zstd path

_OOZ = None
_OODLE_DIR = Path(__file__).parent / "oodle"
_BLOCK = 0x40000  # Oodle uncompressed block size


def _ooz():
    global _OOZ
    if _OOZ is None:
        lib = ctypes.CDLL(str(_OODLE_DIR / "libooz.so"))
        lib.ooz_step.restype = ctypes.c_int
        lib.ooz_step.argtypes = [ctypes.c_char_p, ctypes.c_size_t,
                                 ctypes.c_char_p, ctypes.c_size_t,
                                 ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
        _OOZ = lib
    return _OOZ


def _kraken_decompress(src, uncompressed_size):
    lib = _ooz()
    su, du = ctypes.c_int(), ctypes.c_int()
    out = bytearray()
    soff = 0
    while len(out) < uncompressed_size:
        want = min(_BLOCK, uncompressed_size - len(out))
        dst = ctypes.create_string_buffer(_BLOCK)
        ok = lib.ooz_step(src[soff:], len(src) - soff, dst, want,
                          ctypes.byref(su), ctypes.byref(du))
        if not ok or du.value <= 0:
            raise ValueError(f"Oodle decode failed at output {len(out)}")
        out += dst.raw[:du.value]
        soff += su.value
    return bytes(out)


def decompress(dcx):
    """DCX container bytes -> decompressed payload (BND4, TAE, ...)."""
    if dcx[:4] != b"DCX\x00":
        raise ValueError("not a DCX container")
    dcs = dcx.find(b"DCS\x00")
    uncompressed, compressed = struct.unpack_from(">II", dcx, dcs + 4)
    dcp = dcx.find(b"DCP\x00")
    codec = dcx[dcp + 4:dcp + 8]
    dca = dcx.find(b"DCA\x00")
    data_start = dca + struct.unpack_from(">I", dcx, dca + 4)[0]
    payload = dcx[data_start:data_start + compressed]
    if codec == b"KRAK":
        return _kraken_decompress(payload, uncompressed)
    if codec in (b"ZSTD", b"DFLT"):
        return regulation.decompress_dcx(dcx)  # its own zstd/deflate path
    raise ValueError(f"unsupported DCX codec {codec!r}")
