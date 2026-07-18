#!/usr/bin/env python3
"""
Local web UI for the optimizer — stdlib only, offline, single page.

    nr ui            start http://127.0.0.1:8377 and open the browser

Endpoints:
    GET  /              the single-page app (static/index.html)
    GET  /api/meta      characters, bosses, weapon types, toggles, actions, levels
    POST /api/collection  decode an uploaded save (raw .sl2 bytes) -> the player's
                          relics, cached under a token; body-in, JSON summary out
    POST /api/optimize  run the engine; body = the form as JSON (optional
                        `collection` token to run on an uploaded save)

Game data is loaded once at startup and shared read-only across requests.
Uploaded saves are decoded to relics in memory and never persisted.
"""

import json
import os
import re
import threading
import time
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from nightreign.io import savefile
from nightreign.optimize import runner
from nightreign.optimize.context import Context
from nightreign.resources import actions, curses, kits, relic_reference, weapon_types

STATIC = Path(__file__).parent / "static"

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8", ".json": "application/json",
    ".woff2": "font/woff2", ".webp": "image/webp", ".png": "image/png",
    ".svg": "image/svg+xml", ".webmanifest": "application/manifest+json",
}

# ---- uploaded-collection sessions -----------------------------------------
# A visitor uploads their save (POST /api/collection); we decode it to a relic
# list and cache it under an opaque token so subsequent /api/optimize calls
# stay tiny. The save itself is NEVER stored — only the decoded relics. The
# cache is bounded (TTL + cap, per process) so it can't grow without limit.
MAX_UPLOAD = 32 * 1024 * 1024        # a Nightreign save is ~19 MB
_COLLECTION_TTL = 2 * 3600           # seconds a decoded collection is kept
_COLLECTION_CAP = 50                 # max concurrent collections held
_COLLECTIONS = {}                    # token -> (created_ts, relics)
_COLLECTIONS_LOCK = threading.Lock()


def _store_collection(relics):
    """Cache a decoded collection, return its token. Evicts expired then oldest."""
    token = uuid.uuid4().hex
    now = time.time()
    with _COLLECTIONS_LOCK:
        for t in [t for t, (ts, _) in _COLLECTIONS.items() if now - ts > _COLLECTION_TTL]:
            _COLLECTIONS.pop(t, None)
        while len(_COLLECTIONS) >= _COLLECTION_CAP:
            _COLLECTIONS.pop(min(_COLLECTIONS, key=lambda t: _COLLECTIONS[t][0]), None)
        _COLLECTIONS[token] = (now, relics)
    return token


def _get_collection(token):
    """The relics for a token, or None if unknown/expired."""
    now = time.time()
    with _COLLECTIONS_LOCK:
        entry = _COLLECTIONS.get(token)
        if not entry or now - entry[0] > _COLLECTION_TTL:
            _COLLECTIONS.pop(token, None)
            return None
        return entry[1]


BUILD_HINT = (
    "<!doctype html><meta charset=utf-8>"
    "<title>EvilNightreign — build the UI</title>"
    "<body style='background:#05070c;color:#cbd6e6;font:16px/1.6 Georgia,serif;"
    "display:flex;min-height:100vh;align-items:center;justify-content:center;text-align:center'>"
    "<div><h1 style='color:#c9a24a;font-weight:600'>Interface not built</h1>"
    "<p>The SPA must be compiled once:</p>"
    "<pre style='color:#8fb6e6;background:#0d121d;padding:14px 18px;display:inline-block;text-align:left'>"
    "npm --prefix web install\nnpm --prefix web run build</pre>"
    "<p style='color:#6f7f99'>then restart <code>nr ui</code>.</p></div></body>"
).encode()


def _icon_url(data, kind, key):
    """`/assets/icons/<iconId>.webp` for a weapon_id / relic item_id, or None."""
    if key is None:
        return None
    iid = (data.get("icons") or {}).get(kind, {}).get(str(key))
    return f"/assets/icons/{iid}.webp" if iid else None


