#!/usr/bin/env python3
"""Parse FromSoft Scaleform `.layout` texture-atlas descriptors (from a sblytbnd).

Each menu icon is a sub-rectangle of a big atlas page. The `.sblytbnd.dcx` holds
one `.layout` XML per page, e.g.:

    <TextureAtlas imagePath="...\\SB_ItemIcon_0.tif" width="4096" height="4096">
      <SubTexture name="MENU_ItemIcon_00015.png" x="0" width="160" y="0" height="160" .../>

We map each SubTexture name -> (page, x, y, w, h), where `page` is the imagePath
basename without extension (matches the TPF texture name). Stdlib only.
"""
import re

from nightreign.io.regulation import parse_bnd4

_IMG = re.compile(r'imagePath="([^"]+)"')
_SUB = re.compile(
    r'name="([^"]+)"\s+x="(\d+)"\s+width="(\d+)"\s+y="(\d+)"\s+height="(\d+)"'
)


def parse_layouts(sblytbnd_bytes):
    """{subtexture_name: (page_name, x, y, w, h)} across every `.layout` in the bnd."""
    rects = {}
    for fname, blob in parse_bnd4(sblytbnd_bytes).items():
        if not fname.endswith(".layout"):
            continue
        text = blob.decode("utf-8", "replace")
        m = _IMG.search(text)
        if not m:
            continue
        page = m.group(1).replace("\\", "/").split("/")[-1].rsplit(".", 1)[0]
        for name, x, w, y, h in _SUB.findall(text):
            rects[name] = (page, int(x), int(y), int(w), int(h))
    return rects
