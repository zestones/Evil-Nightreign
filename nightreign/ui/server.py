#!/usr/bin/env python3
"""
Local web UI for the optimizer — stdlib only, offline, single page.

    nr ui            start http://127.0.0.1:8377 and open the browser

Endpoints:
    GET  /            the single-page app (static/index.html)
    GET  /api/meta    characters, bosses, weapon types, toggles, actions, levels
    POST /api/optimize  run the engine; body = the form as JSON

Game data is loaded once at startup and shared read-only across requests.
"""

import json
import re
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from nightreign.optimize import runner
from nightreign.optimize.context import Context
from nightreign.resources import actions, weapon_types

STATIC = Path(__file__).parent / "static"

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8", ".json": "application/json",
    ".woff2": "font/woff2", ".webp": "image/webp", ".png": "image/png",
    ".svg": "image/svg+xml", ".webmanifest": "application/manifest+json",
}


BUILD_HINT = (
    "<!doctype html><meta charset=utf-8>"
    "<title>EvilNightreign — build the UI</title>"
    "<body style='background:#05070c;color:#cbd6e6;font:16px/1.6 Georgia,serif;"
    "display:flex;min-height:100vh;align-items:center;justify-content:center;text-align:center'>"
    "<div><h1 style='color:#c9a24a;font-weight:600'>Interface non construite</h1>"
    "<p>La SPA doit être compilée une fois :</p>"
    "<pre style='color:#8fb6e6;background:#0d121d;padding:14px 18px;display:inline-block;text-align:left'>"
    "npm --prefix web install\nnpm --prefix web run build</pre>"
    "<p style='color:#6f7f99'>puis relance <code>nr ui</code>.</p></div></body>"
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


def _inactive_reason(ctx, effect_info, relic_entry, character):
    """Why an effect is inactive in this context (French), or None if it's active."""
    nf = relic_entry.get("nightfarer")
    if nf and nf != character:
        return f"Réservé au personnage {nf}"
    state = effect_info.get("state_gate")
    if state and state not in ctx.toggles:
        return f"Nécessite l'engagement : {TOGGLES.get(state, state)}"
    cond = effect_info.get("condition") or {}
    dim = cond.get("dimension")
    if dim == "weapon_type" and cond.get("label") != ctx.weapon_type:
        return f"Seulement avec une arme : {cond.get('label')}"
    if dim == "character" and cond.get("label") != character:
        return f"Seulement pour {cond.get('label')}"
    if dim and dim != "weapon_type" and dim != "character" and dim not in ctx.toggles:
        return f"Nécessite l'engagement : {TOGGLES.get(dim, dim)}"
    return "Inactif dans ce contexte"


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
    "caster": "Je lance des sorts (sorcelleries / incantations)",
    "low_hp": "Je joue à PV bas",
    "situational": "Effets situationnels (garde, ennemis affligés)",
    "status_build": "Build orienté statuts",
    "starting_loadout": "Effets de loadout de départ",
    "coop": "Coop / alliés",
    "triple_loadout": "Je porte 3+ armes du même type",
}


def _meta(data):
    heroes = []
    for name in runner.HERO_ORDER:
        base = (runner.HERO_ORDER.index(name) + 1) * 10000
        levels = sorted(
            data["hero_stats"][str(base + i)]["totalLevel"]
            for i in range(8)
            if str(base + i) in data["hero_stats"]
        )
        vessels = [v["name"] for v in data["vessels"].get(name, []) if v.get("owned")]
        if levels and vessels:
            heroes.append({"name": name, "levels": levels, "vessels": vessels})
    return {
        "characters": heroes,
        "bosses": list(data["nightlords"]),
        "weapon_types": sorted(set(weapon_types.WEPMOTION_TO_TYPE.values())),
        "toggles": TOGGLES,
        "actions": actions.ACTION_CLASSES,
        "don_levels": [k for k in sorted(int(k) for k in data["scaling"]["deep_of_night"]) if k <= 5],
        "relic_count": len(data["relics"]),
    }


def _serialize(result, data, character, toggles, don):
    """JSON view of a gameplan; each relic effect is flagged active/inactive
    in the result's own context so the UI can gray out what does nothing."""
    ctx = Context(character, result["weapon_type"], frozenset(toggles), max(don, 1))
    picks = []
    for (kind, color), relic in result["picks"]:
        effects = []
        for e in relic["effects"]:
            info = data["effects"].get(str(e["id"])) or {}
            active = ctx.effect_active(info, e)
            effects.append({
                "text": e["text"],
                "active": active,
                "icon": _effect_icon_url(data, e["id"]),
                "reason": None if active else _inactive_reason(ctx, info, e, character),
                "tradeoff": _is_tradeoff(e["text"]),
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
        "weapon_alternatives": result.get("weapon_alternatives") or [],
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
            if self.path != "/api/optimize":
                return self._send(404, {"error": "not found"})
            try:
                length = int(self.headers.get("Content-Length", 0))
                req = json.loads(self.rfile.read(length) or b"{}")
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
                    data=data,
                )
                toggles = req.get("toggles") or ()
                self._send(
                    200,
                    {
                        "mode": ("generic" if req.get("weapon_type") == "__generic__"
                             else "fixed" if req.get("weapon_type") else "auto"),
                        "results": [
                            _serialize(
                                r,
                                data,
                                (
                                    results[0]["character"]
                                    if results
                                    else req["character"]
                                ),
                                toggles,
                                int(req.get("don", 0)),
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
    print("loading game data ...")
    data = runner.load_data()
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(data))
    url = f"http://127.0.0.1:{port}"
    print(f"nr ui ready on {url}  (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
    return 0