def _effect_icon_url(data, effect_id):
    """`/assets/effect-icons/<statusIconId>.webp` for a relic effect, or None."""
    sid = (data.get("effect_icons") or {}).get(str(effect_id))
    return f"/assets/effect-icons/{sid}.webp" if sid else None


# a relic effect that trades a real drawback for its upside (Nightfarer stat
# swaps, HP drains, "but not for self"). Their exact values live behind a game
# state we don't decode, so the optimizer scores them as neutral — we surface a
# warning instead of silently over-valuing the upside.
_TRADEOFF_RE = re.compile(
    r"\breduced\b[^.]*\b(vigor|strength|dexterity|intelligence|faith|mind|endurance|arcane)\b"
    r"|drains?\s+hp|but\s+not\s+for\s+self|boosts?\s+attack\s+but",
    re.I,
)


def _is_tradeoff(text):
    return bool(_TRADEOFF_RE.search(text or ""))


def _curse_note(key, active, scored):
    """Explanation of a Deep-of-Night curse's status in the score."""
    if not scored:
        return "Real curse, outside the damage/survival model (inflicted status / economy)"
    gate = (curses.spec(key) or {}).get("gate")
    if gate is None:
        return "Malus counted in the score (worst case: always active)"
    return ("Malus counted (situational play engaged)" if active
            else "Malus not counted here — only bites situationally (post-flask / critical HP)")


def _inactive_reason(ctx, effect_info, relic_entry, character):
    """Why an effect is inactive in this context (French), or None if it's active."""
    nf = relic_entry.get("nightfarer")
    if nf and nf != character:
        return f"Reserved for the character {nf}"
    state = effect_info.get("state_gate")
    if state and state not in ctx.toggles:
        return f"Requires the commitment: {TOGGLES.get(state, state)}"
    cond = effect_info.get("condition") or {}
    dim = cond.get("dimension")
    if dim == "weapon_type" and cond.get("label") != ctx.weapon_type:
        return f"Only with a weapon: {cond.get('label')}"
    if dim == "character" and cond.get("label") != character:
        return f"Only for {cond.get('label')}"
    if dim and dim != "weapon_type" and dim != "character" and dim not in ctx.toggles:
        return f"Requires the commitment: {TOGGLES.get(dim, dim)}"
    return "Inactive in this context"


def _synergy(b):
    """What to prioritise on weapons/items found in-run, derived from the build's
    OWN amplification (reliable — straight from the aggregated relic state, not
    from the disabled affix pool):
      * the damage type(s) the build amplifies most -> hunt that affinity / +type%
      * the status(es) the build applies -> hunt weapons with that buildup
      * the stat the build boosts most -> hunt weapons that scale with it
    """
    out = []
    mults = b.get("attack_multipliers") or {}
    ranked = sorted(((t, m) for t, m in mults.items() if m > 1.03), key=lambda x: -x[1])
    if ranked:
        spread = ranked[0][1] - ranked[-1][1]
        if spread < 0.02 and len(ranked) >= 4:
            out.append({"kind": "all", "mult": round(ranked[0][1], 3)})
        else:
            out += [{"kind": "damage", "type": t, "mult": round(m, 3)} for t, m in ranked[:3]]
    out += [{"kind": "status", "type": st} for st in (b.get("status") or {})]
    stats = {f: v for f, v in (b.get("stat_bonuses") or {}).items() if v > 0}
    if stats:
        f, v = max(stats.items(), key=lambda x: x[1])
        out.append({"kind": "stat", "type": f, "value": v})
    return out

TOGGLES = {
    "weak_point": "I aim for weak points (the target's weak-point multiplier)",
    "caster": "I cast spells (sorceries / incantations)",
    "low_hp": "I play at low HP",
    "situational": "Guard effects and effects vs afflicted enemies (poison, frost, bleed…)",
    "status_build": "Status-focused build",
    "starting_loadout": "Starting-loadout effects",
    "coop": "Co-op / allies",
    "triple_loadout": "I carry 3+ weapons of the same type",
}


