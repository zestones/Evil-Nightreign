#!/usr/bin/env python3
"""Resolve every Magic row into a scored spell catalog.

Chain (validated on the params 2026-07-17): Magic.refId1/refId2 -> Bullet ->
atkId_Bullet -> AtkParam_Pc = the spell's real per-type damage, stance damage
and on-hit status buildup. Two complementary paths cover every spell shape:
the bullet TREE is authoritative when it resolves damage (it carries the
multi-hit structure — Phalanx blades, spawners), and `Magic.atkParamId` is
the fallback for DEFERRED casts whose projectile fires from a summoned
construct rather than the cast bullet (e.g. 4390 Magic Glintblade: the blade
bullet has no atkId, the damage lives on atkParamId=43900 -> 182 magic).
Some rows have neither (atkParamId=-1 AND a damage-less tree): pure utility.

Hits per cast resolve params-only through the bullet tree: `numShoot`
(fan-out), `HitBulletID` (on-hit child), `intervalCreate*` (periodic spawner
over the bullet's `life`). A spell whose structure cannot be resolved keeps
its direct hits with confidence "assumed" — flagged for the calibration
session, never invented (docs/roadmap.md phase E doctrine).

Spell school = `subCategory1`, the SAME id space that gates relic effects
(actions.SUBCATEGORY_ACTIONS — verified: 4390 Glintblade Phalanx -> 3, 4100
Rock Sling -> 4). Unmapped schools still benefit from the sorcery_any /
incant_any umbrellas via their `action` class.

Output: data/curated/magic.json  {spell_id: {name, action, school, incant,
fp, fp_charge, stamina, damage, super_armor, status, hits, confidence,
charged: {...}, requirements}}
"""
import json
import math

from nightreign.io import paramdef, regulation
from nightreign.resources import constants, statuses
from nightreign.resources.actions import SUBCATEGORY_ACTIONS

ATK_FIELDS = {"atkPhys": "phys", "atkMag": "mag", "atkFire": "fire",
              "atkThun": "thunder", "atkDark": "dark"}
MAX_DEPTH = 4          # bullet recursion guard (chains are shallow in practice)


def _san(v):
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v):
            return None
        return round(v, 6)
    return v


def _atk_payload(atk_row, speffects):
    """(damage, super_armor, status) carried by one AtkParam_Pc row."""
    damage = {out: atk_row[f] for f, out in ATK_FIELDS.items() if atk_row.get(f, 0) > 0}
    status = {}
    # AtkParam rows may attach status via their own spEffectId0-4 (rare for
    # spells; the common carrier is the Bullet's spEffectIDForShooter/../4)
    return damage, _san(atk_row.get("atkSuperArmor", 0)) or 0, status


def _bullet_status(bullet, speffects):
    """On-hit status buildup attached to a bullet (spEffectId0-4 -> SpEffect)."""
    out = {}
    for i in range(5):
        sp = speffects.get(bullet.get(f"spEffectId{i}"))
        if not sp:
            continue
        for field, status in statuses.BUILDUP_FIELDS.items():
            v = sp.get(field)
            if isinstance(v, (int, float)) and v > 0:
                out[status] = out.get(status, 0) + v
    return out


def _new_acc():
    """Two-channel accumulator: `solo` nodes hit independently; `shared`
    nodes participate in the game's shared-hit-list re-hit window (a single
    target can only be re-hit every dmgHitRecordLifeTime seconds across the
    WHOLE volley) and are windowed in _resolve_cast."""
    return {"solo": {"damage": {}, "sa": 0.0, "status": {}, "hits": 0.0},
            "shared": {"damage": {}, "sa": 0.0, "status": {}, "hits": 0.0},
            "rehits": set(), "duration": 0.0, "conf": "params"}


def _acc_add(acc, chan, damage, sa, status, hits, times=1.0):
    c = acc[chan]
    for t, v in damage.items():
        c["damage"][t] = c["damage"].get(t, 0) + v * times
    c["sa"] += sa * times
    for k, v in status.items():
        c["status"][k] = c["status"].get(k, 0) + v * times
    c["hits"] += hits * times


