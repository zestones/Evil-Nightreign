#!/usr/bin/env python3
"""Throwable/consumable damage catalog (pots, knives, perfumes...).

Chain (validated on the params 2026-07-17): EquipParamGoods.refId_default ->
Bullet -> AtkParam_Pc, the SAME resolution the spell catalog uses (magic.py's
bullet-tree recursion, shared-hit window included). `level2RefId`/`level3RefId`
are Scholar's Bagcraft tiers of the same consumable.

Only goods that resolve REAL damage are kept; the play-profile action class
of each is inferred from its name (pot/knife/dart/perfume families) — a good
with no recognizable family is kept with action=null (displayed, not scored).

Output: data/curated/goods.json {id: {name, action, damage, hits, confidence,
status, super_armor, tiers: {2: {...}, 3: {...}}}}
"""
import json

from nightreign.io import paramdef, regulation
from nightreign.resources import constants
from nightreign.datagen.magic import _resolve_bullet, _worse  # shared resolution

# name fragment -> play-profile action class (resources/actions.py taxonomy)
_ACTION_BY_NAME = (
    ("Pot", "throwing_pot"),
    ("Knife", "throwing_knife"),
    ("Dagger", "throwing_knife"),
    ("Dart", "throwing_knife"),
    ("Perfume", "perfume"),
    ("Spraymist", "perfume"),
)


def _resolve(ref_id, bullets, atk, speffects):
    if not ref_id or ref_id <= 0:
        return None
    acc = _resolve_bullet(ref_id, bullets, atk, speffects)
    solo, shared = acc["solo"], acc["shared"]
    sh_damage, sh_hits = shared["damage"], shared["hits"]
    if sh_hits > 1 and acc["rehits"]:
        window = 1 + int(acc["duration"] / min(acc["rehits"]))
        if window < sh_hits:
            scale = window / sh_hits
            sh_damage = {t: v * scale for t, v in sh_damage.items()}
            sh_hits = window
    damage = dict(solo["damage"])
    for t, v in sh_damage.items():
        damage[t] = damage.get(t, 0) + v
    if not damage:
        return None
    status = dict(solo["status"])
    for k, v in shared["status"].items():
        status[k] = status.get(k, 0) + v
    out = {"damage": {t: round(v, 4) for t, v in damage.items()},
           "hits": round(solo["hits"] + sh_hits, 4), "confidence": acc["conf"]}
    if status:
        out["status"] = {k: round(v, 4) for k, v in status.items()}
    sa = solo["sa"] + shared["sa"]
    if sa:
        out["super_armor"] = round(sa, 4)
    return out


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    print("  goods: reading regulation.bin ...")
    params = regulation.load_params()

    def decode(name, defname=None):
        _, layout, _ = paramdef.parse_def(constants.DEFS / f"{defname or name}.xml")
        return paramdef.decode_param(params[name], layout)

    goods = decode("EquipParamGoods")
    bullets = decode("Bullet")
    atk = decode("AtkParam_Pc", "AtkParam")
    speffects = decode("SpEffectParam")
    names_path = constants.NAMES / "EquipParamGoods.json"
    names = {e["ID"]: e["Entries"][0]
             for e in json.load(open(names_path))["Entries"]
             if e.get("Entries") and e["Entries"][0]} if names_path.exists() else {}

    out = {}
    n_actioned = 0
    for gid, g in goods.items():
        payload = _resolve(g.get("refId_default"), bullets, atk, speffects)
        if not payload:
            continue
        name = names.get(gid, f"goods {gid}")
        action = next((a for frag, a in _ACTION_BY_NAME if frag.lower() in name.lower()), None)
        entry = {"name": name, "action": action, **payload}
        tiers = {}
        for lvl, field in ((2, "level2RefId"), (3, "level3RefId")):
            t = _resolve(g.get(field), bullets, atk, speffects)
            if t:
                tiers[str(lvl)] = t
        if tiers:
            entry["tiers"] = tiers
        if action:
            n_actioned += 1
        out[gid] = entry

    json.dump(out, open(constants.DATA_CURATED / "goods.json", "w"),
              ensure_ascii=False, allow_nan=False, indent=1)
    print(f"  goods: {len(out)} damaging consumables ({n_actioned} mapped to a play action)")


if __name__ == "__main__":
    run()