def _curse_catalog(relics):
    """The Deep-of-Night curses present in a relic collection, for the acceptance
    list: [{key, label, group, scored, count}] + the per-cursed-relic key sets
    (so the UI can show a live 'N relics excluded' count)."""
    present, text_by_key, cursed_sets = {}, {}, []
    for r in relics:
        ks = []
        for e in r["effects"]:
            if e.get("is_curse") and e.get("key"):
                ks.append(e["key"])
                text_by_key.setdefault(e["key"], e.get("text"))
        if ks:
            cursed_sets.append(sorted(set(ks)))
            for k in set(ks):
                present[k] = present.get(k, 0) + 1
    catalog = []
    for k, n in present.items():
        label, group = curses.display(k, text_by_key.get(k))
        catalog.append({"key": k, "label": label, "group": group,
                        "scored": curses.spec(k) is not None, "count": n})
    catalog.sort(key=lambda c: (curses.group_rank(c["group"]), -c["count"], c["label"]))
    return catalog, cursed_sets


def _meta(data):
    heroes = []
    for name in runner.HERO_ORDER:
        base = (runner.HERO_ORDER.index(name) + 1) * 10000
        levels = sorted(
            data["hero_stats"][str(base + i)]["totalLevel"]
            for i in range(8)
            if str(base + i) in data["hero_stats"]
        )
        vessels = [v["name"] for v in data["vessels"].get(name, []) if v.get("obtainable")]
        if levels and vessels:
            heroes.append({"name": name, "levels": levels, "vessels": vessels})
    curse_catalog, cursed_sets = _curse_catalog(data["relics"])
    return {
        "characters": heroes,
        "bosses": list(data["nightlords"]),
        "weapon_types": sorted(set(weapon_types.WEPMOTION_TO_TYPE.values())
                               | set(weapon_types.CATALYST_TYPES)),
        "toggles": TOGGLES,
        "actions": actions.ACTION_CLASSES,
        "don_levels": [k for k in sorted(int(k) for k in data["scaling"]["deep_of_night"]) if k <= 5],
        "relic_count": len(data["relics"]),
        "curses": curse_catalog,
        "cursed_relic_curses": cursed_sets,
        # per-Nightfarer kit sheets (phase C): archetype presets + paradigms
        # for the future profile-first UI; figures carry their sources
        "kits": {name: {
            "passive": (kits.kit(name).get("passive") or {}).get("name"),
            "skill_paradigm": kits.kit(name).get("skill_paradigm"),
            "ultimate_paradigm": kits.kit(name).get("ultimate_paradigm"),
            "favored_sources": kits.kit(name).get("favored_sources", []),
            "archetypes": kits.kit(name).get("archetypes", []),
        } for name in runner.HERO_ORDER if kits.kit(name)},
    }


def _alt_spell(data, wid, play):
    """The resolved spell an alternative catalyst would use under the build's
    profile — so the user sees WHY one staff outranks another (the spell is
    the payload, not the stick)."""
    if wid is None:
        return None
    cast_actions = [a for a in play if a.startswith(("sorcery_", "incant_"))]
    if not cast_actions:
        return None
    entry = data.get("catalyst_spells", {}).get(str(wid))
    hit = runner._match_spell(data, entry, cast_actions[0])
    if not hit:
        return None
    _sid, spell, _guaranteed = hit
    return spell.get("name", "").replace("Sorcery: ", "").replace("Incantation: ", "")


