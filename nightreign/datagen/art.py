#!/usr/bin/env python3
"""Extract character visuals for the web UI: face icons, full-body renders,
scenario illustrations.

Sources:
  * `/menu/01_common_h.tpf.dcx` (+ its sblytbnd) — the icon atlas. Page
    `SB_MenuIcon_1` holds the Nightfarer **face icons** `MENU_MenuIcon_41{C}0`
    (C = index in runner.HERO_ORDER) — the clean portrait busts the game uses in
    its character-select / player cards.
  * `/menu/00_solo_h.tpfbhd`+`.tpfbdt` (a split BXF4 bundle) — `MENU_Character_49{C}00`
    full-body renders on transparent backgrounds, and `MENU_ScenarioIllust_*`
    ink-on-parchment lore illustrations.

Outputs (gitignored, regenerable — copyright):
  * nightreign/ui/static/assets/art/faces/<Character>.webp    (256, char select)
  * nightreign/ui/static/assets/art/heroes/<Character>.webp   (full-body scene)
  * nightreign/ui/static/assets/art/illust/<id>.webp

Build-time only (Pillow). Rerun with `nr data art`.
"""
import io as _io
import re

from nightreign.io import atlas, bxf, dcx, tpf
from nightreign.io.archive import DataArchive
from nightreign.optimize.runner import HERO_ORDER
from nightreign.resources import constants

SOLO_BHF = "/menu/00_solo_h.tpfbhd"
SOLO_BDT = "/menu/00_solo_h.tpfbdt"
ATLAS_TPF = "/menu/01_common_h.tpf.dcx"
ATLAS_SBL = "/menu/01_common_h.sblytbnd.dcx"
ART_DIR = constants.PACKAGE / "ui" / "static" / "assets" / "art"
HERO_MAX_H = 1100
ILLUST_MAX_W = 1400
FACE_SIZE = 256


def _decode_tpf(blob):
    from PIL import Image
    if blob[:4] == b"DCX\x00":
        blob = dcx.decompress(blob)
    dds = next(iter(tpf.parse_tpf(blob).values()))
    im = Image.open(_io.BytesIO(dds))
    im.load()
    return im.convert("RGBA")


def run():
    from PIL import Image

    a = DataArchive()
    faces = ART_DIR / "faces"
    heroes = ART_DIR / "heroes"
    illust = ART_DIR / "illust"
    for d in (faces, heroes, illust):
        d.mkdir(parents=True, exist_ok=True)

    # --- face icons (01_common atlas, page SB_MenuIcon_1) --------------------
    rects = atlas.parse_layouts(dcx.decompress(a.get(ATLAS_SBL)))
    blobs = tpf.parse_tpf(dcx.decompress(a.get(ATLAS_TPF)))
    pages = {}

    def page(name):
        if name not in pages:
            im = Image.open(_io.BytesIO(blobs[name]))
            im.load()
            pages[name] = im.convert("RGBA")
        return pages[name]

    n_faces = 0
    for c, name in enumerate(HERO_ORDER):
        rect = rects.get(f"MENU_MenuIcon_{41000 + c * 10}.png")
        if not rect:
            continue
        pg, x, y, w, h = rect
        ic = page(pg).crop((x, y, x + w, y + h)).resize((FACE_SIZE, FACE_SIZE), Image.Resampling.LANCZOS)
        ic.save(faces / f"{name}.webp", "WEBP", quality=90, method=6)
        n_faces += 1

    # --- full-body renders + illustrations (00_solo BXF4) --------------------
    entries = bxf.read_bxf4(a.get(SOLO_BHF), a.get(SOLO_BDT))

    n_heroes = 0
    for c, name in enumerate(HERO_ORDER):
        key = f"MENU_Character_49{c}00.tpf.dcx"
        if key not in entries:
            continue
        im = _decode_tpf(entries[key])
        bbox = im.getbbox()
        if bbox:
            im = im.crop(bbox)
        if im.height > HERO_MAX_H:
            im = im.resize((round(im.width * HERO_MAX_H / im.height), HERO_MAX_H), Image.Resampling.LANCZOS)
        im.save(heroes / f"{name}.webp", "WEBP", quality=90, method=6)
        n_heroes += 1

    n_illust = 0
    for key in entries:
        m = re.match(r"MENU_ScenarioIllust_(\d+)\.tpf\.dcx$", key)
        if not m:
            continue
        im = _decode_tpf(entries[key]).convert("RGB")
        if im.width > ILLUST_MAX_W:
            im = im.resize((ILLUST_MAX_W, round(im.height * ILLUST_MAX_W / im.width)), Image.Resampling.LANCZOS)
        im.save(illust / f"{m.group(1)}.webp", "WEBP", quality=82, method=6)
        n_illust += 1

    print(f"  art: {n_faces} face icons -> {faces}")
    print(f"  art: {n_heroes} hero renders -> {heroes}")
    print(f"  art: {n_illust} illustrations -> {illust}")
