#!/usr/bin/env python3
"""Data invariants the math doc (optimizer_mathematical_formulation.md) relies on — machine-checked.

The proofs in S2/S3 are stated on the *per-key* model. That model is only valid
because the curated data satisfies the invariants below; re-run this script
whenever `data/curated/` is regenerated (`nr data`). Exits non-zero on failure.

  INV-1  `stacks` is a function of the effect KEY (never mixed across copies).
         It is NOT a function of the group: some groups mix flags across
         levels, so any per-group sigma is wrong on real data.
  INV-2  Within a group, key <-> (group, level) is a bijection carrying a
         single magnitude — "the effect of group g at level l" is well defined.
  INV-3  Contributions to the tracked multiplicative fields are nonnegative in
         log space (no *AttackRate in (0,1), no *DamageCutRate > 1) on any
         non-debuff effect. Deep-of-Night CURSES deliberately break this (they
         are the malus); they are excluded here and handled signed by the
         aggregation (dominance iterates the key union, search leans on beam +
         exhaustive rather than the greedy monotonicity bound).

Known quirks (reported, not fatal — the per-key model absorbs them):
  Q-1  A few keys carry several distinct magnitudes across their ids; the
       sigma=0 aggregation takes the max over copies, which keeps Agg a
       well-defined set function.
  Q-2  A relic can carry the SAME key several times, so sigma=1 profile
       entries must SUM intra-relic copies (a max would under-count).
"""
import collections
import json
import sys

from nightreign.resources import constants

RELICS = json.load(open(constants.DATA_CURATED / "relics.json"))
EFFECTS = json.load(open(constants.DATA_CURATED / "effects.json"))

ATTACK_FIELDS = ["physicsAttackRate", "magicAttackRate", "fireAttackRate",
                 "thunderAttackRate", "darkAttackRate"]

failures = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        failures.append(name)


print(f"Invariants on {len(RELICS)} owned relics\n")

# ---- INV-1: stacks is per-key; and demonstrably NOT per-group ----
stacks_by_key = collections.defaultdict(set)
stacks_by_group = collections.defaultdict(set)
for r in RELICS:
    for e in r["effects"]:
        stacks_by_key[e["key"]].add(bool(e.get("stacks")))
        if e.get("group"):
            stacks_by_group[e["group"]].add(bool(e.get("stacks")))
mixed_keys = [k for k, s in stacks_by_key.items() if len(s) > 1]
mixed_groups = [g for g, s in stacks_by_group.items() if len(s) > 1]
check("INV-1 stacks uniform per key", not mixed_keys, f"{len(stacks_by_key)} keys")
print(f"        (evidence sigma is per-key, not per-group: {len(mixed_groups)}/"
      f"{len(stacks_by_group)} groups mix flags across levels: {mixed_groups})")

# ---- INV-2: (group, level) <-> key, single magnitude ----
gl_keys = collections.defaultdict(set)
gl_mags = collections.defaultdict(set)
key_gl = collections.defaultdict(set)
for r in RELICS:
    for e in r["effects"]:
        if e.get("group"):
            gl = (e["group"], e.get("level"))
            gl_keys[gl].add(e["key"])
            key_gl[e["key"]].add(gl)
            info = EFFECTS.get(str(e["id"])) or {}
            gl_mags[gl].add(json.dumps(info.get("magnitude") or {}, sort_keys=True))
bad_gl = [gl for gl, ks in gl_keys.items() if len(ks) > 1] \
       + [k for k, gls in key_gl.items() if len(gls) > 1] \
       + [gl for gl, ms in gl_mags.items() if len(ms) > 1]
check("INV-2 key <-> (group, level), single magnitude", not bad_gl,
      f"{len(gl_keys)} pairs")

# ---- INV-3: v >= 0 on tracked multiplicative fields ----
cut_fields = sorted({f for info in EFFECTS.values()
                     for f in (info.get("magnitude") or {})
                     if f.endswith("DamageCutRate")})
violations = []
for r in RELICS:
    for e in r["effects"]:
        info = EFFECTS.get(str(e["id"])) or {}
        if info.get("is_debuff"):
            continue  # curses carry the malus by design (see INV-3 doc above)
        m = info.get("magnitude") or {}
        for f in ATTACK_FIELDS:
            v = m.get(f)
            if isinstance(v, (int, float)) and 0 < v < 1:
                violations.append((r["name"], e["key"], f, v))
        for f in cut_fields:
            v = m.get(f)
            if isinstance(v, (int, float)) and v > 1:
                violations.append((r["name"], e["key"], f, v))