def _resolve_bullet(bid, bullets, atk, speffects, depth=0):
    """Aggregate a bullet tree per ONE cast into a two-channel accumulator.
    Only nodes that resolve to a damaging AtkParam row count as hits."""
    acc = _new_acc()
    b = bullets.get(bid)
    if not b or depth > MAX_DEPTH:
        if b:
            acc["conf"] = "assumed"
        return acc
    shots = max(1, b.get("numShoot") or 1)
    acc["duration"] = b.get("life") or 0.0

    a = atk.get(b.get("atkId_Bullet"))
    if a:
        d, s, _ = _atk_payload(a, speffects)
        if d:
            shared = bool(b.get("isUseSharedHitList")) and (b.get("dmgHitRecordLifeTime") or 0) > 0
            chan = "shared" if shared else "solo"
            _acc_add(acc, chan, d, s, _bullet_status(b, speffects), 1)
            if shared:
                acc["rehits"].add(b["dmgHitRecordLifeTime"])

    def _merge_child(child_bid, times=1.0):
        m = _resolve_bullet(child_bid, bullets, atk, speffects, depth + 1)
        for chan in ("solo", "shared"):
            c = m[chan]
            _acc_add(acc, chan, c["damage"], c["sa"], c["status"], c["hits"], times)
        acc["rehits"] |= m["rehits"]
        acc["duration"] += m["duration"]
        acc["conf"] = _worse(acc["conf"], m["conf"])

    # child spawned on hit (e.g. explosion after impact, chained sequence)
    child = b.get("HitBulletID")
    if child and child > 0 and child != bid:
        _merge_child(child)

    # periodic spawner over the bullet's life (volleys, rains)
    ib = b.get("intervalCreateBulletId")
    if ib and ib > 0 and ib != bid:
        tmin = b.get("intervalCreateTimeMin") or 0
        tmax = b.get("intervalCreateTimeMax") or 0
        life = b.get("life") or 0
        interval = (tmin + tmax) / 2.0
        if interval > 0 and life > 0:
            _merge_child(ib, times=life / interval)
            acc["conf"] = _worse(acc["conf"], "params_interval")
        else:
            # unbounded spawner: never fabricate a tick count — the single
            # emission stands and the spell is flagged for calibration
            acc["conf"] = _worse(acc["conf"], "assumed")

    if shots > 1:
        for chan in ("solo", "shared"):
            c = acc[chan]
            c["damage"] = {t: v * shots for t, v in c["damage"].items()}
            c["status"] = {k: v * shots for k, v in c["status"].items()}
            c["sa"] *= shots
            c["hits"] *= shots
    return acc


_CONF_RANK = {"params": 0, "params_deferred": 1, "params_interval": 1, "assumed": 2}


def _worse(a, b):
    return a if _CONF_RANK[a] >= _CONF_RANK[b] else b


def _channel_emission(bid, bullets, atk, depth=0):
    """(per_emission_damage, rehit_period) of the first DAMAGING bullet with a
    re-hit period in the tree — the sustained emission of a channeled cast.
    Damage counts the full emission (numShoot projectiles), consistent with
    the multi-hit treatment elsewhere. (0-damage or no re-hit -> ({}, 0))."""
    b = bullets.get(bid)
    if not b or depth > MAX_DEPTH:
        return {}, 0.0
    a = atk.get(b.get("atkId_Bullet"))
    rehit = b.get("dmgHitRecordLifeTime") or 0.0
    if a and rehit > 0:
        shots = max(1, b.get("numShoot") or 1)
        damage = {out: a[f] * shots for f, out in ATK_FIELDS.items() if a.get(f, 0) > 0}
        if damage:
            return damage, rehit
    for f in ("HitBulletID", "intervalCreateBulletId"):
        child = b.get(f)
        if child and child > 0 and child != bid:
            d, r = _channel_emission(child, bullets, atk, depth + 1)
            if r:
                return d, r
    return {}, 0.0


def _resolve_cast(magic_row, ref_field, bullets, atk, speffects, atk_fallback=None):
    """One cast slot (refId1 = normal, refId2 = charged) -> payload dict.

    atk_fallback: the Magic row's atkParamId row, used when the bullet tree
    resolves NO damage (deferred-construct spells) — never added on top of a
    resolved tree (Pebble's atkParamId is the same row its tree reaches;
    summing both would double-count).

    SINGLE-TARGET correction (the game's own mechanism, not a heuristic):
    when every damaging node shares ONE AtkParam row and carries
    isUseSharedHitList + dmgHitRecordLifeTime, the whole volley shares a
    re-hit window — one target can only be hit every R seconds, so
    hits_on_target = min(emitted, 1 + exposure/R). Glintstone Arc (54
    projectiles, R=99s) collapses to 1; Triple Rings (R=0.9s over ~2.7s)
    to ~3. Heterogeneous trees (mixed AtkParam rows) are one-shot sequences
    and keep the emitted sum."""
    rid = magic_row.get(ref_field)
    damage, sa, status, hits, conf = ({}, 0.0, {}, 0, "params")
    if rid and rid > 0:
        acc = _resolve_bullet(rid, bullets, atk, speffects)
        conf = acc["conf"]
        solo, shared = acc["solo"], acc["shared"]
        # window the shared channel: hits_on_target = min(emitted, 1 + T/R)
        sh_damage, sh_sa, sh_status, sh_hits = (shared["damage"], shared["sa"],
                                                shared["status"], shared["hits"])
        if sh_hits > 1 and acc["rehits"]:
            window = 1 + int(acc["duration"] / min(acc["rehits"]))
            if window < sh_hits:
                scale = window / sh_hits
                sh_damage = {t: v * scale for t, v in sh_damage.items()}
                sh_status = {k: v * scale for k, v in sh_status.items()}
                sh_sa *= scale
                sh_hits = window
        damage = dict(solo["damage"])
        for t, v in sh_damage.items():
            damage[t] = damage.get(t, 0) + v
        status = dict(solo["status"])
        for k, v in sh_status.items():
            status[k] = status.get(k, 0) + v
        sa = solo["sa"] + sh_sa
        hits = solo["hits"] + sh_hits
    if not damage and atk_fallback:
        d, s, _ = _atk_payload(atk_fallback, speffects)
        if d:
            damage, sa, hits = d, s, 1
            conf = "params_deferred"   # per-hit exact; fire count assumed 1
    if not damage and not status:
        return None  # buff/utility cast — legitimately no damage payload
    out = {"damage": {t: _san(v) for t, v in damage.items()},
           "hits": _san(hits), "confidence": conf}
    if sa:
        out["super_armor"] = _san(sa)
    if status:
        out["status"] = {k: _san(v) for k, v in status.items()}
    return out