def _serialize(result, data, character, toggles, don, count_debuffs=True):
    """JSON view of a gameplan; each relic effect is flagged active/inactive
    in the result's own context so the UI can gray out what does nothing."""
    ctx = Context(character, result["weapon_type"], frozenset(toggles), max(don, 1), count_debuffs)
    picks = []
    for (kind, color), relic in result["picks"]:
        effects = []
        for e in relic["effects"]:
            info = data["effects"].get(str(e["id"])) or {}
            active = ctx.effect_active(info, e)
            is_curse = bool(e.get("is_curse"))
            scored = is_curse and curses.spec(e.get("key")) is not None
            nf = e.get("nightfarer")
            effects.append({
                "text": e["text"],
                "active": active,
                "icon": _effect_icon_url(data, e["id"]),
                "reason": None if active else _inactive_reason(ctx, info, e, character),
                # only a character lock strikes the effect through; every other
                # inactive reason (unpicked toggle, weapon mismatch) is a soft mark.
                "char_locked": bool(nf and nf != character),
                # curses have real drawback handling — don't also flag the regex tradeoff
                "tradeoff": _is_tradeoff(e["text"]) and not is_curse,
                "curse": is_curse,
                "pair": e.get("pair"),
                "scored": scored,
                "note": _curse_note(e.get("key"), active, scored) if is_curse else None,
            })
        picks.append(
            {
                "kind": kind,
                "slot_color": color,
                "name": runner.pretty_name(relic["name"]),
                "color": relic["color"],
                "unique": relic["type"] == "UniqueRelic",
                "grid": relic.get("grid"),
                "grid_by_color": relic.get("grid_by_color"),
                "icon": _icon_url(data, "relics", relic.get("item_id")),
                "effects": effects,
            }
        )
    b = result["breakdown"]
    return {
        "score": result["score"],
        "absolute_offense": result.get("absolute_offense", b["offense"]),
        "absolute_dps": result.get("absolute_dps"),
        "weapon": result["weapon"],
        "weapon_icon": _icon_url(data, "weapons", result.get("weapon_id")),
        "weapon_type": result["weapon_type"],
        "weapon_alternatives": [
            {"name": name, "ratio": ratio, "icon": _icon_url(data, "weapons", wid),
             "spell": _alt_spell(data, wid, b.get("play") or {})}
            for (name, ratio, *rest) in (result.get("weapon_alternatives") or [])
            for wid in [rest[0] if rest else None]
        ],
        "vessel": result["vessel"],
        "targets": result["targets"],
        "picks": picks,
        "offense_ratio": b["offense_ratio"], "generic": result.get("generic", False),
        "ref_weapon": result.get("ref_weapon"),
        "cadence": result.get("cadence"),
        "survival_ratio": b["survival_ratio"],
        "attack_multipliers": b["attack_multipliers"],
        "stat_bonuses": b["stat_bonuses"],
        "status": b.get("status") or {},
        "affix_hunt": result.get("affix_hunt") or [],
        "synergy": _synergy(b),
        "actions_hit": b.get("actions_hit") or {},
        "top_effects": [
            {"key": runner.pretty_name(k), "mult": m, "action": a}
            for k, m, a in b.get("top_effects", [])
        ],
        "ignored_effects": [
            {"key": runner.pretty_name(k), "mult": m, "action": a}
            for k, m, a in b.get("ignored_effects", [])
        ],
        # multi-source engine surface (phase D/E UI): per-action sources with
        # their calibration flag, the FP clamp report, the kit factor, and the
        # talisman hunt (marginal-gain recommendations)
        "sources": b.get("sources") or {},
        "fp": b.get("fp") or {},
        "fp_pool": b.get("fp_pool"),
        "play": b.get("play") or {},
        "kit": result.get("kit"),
        "stamina": result.get("stamina"),
        "accessory_hunt": [
            {**a, "icon": _icon_url(data, "accessories", a.get("id"))}
            for a in (result.get("accessory_hunt") or [])
        ],
    }


