# TODO — what's left

*As of 2026-07-18. The foundation (attack rating, spell damage, FP, stamina pool, statuses, multi-source selection, relics, per-user save import) is calibrated and tested. What follows is the remaining backlog, by category.*

## 🎯 Remaining in-game measurements (checklist in docs/calibration.md)

- [ ] **Stamina regen** (empty→full bar, timed) — the ONLY unknown for the full sustain constraint. Pool and per-attack costs are already in place.
- [ ] **Linear vs defense multiplier** — one bare R1 on a known-defense dummy. Greatsword (125/126) and spells (141) say linear; a dagger R1 at 85 (unknown target) casts doubt. Settles the whole melee model.
- [ ] **One incantation (seal / Faith)** — confirm that `SPELL_SCALING_CORRECTION` applies to incantations (currently assumed).
- [ ] **Hit counts for `assumed` multi-hit spells** (Elden Stars, Glintstone Stars, Star Shower…) + **Night Comet base** (overestimated) + Rancorcall / Stars of Ruin (already measured, to apply).
- [ ] **Real NR bleed %**, **frost proc HP**, **sleep / madness** — low priority.

## 🔧 Data work (no measurement, pure decoding)

- [ ] **ItemLotParam → the catalyst slot-2 pool** (we know slot-1 is fixed and slot-2 is a roll, but the exact roll pool isn't decoded).
- [ ] **Rolled weapon-art payloads** (SwordArtsTable → drop; like the affixes). Re-wire `data["sword_arts"]`.
- [ ] **Weapon affixes**: re-enable with a reliable player-visible source (disabled since 07-16).
- [ ] weaponLevel 25 variants (settle via loot tables).

## ⚙️ Engine features (data ready, not wired)

- [ ] **Stamina constraint** (sustained DPS = min(cadence, regen/cost)) — as soon as regen is measured.
- [ ] **Spell cadence** — fast spells (Carian Slicer, Pebble) are undervalued for lack of `rate_hz`. Model cast time (animation_durations extracted).
- [ ] **Ultimate charge economy** (`ultChargeB` extracted; charge→time formula to establish).
- [ ] **Stagger / poise axis** (`saWeaponDamage` / ToughnessParam extracted, never scored).
- [ ] **Party scaling** (MultiPlayCorrectionParam extracted).
- [ ] **Ammunition** (arrow elemental share), **two-handing / power-stance** (after measurement), **per-level rarity gates**.
- [ ] **Generalist over the 200 NPCs** (npcs.json extracted, unused — perf work).

## 🖥️ UI/UX

- [x] **English pass** — all chrome in English (game data already English). *(done 07-17)*
- [x] **"How it works" modal** — full-viewport, explains how the engine reached each result (score, weapon, guaranteed/rolled spells, sources, relics, stamina, FP, calibrated vs theoretical, not-modeled). Declutters the left column. *(done 07-17 — `web/src/components/HowItWorks.tsx`, 7 sections)*
- [x] **Save import** — visitors upload their `NR0000.sl2`; the optimizer runs on their own relics. Landing overlay (demo vs import), server-side decode, session token. *(done 07-18)*
- [x] **Searchable comboboxes** (play profile, weapon type), **themed tooltip**, **favicon**, **objective slider fix**, **talisman gating** (conditional talismans excluded). *(done 07-18)*

## Locked in (don't redo)

AR 0.596 · SPELL_FACTOR 0.596 · SPELL_SCALING_CORRECTION 0.9027 · catalyst ladders · linear stat interpolation · FP = 45 + 5×Mind · Stamina = 48 + 2×END · poison/rot/frost · slot-1 guaranteed vs slot-2 roll · physical subtypes · bows (flat) · channeled · consumables · talismans (gated ones excluded) · kits · curses · universal effects.json (1117) · vessels `obtainable` · per-user save import.