check("INV-3 no negative log-contribution on tracked fields", not violations,
      f"{len(ATTACK_FIELDS)} attack + {len(cut_fields)} cut fields")
for v in violations[:5]:
    print(f"        offending: {v}")

# ---- Q-1: keys with several magnitudes (max semantics required) ----
key_mags = collections.defaultdict(set)
for r in RELICS:
    for e in r["effects"]:
        info = EFFECTS.get(str(e["id"])) or {}
        key_mags[e["key"]].add(json.dumps(info.get("magnitude") or {}, sort_keys=True))
multi = sorted(k for k, ms in key_mags.items() if len(ms) > 1)
print(f"  Q-1   keys with several magnitudes across ids: {len(multi)} {multi}")

# ---- Q-2: intra-relic duplicate keys (sum semantics required for sigma=1) ----
dups = []
for r in RELICS:
    cnt = collections.Counter(e["key"] for e in r["effects"])
    for k, c in cnt.items():
        if c > 1:
            dups.append((r["name"], k, c, bool(stacks_by_key[k] == {True})))
print(f"  Q-2   relics carrying the same key several times: {len(dups)} {dups}")

# ---- stat: unresolved effect ids (skipped by every experiment) ----
unresolved = sum(1 for r in RELICS for e in r["effects"]
                 if str(e["id"]) not in EFFECTS)
total = sum(len(r["effects"]) for r in RELICS)
print(f"  info  effect instances without a resolved definition: {unresolved}/{total}")

# ---- RES-*: multi-source resolvability (ROADMAP phase A acceptance) ----
# Every damage source the engine may score must resolve end-to-end in the
# curated data; a broken chain must fail HERE, not silently score zero.
print()
MAGIC_PATH = constants.DATA_CURATED / "magic.json"
if MAGIC_PATH.exists():
    MAGIC = json.load(open(MAGIC_PATH))
    CUSTOM = json.load(open(constants.DATA_RAW / "custom_weapons.json"))
    WEAPONS = json.load(open(constants.DATA_RAW / "weapons.json"))
    CHARACTERS = json.load(open(constants.DATA_CURATED / "characters.json"))

    # RES-1: every rolled catalyst spell resolves to a magic.json entry
    bad_spells = [(cid, s["id"]) for cid, c in CUSTOM.items()
                  for s in (c.get("spells") or []) if str(s["id"]) not in MAGIC]
    n_cat = sum(1 for c in CUSTOM.values() if c.get("spells"))
    check("RES-1 every rolled catalyst spell resolves", not bad_spells,
          f"{n_cat} catalyst instances")

    # RES-2: every character skill/ultimate (except -1) is a real hidden
    # weapon with an attack base (Executor's ultimate is a transformation)
    bases = ("attackBasePhysics", "attackBaseMagic", "attackBaseFire",
             "attackBaseThunder", "attackBaseDark")
    bad_skills = []
    for name, c in CHARACTERS.items():
        for field in ("skill_weapon", "ultimate_weapon"):
            wid = c.get(field)
            if wid in (None, -1):
                continue
            row = WEAPONS.get(str(wid)) or {}
            if not any((row.get(f) or 0) > 0 for f in bases):
                bad_skills.append((name, field, wid))
    check("RES-2 every character skill/ult is a damaging hidden weapon",
          not bad_skills, f"{len(CHARACTERS)} characters")
    for b in bad_skills[:5]:
        print(f"        offending: {b}")

    # RES-3: every damaging spell carries a play-profile action class
    bad_actions = [sid for sid, m in MAGIC.items()
                   if "damage" in m and not str(m.get("action", "")).startswith(("sorcery_", "incant_"))]
    check("RES-3 every damaging spell has a cast action class", not bad_actions,
          f"{sum(1 for m in MAGIC.values() if 'damage' in m)} damaging spells")
else:
    print("  skip  RES-* multi-source invariants (magic.json not generated — run `nr data magic`)")

sys.exit(1 if failures else 0)
