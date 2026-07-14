#!/usr/bin/env python3
"""Extract PARAM files from Nightreign's regulation.bin. Read-only, stdlib only.

Validated pipeline (openssl + system libzstd via ctypes):
  regulation.bin --AES-256-CBC--> DCX/ZSTD container --libzstd--> BND4 of ~189 PARAMs

Reads only the local working copy (inputs/regulation.bin); never the Steam install.
"""
import ctypes
import ctypes.util
import os
import struct
import subprocess
import tempfile

from nightreign.resources import constants


def _load_zstd():
    name = ctypes.util.find_library("zstd") or "libzstd.so.1"
    z = ctypes.CDLL(name)
    z.ZSTD_decompress.restype = ctypes.c_size_t
    z.ZSTD_decompress.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_size_t]
    z.ZSTD_isError.restype = ctypes.c_uint
    z.ZSTD_isError.argtypes = [ctypes.c_size_t]
    return z


def decrypt_regulation(path=None):
    """Decrypt regulation.bin -> DCX container (bytes). IV is the leading 16 bytes."""
    path = str(path or constants.REGULATION)
    data = open(path, "rb").read()
    cipher = data[16:]  # first 16 bytes are the (zero) IV
    with tempfile.NamedTemporaryFile(delete=False) as fin:
        fin.write(cipher)
        cipher_path = fin.name
    out_path = cipher_path + ".dec"
    try:
        subprocess.run(
            ["openssl", "enc", "-d", "-aes-256-cbc", "-K", constants.REGULATION_KEY,
             "-iv", "0" * 32, "-nopad", "-in", cipher_path, "-out", out_path],
            check=True, capture_output=True)
        return open(out_path, "rb").read()
    finally:
        for p in (cipher_path, out_path):
            if os.path.exists(p):
                os.remove(p)


def decompress_dcx(dcx):
    """Decompress a DCX/ZSTD container -> BND4 (bytes)."""
    assert dcx[:4] == b"DCX\x00", "expected a DCX container"
    dcs = dcx.find(b"DCS\x00")
    uncompressed_size, compressed_size = struct.unpack_from(">II", dcx, dcs + 4)
    zstd_start = dcx.find(b"\x28\xB5\x2F\xFD")  # ZSTD frame magic
    src = dcx[zstd_start:zstd_start + compressed_size]
    z = _load_zstd()
    dst = ctypes.create_string_buffer(uncompressed_size)
    written = z.ZSTD_decompress(dst, uncompressed_size, src, len(src))
    if z.ZSTD_isError(written):
        raise RuntimeError("ZSTD decompression failed")
    return dst.raw[:written]


def parse_bnd4(bnd):
    """Return {short_param_name: param_bytes} for every BND4 entry."""
    assert bnd[:4] == b"BND4", "expected a BND4 container"
    count = struct.unpack_from("<i", bnd, 0x0C)[0]
    file_header_size = struct.unpack_from("<q", bnd, 0x20)[0]
    out = {}
    for i in range(count):
        p = 0x40 + i * file_header_size
        uncompressed = struct.unpack_from("<q", bnd, p + 0x10)[0]
        data_offset = struct.unpack_from("<I", bnd, p + 0x18)[0]
        name_offset = struct.unpack_from("<I", bnd, p + 0x20)[0]
        end = name_offset
        while bnd[end:end + 2] != b"\x00\x00":
            end += 2
        full_name = bnd[name_offset:end].decode("utf-16-le", "ignore")
        short = full_name.replace("\\", "/").split("/")[-1].replace(".param", "")
        out[short] = bnd[data_offset:data_offset + uncompressed]
    return out


def load_params(path=None):
    """regulation.bin -> {param_name: PARAM bytes}."""
    return parse_bnd4(decompress_dcx(decrypt_regulation(path)))
