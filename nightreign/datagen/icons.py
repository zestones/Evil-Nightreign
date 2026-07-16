#!/usr/bin/env python3
"""Extract in-game item icons (weapons + relics) into the web UI's static assets.

The icon atlas `/menu/01_common_h.tpf.dcx` holds 26 BC7 pages (4096x4096); the
paired `/menu/01_common_h.sblytbnd.dcx` maps each `MENU_ItemIcon_{id}` to a
rectangle on a page. We decode only the pages we touch, crop every icon the UI
can show, and save a small WebP named by iconId.

Icon ids come straight from the params:
  * weapons -> EquipParamWeapon.iconId   (droppable pool + hero start weapons)
  * relics  -> EquipParamAntique.iconId  (per relic item_id in relics.json)

Outputs:
  * nightreign/ui/static/assets/icons/<iconId>.webp   (gitignored, regenerable)
  * data/curated/icons.json = {"weapons": {wid: iconId}, "relics": {item_id: iconId}}

Build-time only: Pillow (imported lazily) decodes BC7; the runtime UI just serves
the files. Rerun with `nr data icons`.
"""
import io as _io
import json

from nightreign.io import atlas, dcx, paramdef, regulation, tpf
from nightreign.io.archive import DataArchive
from nightreign.resources import constants

ATLAS_TPF = "/menu/01_common_h.tpf.dcx"
ATLAS_SBL = "/menu/01_common_h.sblytbnd.dcx"
SUBTEX = "MENU_ItemIcon_{:05d}.png"
STATUS_SUBTEX = "MENU_StatusIcon_{}.png"  # per-effect category icon
OUT_DIR = constants.PACKAGE / "ui" / "static" / "assets" / "icons"
EFF_DIR = constants.PACKAGE / "ui" / "static" / "assets" / "effect-icons"
ELEM_DIR = constants.PACKAGE / "ui" / "static" / "assets" / "element-icons"
SIZE = 128  # output item-icon edge (px)
EFF_SIZE = 64  # output effect-icon edge (px)

# the game's per-affinity damage icons (SB_PropertyIcon; phys uses the plain
# attack sword from SB_StatusIcon). Confirmed by eye from the atlas.
ELEMENT_SUBTEX = {
    "phys": "MENU_StatusIcon_20206.png",
    "mag": "MENU_PropertyIcon_40146.png",
    "fire": "MENU_PropertyIcon_40148.png",
    "thunder": "MENU_PropertyIcon_40150.png",
    "dark": "MENU_PropertyIcon_40145.png",
}


def _effect_icon_map():
    """{effect_id: statusIconId} for every relic effect that has a category icon
    (AttachEffectParam.statusIconId)."""
    attach = json.load(open(constants.DATA_RAW / "attach_effect.json"))
    relics = json.load(open(constants.DATA_CURATED / "relics.json"))
    out = {}
    for r in relics:
        for e in r["effects"]:
            row = attach.get(str(e["id"]))
            sid = row.get("statusIconId") if row else None
            if isinstance(sid, int) and sid > 0:
                out[str(e["id"])] = sid
    return out


def _decode(name, params):
    _, layout, _ = paramdef.parse_def(constants.DEFS / f"{name}.xml")
    return paramdef.decode_param(params[name], layout)


def _icon_maps():
    """{weapon_id: iconId}, {item_id: iconId} for everything the UI can name."""
    params = regulation.load_params()
    weap = _decode("EquipParamWeapon", params)
    antq = _decode("EquipParamAntique", params)
    weapons = json.load(open(constants.DATA_RAW / "weapons.json"))
    relics = json.load(open(constants.DATA_CURATED / "relics.json"))

    w_icons = {}
    for wid in weapons:
        row = weap.get(int(wid))
        if row and row.get("iconId"):
            w_icons[str(wid)] = row["iconId"]
    r_icons = {}
    for r in relics:
        row = antq.get(r["item_id"])
        if row and row.get("iconId"):
            r_icons[str(r["item_id"])] = row["iconId"]
    return w_icons, r_icons


def run():
    from PIL import Image  # build-time only

    a = DataArchive()
    rects = atlas.parse_layouts(dcx.decompress(a.get(ATLAS_SBL)))
    blobs = tpf.parse_tpf(dcx.decompress(a.get(ATLAS_TPF)))

    w_icons, r_icons = _icon_maps()
    wanted = sorted({*w_icons.values(), *(int(v) for v in r_icons.values())})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pages = {}  # page_name -> decoded RGBA (lazy: only pages we crop from)

    def page(name):
        if name not in pages:
            im = Image.open(_io.BytesIO(blobs[name]))
            im.load()
            pages[name] = im.convert("RGBA")
        return pages[name]

    saved = set()
    for iid in wanted:
        rect = rects.get(SUBTEX.format(iid))
        if not rect:
            continue
        pg, x, y, w, h = rect
        icon = page(pg).crop((x, y, x + w, y + h))
        if icon.size != (SIZE, SIZE):
            icon = icon.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
        icon.save(OUT_DIR / f"{iid}.webp", "WEBP", quality=88, method=6)
        saved.add(iid)

    # keep only mappings whose icon was actually extracted (no dead 404s)
    manifest = {
        "weapons": {k: v for k, v in w_icons.items() if v in saved},
        "relics": {k: v for k, v in r_icons.items() if int(v) in saved},
    }
    json.dump(manifest, open(constants.DATA_CURATED / "icons.json", "w"))
    missing = len(wanted) - len(saved)
    total = sum(f.stat().st_size for f in OUT_DIR.glob("*.webp"))
    print(f"  icons: {len(saved)} WebP written ({missing} ids without an atlas rect), "
          f"{total/1e6:.1f} MB -> {OUT_DIR}")
    print(f"  manifest -> data/curated/icons.json "
          f"({len(manifest['weapons'])} weapons, {len(manifest['relics'])} relics)")

    # per-effect category icons (like the game's relic screen)
    eff_map = _effect_icon_map()
    EFF_DIR.mkdir(parents=True, exist_ok=True)
    eff_saved = set()
    for sid in sorted(set(eff_map.values())):
        rect = rects.get(STATUS_SUBTEX.format(sid))
        if not rect:
            continue
        pg, x, y, w, h = rect
        icon = page(pg).crop((x, y, x + w, y + h)).resize((EFF_SIZE, EFF_SIZE), Image.Resampling.LANCZOS)
        icon.save(EFF_DIR / f"{sid}.webp", "WEBP", quality=90, method=6)
        eff_saved.add(sid)
    eff_manifest = {eid: sid for eid, sid in eff_map.items() if sid in eff_saved}
    json.dump(eff_manifest, open(constants.DATA_CURATED / "effect_icons.json", "w"))
    print(f"  effect icons: {len(eff_saved)} WebP -> {EFF_DIR} "
          f"({len(eff_manifest)} effects mapped -> data/curated/effect_icons.json)")

    # per-affinity damage icons (fire/magic/lightning/holy + physical)
    ELEM_DIR.mkdir(parents=True, exist_ok=True)
    n_elem = 0
    for elem, sub in ELEMENT_SUBTEX.items():
        rect = rects.get(sub)
        if not rect:
            continue
        pg, x, y, w, h = rect
        icon = page(pg).crop((x, y, x + w, y + h)).resize((EFF_SIZE, EFF_SIZE), Image.Resampling.LANCZOS)
        icon.save(ELEM_DIR / f"{elem}.webp", "WEBP", quality=90, method=6)
        n_elem += 1
    print(f"  element icons: {n_elem} WebP -> {ELEM_DIR}")