def make_handler(data):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, body, ctype="application/json"):
            payload = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                # the SPA is built from web/ into static/app (npm run build)
                spa = STATIC / "app" / "index.html"
                if spa.exists():
                    return self._serve_file(spa)
                return self._send(200, BUILD_HINT, "text/html; charset=utf-8")
            if path == "/api/meta":
                return self._send(200, _meta(data))
            return self._serve_static(path)

        def _serve_file(self, target):
            ctype = CONTENT_TYPES.get(target.suffix, "application/octet-stream")
            self._send(200, target.read_bytes(), ctype)

        def _serve_static(self, path):
            """Serve a file under static/ (css, js, fonts, icons); no traversal."""
            target = (STATIC / path.lstrip("/")).resolve()
            root = STATIC.resolve()
            if root in target.parents and target.is_file():
                return self._serve_file(target)
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path == "/api/collection":
                return self._handle_collection()
            if self.path == "/api/optimize":
                return self._handle_optimize()
            return self._send(404, {"error": "not found"})

        def _handle_collection(self):
            """Decode an uploaded save (raw .sl2 bytes) into the player's relic
            collection and cache it under a token. The save is never stored."""
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > MAX_UPLOAD:
                return self._send(400, {"error": "empty or oversized save file"})
            raw = self.rfile.read(length)
            try:
                effect_by_id, text_by_key, item_by_id = data["reference"]
                records = savefile.read_relic_records_from_bytes(set(item_by_id), raw)
                relics = relic_reference.build_relics(
                    records, effect_by_id, text_by_key, item_by_id)
            except Exception as e:  # malformed / non-Nightreign file — never crash
                return self._send(400, {"error": f"could not read save ({type(e).__name__})"})
            if not relics:
                return self._send(400, {"error": "no relics found in this save"})
            catalog, cursed_sets = _curse_catalog(relics)
            token = _store_collection(relics)
            return self._send(200, {"token": token, "relic_count": len(relics),
                                    "curses": catalog, "cursed_relic_curses": cursed_sets})

        def _handle_optimize(self):
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length) or b"{}")
                # per-request collection: an uploaded save's token swaps the relic
                # list (shallow copy — the ThreadingHTTPServer shares `data`, so
                # never mutate the global in place). No token = demo collection.
                req_data = data
                token = req.get("collection")
                if token:
                    relics = _get_collection(token)
                    if relics is None:
                        return self._send(410, {"error": "collection expired — re-import your save"})
                    req_data = {**data, "relics": relics}
                play = {
                    a: float(w)
                    for a, w in (req.get("play") or {}).items()
                    if float(w) > 0
                } or {"melee": 1.0}
                total = sum(play.values())
                play = {a: w / total for a, w in play.items()}
                results = runner.optimize(
                    req["character"],
                    boss=req.get("boss") or None,
                    weapon_type=req.get("weapon_type") or None,
                    level=int(req.get("level", 15)),
                    weight=float(req.get("weight", 0.5)),
                    don=int(req.get("don", 0)),
                    toggles=tuple(req.get("toggles") or ()),
                    beam_k=int(req.get("beam", 12)),
                    top=int(req.get("top", 3)),
                    max_weapon_level=int(req.get("max_weapon_level", 25)),
                    play=play,
                    data=req_data,
                    count_debuffs=bool(req.get("count_debuffs", True)),
                    refused_curses=tuple(req.get("refused_curses") or ()),
                )
                toggles = req.get("toggles") or ()
                count_debuffs = bool(req.get("count_debuffs", True))
                self._send(
                    200,
                    {
                        "mode": ("generic" if req.get("weapon_type") == "__generic__"
                             else "fixed" if req.get("weapon_type") else "auto"),
                        "results": [
                            _serialize(
                                r,
                                req_data,
                                (
                                    results[0]["character"]
                                    if results
                                    else req["character"]
                                ),
                                toggles,
                                int(req.get("don", 0)),
                                count_debuffs,
                            )
                            for r in results
                        ],
                    },
                )
            except SystemExit as e:
                self._send(400, {"error": str(e)})
            except Exception as e:  # surface the reason instead of a dead page
                self._send(500, {"error": f"{type(e).__name__}: {e}"})

    return Handler


def serve(port=8377, open_browser=True):
    # Host/port are env-overridable so the same command runs locally (default
    # 127.0.0.1, private) and on a host like Render (HOST=0.0.0.0, PORT injected).
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", port))
    print("loading game data ...")
    data = runner.load_data()
    # id->name/semantics maps for decoding uploaded saves (POST /api/collection)
    data["reference"] = relic_reference.load()
    server = ThreadingHTTPServer((host, port), make_handler(data))
    url = f"http://{host}:{port}"
    print(f"nr ui ready on {url}  (Ctrl+C to stop)")
    if open_browser and host in ("127.0.0.1", "localhost"):
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    return 0
