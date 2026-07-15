#!/usr/bin/env python3
"""Read files out of Nightreign's encrypted dvdbnd archives (data0-3.bhd/.bdt).

Pipeline (all stdlib + the bundled Oodle lib), validated 2026-07-15:
  .bhd  --RSA(public key)-->  BHD5 index (path-hash -> offset/size/AES ranges)
  .bdt  --seek + partial AES-128-ECB-->  DCX container
  DCX   --> io/dcx.decompress (Oodle Kraken / ZSTD)

The per-archive RSA public keys are the standard community constants (as
shipped in UXM/BinderTool), reused read-only against a copy of the game the
user owns. Format per TKGP's SoulsFormats (BHD5.cs / SFUtil.cs).
"""
import base64
import struct

MASK64 = (1 << 64) - 1
HASH_PRIME = 0x85  # ER/NR 64-bit dvdbnd path hash

# Public per-archive BHD keys (PKCS#1 RSA PUBLIC KEY). Cryptographic constants.
KEYS = {
    "data0": "MIIBDAKCAQEAz8F9U1V9hgKs40gdzl1ZOf3IBirf6xUEzXtDd6oSEBE6XiYocvAB"
             "ykiK+WMdAaJL7HJ58Gt2xSRxA3t9toCGKMI/3gNAfcR0BV83gsQo0O0dVP0fqyxX"
             "lA2pGN5B4IE8aLWPX2cNNFSFKAdjYnzsYSevzef/pgnpV1ZgPf2j2SQwNGSufYeN"
             "3Owji8l0K2C0fKIx6gSO0cK9kvTIm8AdpvzZbBkTylT1jF3m8DsSA1OFzFJTdFyZ"
             "bTRi85M6bmv6rHtvZc5OW21dye7Q6fmLlxOyMetLTu4dpOXjHAAf/LFTbfQpXFr9"
             "aXO4O6I7nWDJn7FRzNlLkb8RwSyZ1/KWyQIFALEDsAc=",
    "data1": "MIIBDAKCAQEA0E6dtnDmT6d2+VaNkPzomUNv+T6896H//RAaTR2guPACMDNZpAsF"
             "vV3MfNcR2BS6Cbxl55MmMWsmsZs1s293MuOdS+c99vmZbNYcXWjx0uJGO+VrRXe4"
             "3TRzmQFh1uD+Xcq6+wYfTrGyLOdAtmwdDXNvW8jYoFDM7nsuoPKOXKtKd0uz7/MK"
             "ZYLk1J7pAoBQqw9VD5qi2Ih86zn0VWm5lLMTI0qnutOzpZVDvZWBg/jr4Nbnr/Ox"
             "PLeJO1tFuRuHUPuBAWtYM/J23MPqqKkQrG5z2r7PexUI744UPdmo3Sn+Mqynuxxv"
             "V9SEhska6pStzn8R9i94wOKPTQ32HEFuUQIFAP////8=",
    "data2": "MIIBDAKCAQEAqpkf9yHnx8k84+WXITLFUW/STypXjZMPuw842pzNHa5L7v9gU4M5"
             "hBHwTQs0YIcfnf+mbjqoJYnmYPBblxLjFXgwT4ICJdpnPMY75BwD0Nv28/CvvIsA"
             "0QQWOhUeOXnm5BT26dGYi3CHHPvD14F76tJt3TO/CC3fyhdxne9Cra5G87aGTJGv"
             "0ImsU0KPCizYX/RHQ2jdJdlB5BHzkMgLhIaEdhC3nhIqMJDNQNGKMo7rRV1tAEGf"
             "0zIZ23PGEsPsbVg31nnnRoq338WfD9ArZZG6bM11vlfVcYmrJs7v4vBjKXnYVwVX"
             "0rQGIfSNDnaZcEj4tsl04AqnupTdvSrHXwIFANOg6RU=",
    "data3": "MIIBCwKCAQEAwm2Rcw4eoP8FgWijxw1X8b9rEVFsVqy7rXWcH2yVm61yYBlzPlTq"
             "Kqnc2VeqZSh/TLXeFY3+Om2X78RQxZNS3L3OokvD7l/0wqPIpXSSumeeL8UAZm5k"
             "7nFA2m2HJfc+F07kNwwCEqhmFs5YQIMnWyIrqnEax/qSncFErLjIYMBMArVnVLE8"
             "WqgsD7N8lW937dlUcT2TaPh1HfjavKOSUy/OHM9zaneyDL4NRmDdU8GmNXTSm5kP"
             "YoSRCDIvFVj0g5iaXr60eRh0d+40TctoBUdtaoJCPOyRlmkE7qU6Q9FyyvMNbhtf"
             "D95d+6IJejNd7kvyV/ISlB37kb2Uh9TavwIEOqKLtw==",
}