def run():
    constants.DATA_CURATED.mkdir(parents=True, exist_ok=True)
    print("  magic: reading regulation.bin ...")
    params = regulation.load_params()

    def decode(name, defname=None):
        _, layout, _ = paramdef.parse_def(constants.DEFS / f"{defname or name}.xml")
        return paramdef.decode_param(params[name], layout)

    magic = decode("Magic")
    bullets = decode("Bullet")
    atk = decode("AtkParam_Pc", "AtkParam")
    speffects = decode("SpEffectParam")
    names = {e["ID"]: e["Entries"][0]
             for e in json.load(open(constants.NAMES / "Magic.json"))["Entries"]
             if e.get("Entries") and e["Entries"][0]}

    out = {}
    n_damage = n_utility = n_assumed = 0
    for rid, m in magic.items():
        if rid in (90, 999999999):   # placeholder rows
            continue
        name = names.get(rid, f"spell {rid}")
        school_id = m.get("subCategory1") or 0
        school = SUBCATEGORY_ACTIONS.get(school_id)
        incant = name.startswith("Incantation")
        # play-profile action class of a cast: the mapped school, else the
        # family umbrella (still buffed by generic sorcery/incant relics)
        action = school or ("incant_any" if incant else "sorcery_any")
        entry = {
            "name": name, "action": action, "incant": incant,
            "school_id": school_id or None,
            "fp": m.get("mp") or 0, "stamina": m.get("stamina") or 0,
        }
        if m.get("mp_charge"):
            entry["fp_charge"] = m["mp_charge"]
        reqs = {k: v for k, v in (("int", m.get("requirementIntellect")),
                                  ("fai", m.get("requirementFaith"))) if v}
        if reqs:
            entry["requirements"] = reqs
        fallback = atk.get(m.get("atkParamId") or -1)
        cast = _resolve_cast(m, "refId1", bullets, atk, speffects, atk_fallback=fallback)
        if cast:
            entry.update(cast)
            n_damage += 1
            if cast["confidence"] == "assumed":
                n_assumed += 1
        else:
            n_utility += 1
        charged = _resolve_cast(m, "refId2", bullets, atk, speffects)
        if charged:
            entry["charged"] = charged
        # CHANNELED casts (hold-to-sustain): consumeLoopMP_forMenu is the FP
        # drain per second (cross-validated: Comet Azur 40 + 10/s matches the
        # in-game display); the damaging bullet's dmgHitRecordLifeTime is the
        # re-hit period, so sustained DPS is fully params-resolved. The
        # per-cast `damage`/`hits` above describe one emission only.
        loop_mp = m.get("consumeLoopMP_forMenu") or 0
        if loop_mp > 0:
            channel = {"fp_per_s": loop_mp}
            # the sustained emission may sit on refId1 (beams: Comet Azur) or
            # refId2 (breaths: Dragonfire's spray — refId1 is a 0.05s primer)
            damage, rehit = {}, 0.0
            for ref in ("refId1", "refId2"):
                damage, rehit = _channel_emission(m.get(ref) or -1, bullets, atk)
                if rehit:
                    break
            if rehit > 0 and damage:
                hits_per_s = 1.0 / rehit
                channel["hits_per_s"] = _san(hits_per_s)
                channel["damage_per_s"] = {t: _san(v * hits_per_s)
                                           for t, v in damage.items()}
                channel["confidence"] = "params"
            else:
                channel["confidence"] = "assumed"   # drain known, tick rate not
            entry["channel"] = channel
        out[rid] = entry

    json.dump(out, open(constants.DATA_CURATED / "magic.json", "w"),
              ensure_ascii=False, allow_nan=False, indent=1)
    print(f"  magic: {len(out)} spells — {n_damage} damaging "
          f"({n_assumed} unresolved hit structure), {n_utility} buff/utility")


if __name__ == "__main__":
    run()
