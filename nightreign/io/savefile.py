#!/usr/bin/env python3
"""Read owned relics from the local save copy (inputs/NR0000.sl2). Read-only.

Save format (same scheme as Elden Ring): BND4 of 14 USER_DATA blocks, each
AES-128-CBC (IV = leading 16 bytes, no padding). Decrypted "cleanData" drops the
first 4 bytes. A relic is a 0xC0 / 80-byte record: id@0, itemId@4..6, up to four buff effect
ids @16/20/24/28 and up to three Deep-of-Night curse (debuff) ids @56/60/64,
paired positionally to the buffs (0xFFFFFFFF = empty). Curse slots decoded from
the in-game display (validated); the relic-browser reads only the buff array.

Name resolution lives in datagen/relics.py; this module only decodes raw records.
Stdlib only.
"""
import os
import struct
import subprocess
import tempfile

from nightreign.resources import constants

_VALID_B3 = {0x80, 0x81, 0x82, 0x83, 0x84, 0x85}
_RELIC_RECORD = 0xC0  # 80-byte relic slot marker


def decrypt_slots(save_path=None):
    """Yield (index, cleanData) for each USER_DATA block of the save."""
    data = open(str(save_path or constants.SAVE), "rb").read()
    count = struct.unpack_from("<i", data, 12)[0]
    for i in range(count):
        entry = 0x40 + i * 0x20
        size = struct.unpack_from("<Q", data, entry + 8)[0]
        offset = struct.unpack_from("<I", data, entry + 0x10)[0]
        block = data[offset:offset + size]
        with tempfile.NamedTemporaryFile(delete=False) as fc:
            fc.write(block[16:])
            cipher_path = fc.name
        out_path = cipher_path + ".dec"
        try:
            subprocess.run(
                ["openssl", "enc", "-d", "-aes-128-cbc", "-K", constants.SAVE_KEY,
                 "-iv", block[:16].hex(), "-nopad", "-in", cipher_path, "-out", out_path],
                check=True, capture_output=True)
            yield i, open(out_path, "rb").read()[4:]  # cleanData drops the first 4 bytes
        finally:
            for p in (cipher_path, out_path):
                if os.path.exists(p):
                    os.remove(p)


def scan_relics(buffer, valid_item_ids):
    """Scan a decrypted block -> {record_id: (item_id, [effect_ids], [curse_ids])}.

    Validates on a known itemId (strong signal) and keeps every effect id so no
    relic is silently dropped, even if its effect is not in the reference DB.

    A relic record carries TWO effect arrays: the buffs at 16/20/24/28 and the
    Deep-of-Night curses (debuffs) at 56/60/64, paired positionally to the buffs
    (buff slot k <-> curse slot k). `curses` is index-aligned to the buff slots
    (None where a buff has no paired curse); trailing empties are trimmed.
    """
    found = {}
    length = len(buffer)
    i = 0
    while i < length - 4:
        if buffer[i + 2] in _VALID_B3 and buffer[i + 3] == _RELIC_RECORD and i + 80 <= length:
            record = buffer[i:i + 80]
            record_id = struct.unpack_from("<I", record, 0)[0]
            item_id = record[4] | (record[5] << 8) | (record[6] << 16)
            effects = [struct.unpack_from("<I", record, o)[0] for o in (16, 20, 24, 28)]
            effects = [e for e in effects if e != 0xFFFFFFFF]
            curses = [struct.unpack_from("<I", record, o)[0] for o in (56, 60, 64)]
            curses = [c if c != 0xFFFFFFFF else None for c in curses]
            while curses and curses[-1] is None:
                curses.pop()
            if item_id in valid_item_ids and effects:
                found[record_id] = (item_id, effects, curses)
                i += 80
                continue
        i += 1
    return found


def find_sort_key(buffer, record_id):
    """The relic's in-game sort key: search for <id><01000000>, read u16 at +8.

    The game stores each relic's inventory ordering separately from the relic
    record itself; this is what its grid position derives from. None if absent.
    """
    pattern = struct.pack("<I", record_id) + b"\x01\x00\x00\x00"
    idx = buffer.find(pattern)
    if idx == -1:
        return None
    return struct.unpack_from("<H", buffer, idx + 8)[0]


def read_relic_records(valid_item_ids, save_path=None):
    """All relic records across the save -> {record_id: (item_id, effects, curses, sort_key)}."""
    relics = {}
    for _index, buffer in decrypt_slots(save_path):
        for record_id, (item_id, effects, curses) in scan_relics(buffer, valid_item_ids).items():
            relics[record_id] = (item_id, effects, curses, find_sort_key(buffer, record_id))
    return relics


def read_relic_records_from_bytes(valid_item_ids, data):
    """`read_relic_records` for an in-memory save (uploaded bytes).

    Spills to a temp file (decrypt_slots reads a path and shells to openssl),
    then removes it — the raw save is never persisted. Used by the web upload
    path so a visitor can optimize on their own collection."""
    with tempfile.NamedTemporaryFile(suffix=".sl2", delete=False) as f:
        f.write(data)
        path = f.name
    try:
        return read_relic_records(valid_item_ids, path)
    finally:
        if os.path.exists(path):
            os.remove(path)