def _rsa_public(b64):
    """(modulus, exponent) from a PKCS#1 RSAPublicKey DER blob."""
    der = base64.b64decode(b64)

    def read_len(d, p):
        n = d[p]; p += 1
        if n < 0x80:
            return n, p
        k = n & 0x7F
        return int.from_bytes(d[p:p + k], "big"), p + k

    def read_int(d, p):
        assert d[p] == 0x02
        p += 1
        ln, p = read_len(d, p)
        return int.from_bytes(d[p:p + ln], "big"), p + ln

    assert der[0] == 0x30
    _, pos = read_len(der, 1)
    modulus, pos = read_int(der, pos)
    exponent, pos = read_int(der, pos)
    return modulus, exponent


def _decrypt_bhd(enc, modulus, exponent):
    """RSA-decrypt a .bhd header (public-key modexp per block, drop byte[0])."""
    block = (modulus.bit_length() + 7) // 8
    out = bytearray()
    for i in range(0, len(enc), block):
        b = enc[i:i + block]
        if len(b) < block:
            break
        m = pow(int.from_bytes(b, "big"), exponent, modulus)
        out += m.to_bytes(block, "big")[1:]
    return bytes(out)


def path_hash(path):
    h = path.replace("\\", "/").lower()
    if not h.startswith("/"):
        h = "/" + h
    acc = 0
    for ch in h:
        acc = (acc * HASH_PRIME + ord(ch)) & MASK64
    return acc


def _parse_bhd5(data):
    """decrypted BHD5 -> {name_hash: (offset, size, aes_key, aes_ranges)}."""
    if data[:4] != b"BHD5":
        raise ValueError("bad BHD5 magic — wrong RSA key")
    endian = ">" if data[4] == 0 else "<"
    bucket_count, buckets_offset = struct.unpack_from(endian + "ii", data, 16)
    entries = {}
    pos = buckets_offset
    buckets = [struct.unpack_from(endian + "ii", data, pos + 8 * i)
               for i in range(bucket_count)]
    for count, off in buckets:
        ep = off
        for _ in range(count):
            nh, padded, _unp, foff, _sha, aes_off = struct.unpack_from(
                endian + "QiiQqq", data, ep)
            ep += 40
            key, ranges = None, []
            if aes_off != 0:
                key = bytes(data[aes_off:aes_off + 16])
                rc = struct.unpack_from(endian + "i", data, aes_off + 16)[0]
                rp = aes_off + 20
                for _ in range(rc):
                    s, e = struct.unpack_from(endian + "qq", data, rp)
                    rp += 16
                    ranges.append((s, e))
            entries[nh] = (foff, padded, key, ranges)
    return entries


def _aes_ecb_ranges(buf, key, ranges):
    """AES-128-ECB decrypt the given byte ranges in place (system openssl)."""
    import subprocess
    import tempfile
    for start, end in ranges:
        if start < 0 or end <= start:
            continue
        n = (end - start)
        n -= n % 16
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(bytes(buf[start:start + n]))
            src = f.name
        out = src + ".dec"
        try:
            subprocess.run(["openssl", "enc", "-d", "-aes-128-ecb", "-K", key.hex(),
                            "-nopad", "-in", src, "-out", out],
                           check=True, capture_output=True)
            buf[start:start + n] = open(out, "rb").read()
        finally:
            import os
            for p in (src, out):
                if os.path.exists(p):
                    os.remove(p)


class DataArchive:
    """Index of every file across data0-3; fetch by in-archive path."""

    def __init__(self, game_dir=None):
        from nightreign.resources import constants
        self.game_dir = constants.game_root(game_dir)
        self._index = {}
        for name, b64 in KEYS.items():
            bhd = self.game_dir / f"{name}.bhd"
            if not bhd.exists():
                continue
            raw = bhd.read_bytes()
            dec = raw if raw[:4] == b"BHD5" else _decrypt_bhd(raw, *_rsa_public(b64))
            for h, entry in _parse_bhd5(dec).items():
                self._index.setdefault(h, (name, entry))

    def __len__(self):
        return len(self._index)

    def __contains__(self, path):
        return path_hash(path) in self._index

    def get(self, archive_path):
        """Raw (still DCX) bytes for e.g. '/chr/c0000.anibnd.dcx'."""
        hit = self._index.get(path_hash(archive_path))
        if hit is None:
            raise KeyError(archive_path)
        name, (offset, size, key, ranges) = hit
        with open(self.game_dir / f"{name}.bdt", "rb") as f:
            f.seek(offset)
            data = bytearray(f.read(size))
        if key:
            _aes_ecb_ranges(data, key, ranges)
        return bytes(data)
