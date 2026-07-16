# Optimizer — specification

Reference spec for the relic build optimizer. Everything below is grounded in the data extracted under `data/curated/` (all real in-game values).

## Mission

From the relics you own, produce the strongest playable **gameplan** for a character against a target (or the whole game): what to equip now, what to hunt for in-game, and how to play it.

## Inputs

Three distinct categories.

### A. Context (the situation, not a build choice)

- **Character** (Nightfarer)
- **Target**: one specific Nightlord, **or** generalist (all NPCs / unknown Deep of Night boss)
- **Deep of Night level** (1-7) — scales enemy damage and HP
- **Party**: solo / 2-player / 3-player (co-op)

### B. Objective weights (what you optimize for)

- **Offense ↔ Defense** slider

### C. Constraints / toggles (fixed by you, or suggested by the optimizer — "both modes")

- **Weapon type** (one of 33 categories)
- **Affinity** (physical / fire / lightning / magic / holy / cold / poison / blood)
- **Vessel** (chalice)
- **Playstyle conditions** you commit to: low-HP, caster, guarding, ... (these activate conditional relic effects)
- **Status focus** (bleed / poison / frost / sleep / madness)

## What it optimizes: `S(build)`

A **build** = (character, weapon type + affinity, vessel, 3 normal relics + 3 deep relics).

```
S = w_offense * OFFENSE + w_defense * SURVIVAL
```

- **Offense** = real damage vs the target: weapon AR (base + affinity + stats + relic multipliers, with stacking rules applied) multiplied by the target's elemental/physical weakness.
- **Survival** = effective HP (Vigor + HP relics) and negation (armor × relic negation) against the target's attack × Deep-of-Night scaling → a one-shot margin.
- **Generalist target** → aggregate S (average, or worst-case) over all field bosses + Nightlords.

`S` is the heart of the system: every search algorithm just calls `S` to compare builds. If `S` is correct, the optimizer is correct.

## What it produces: a gameplan

Not a static loadout — a plan, because weapons are found (randomized) during a run.

- **EQUIP (certain)**: the vessel + 6 relics (names + grid coordinates, split normal / deep)
- **HUNT (in-game)**: the weapon type + affinity to look for; which affixes to prioritize (e.g. "+12% Fire"); "carry 3+ Katanas" style advice when a relic rewards it
- **STACK**: the buffs the build maximizes (stackable, biggest contributors)
- **PLAY**: attack types, status to apply
- **SCORES**: offense, survival (one-shot verdict) + why (top contributing effects)

## Modes

- **Targeted** — vs one Nightlord: exploits its exact elemental/status weakness.
- **Generalist** — strong vs all NPCs, used as a proxy for the unknown Deep of Night final boss. This is why every enemy was extracted: being powerful against everything implies being powerful against the unknown boss.

## The engine (how it searches)

Implemented in `nightreign/optimize/` behind `nr optimize`:

```
nr optimize <character> [boss] [--weapon-type T] [--weight W] [--don N]
            [--toggle dim]... [--play "melee=0.7,crit=0.3"] [--types N]
            [--level N] [--beam K] [--top N]
nr ui                # local web UI for the same engine (stdlib http.server,
                     # offline, French). Serves a built SPA (web/ — Vite + React
                     # + Tailwind + Three.js) styled after Nightreign's own menus:
                     # cold navy/silver palette, a Nightfarer character-select
                     # (full-body renders in a gothic arch), a WebGL ember
                     # atmosphere, and every weapon & relic shown with its real
                     # in-game icon. Build once: `npm --prefix web run build`.
                     # Extract the visuals first: `nr data icons art`.
```

```
for each weapon type (fixed, or the 3 best by real damage vs the target)
    pick the best weapon of that type (real AR at the character's stats)
    activate the conditional effects (weapon type + toggles + character locks)
    for each OWNED vessel: prune dominated relics (s_c-aware, per vessel),
        beam-search the 3 normal (+ 3 deep if --don >= 1) slots to maximize S
    keep the best
-> the best overall gameplans (EQUIP / HUNT / STACK / PLAY / SCORES)
```

Key algorithmic points:

- The color-slot assignment is a **transversal matroid** (bipartite matching of relics to colored slots; without `Any` slots it degenerates to a partition matroid, with them it does not), split across **two coupled pools** (normal relics → normal slots, deep relics → deep slots; coupled only through the shared aggregated effect state).
- Damage is **multiplicative** (AR × multipliers), so raw greedy risks the complementarity trap. Taking the **log** makes offense additive again → submodular → beam search (with greedy as warm start) is sound; greedy alone measurably drops below OPT on `Any`-slot vessels (see `optimizer_mathematical_formulation.md` §5.3).
- **Dominance pruning** (outclassed relics) collapses ~400 candidates/color to a few dozen, making near-exact search feasible. Pruning must be **context-aware** (a relic dominated overall can be the only one boosting daggers) and **multiplicity-aware** on `Any`-slot vessels (a relic needs ≥ s_c strict dominators to be dropped — `optimizer_mathematical_formulation.md` §3).
- The remaining non-linearity is the **stat feedback loop** (a +Str relic raises weapon AR through scaling); handled by evaluating AR inside the marginal step, or by fixed-point iteration.

## Data used

All under `data/curated/` (regenerate with `nr data`), all real in-game values:

| File                                 | Role                                                                                                               |
|--------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| `relics.json`                        | owned relics: color, type (normal/deep/unique), grid coords                                                        |
| `effects.json`                       | 460 resolved effects: magnitude + condition + user dimension                                                       |
| `weapons.json`                       | 2317 weapons incl. affinities: base damage + scaling → AR                                                          |
| `weapon_affixes.json`                | 263 possible in-run weapon affixes (rolls to hunt for)                                                             |
| `characters.json`                    | stats (via `hero_stats`), armor negation, ability metadata                                                         |
| `nightlords.json`                    | 8 Nightlords: weaknesses (damage + status) + attacks + poise                                                       |
| `npcs.json`                          | 200 enemies for the generalist target                                                                              |
| `vessels.json`                       | chalices: 3 normal + 3 deep colored slots + `owned` (save-derived; the unobtainable "Chalices" are `owned: false`) |
| `mode_scaling.json`                  | Deep of Night ladder (x1.0 → x1.45)                                                                                |
| `icons.json`                         | weapon_id → iconId and relic item_id → iconId (built by `nr data icons`; feeds the web UI's real game icons)        |
| `nightreign/resources/conditions.py` | condition taxonomy → the user toggles                                                                              |

## EQUIP (certain) vs HUNT (found in-run)

The output separates what you commit to *now* from what you look for *during* the run — matching how the game works (relics are equipped from your owned pool; the weapon is a randomized drop):

- **EQUIP** — the vessel + relics. This is the fixed loadout. Fixing a weapon
  type (`--weapon-type`) optimizes these relics *for that type* without tying
  them to one specific weapon (relic multipliers are weapon-independent, so the
  set is stable across weapons of the type — you don't need to know which drops).
- **HUNT** — the weapon type + best weapons of it (with in-run fallbacks), plus
  a **synergy hint** (`ui/server._synergy`, "Synergies à chasser" in the web UI):
  what to prioritise on a found weapon, derived from the build's OWN aggregated
  state — the damage type(s) it amplifies most (hunt that affinity / +type%), the
  status it applies (hunt that buildup), the stat it boosts (hunt that scaling).
  This is reliable because it comes straight from the relic multipliers, not from
  the raw weapon-affix pool (`optimize/affixes.py`, `weapon_affixes.json`) which
  mixes innate/upgrade/rolled effects and stays **disabled** until a
  player-visible affix source is identified (see the deferred note).

**Deep-of-Night relic curses** (modelled 2026-07-16): deep relics carry debuffs
in a **second effect array** of the save record (offsets 56/60/64, paired
positionally to the buffs at 16/20/24 — `io/savefile.py`, validated against the
in-game blue drawback lines). They are inseparable from their buff. The
aggregation is now **sign-correct** rather than positive-only: the log-space
representation already normalises every axis to "higher = better", so relaxing the
`parse_relic` window guards to the log domain (`v > 0, != 1`) admits curses as
signed contributions with no change to `scoring.py`. `dominates` iterates the
**union** of profile keys (a curse key present only in the dominator may be
negative — skipping it would be unsound for Theorem 2), and the σ=0 aggregation
seeds at the first occurrence (`max(0, v)` would erase a non-stacking malus).
INV-3 is therefore restricted to **non-debuff** keys; the search leans on beam +
exhaustive verification rather than the greedy monotonicity bound (already the
regime §4/§5.3 assign it).

Only the curses that map onto an axis are scored (`resources/curses.py`, explicit
per-key spec, real game magnitudes — nothing invented):
- **always counted (worst-case)** — a downside biting in normal combat is never
  discounted, so a cursed relic is never over-ranked: `lowerAttackWhenBelowMaxHP`
  (×0.915 attack), the five `reduced{Stat}` swaps (−3/−3, real `add*Status`
  deltas), `impairedAffinityDamageNegation` (×1.12 elemental). Their positive
  twins stay gated — deliberately asymmetric.
- **evasion window** (`moreDamageTakenAfterEvasion`, `repeatedEvasions*`, ×1.45
  damage taken) — also **always counted (worst-case)**: every character dodges
  (Duchess just dodges more), so the trigger is near-universal. Dodge *frequency*
  is not in the data, but under a worst-case posture that is moot — the ceiling is
  the same for all — so there is no per-character special-case.
- **other windows** (post-flask, near-death): their window correlates with
  safety/rarity, so we do NOT invent an uptime — they are **display-only** (shown,
  never scored) and handled purely through the acceptance list.

Two clean, separate malus controls (a curse is never gated by a *playstyle*
engagement toggle — those activate buffs only):
- **master switch** `count_debuffs` (default on): do the chiffrable combat curses
  weigh the score (worst-case) or not.
- **acceptance list** `refused_curses`: per-curse veto — refusing a curse
  hard-excludes every relic carrying it (`Context.relic_vetoed`, filtered in
  `build_pools`). Works for ALL curses, including the ones we never score
  (economy, self-status, the safety-correlated windows) — this is where the
  player supplies the tolerance the data can't. The UI (`CursesSection`, shown
  only under Deep of Night) lists the curses present in the owned relics, grouped
  by concern (combat / survie / utilitaire), labelled in French, with a live
  "N relics excluded" count; `resources/curses.py:CURSE_META` holds the labels.

Separately, relic **Intelligence** bonuses now feed AR: `addMagicStatus` was
missing from the tracked stat adds even though the AR engine scales on
`statIntelligence` — a fixed gap, so `+Int` buffs and the `−Int` curse halves now
count (Mind/Endurance stay out, off both axes). The survival axis also had a
type-key bug (`TARGET_TYPE_TO_ENGINE`): incoming magic/lightning/holy hits were
dropped, so 5 of 8 Nightlords lost their biggest hit — now fixed.
- **display-only** — out of axis by definition (player status resistance, rune /
  flask / ultimate economy, continuous chip): surfaced in the UI ("non chiffrée")
  but never scored. A curse's `*AttackPower` is self-inflicted status and is
  explicitly excluded from the enemy-buildup (offense) term.

The UI renders each curse as the game does — a blue line under its paired buff —
tagged "comptée" when it bites the score. Inactive/character-mismatched effects
are shown struck-through.

## Game archive extraction (`nightreign/io/`)

The encrypted dvdbnd archives (`data0-3.bhd/.bdt`) are readable end-to-end,
stdlib-only plus a self-built Oodle lib (`io/oodle/`, rebuild with its
`build.sh`). Pipeline, validated 2026-07-15: RSA-decrypt the BHD5 index
(`io/archive.py`, public per-archive keys) → seek + partial AES-128-ECB in the
BDT → `io/dcx.py` decompresses the DCX (Oodle Kraken, block-by-block, or ZSTD)
→ `parse_bnd4` → `io/tae.py` reads TAE animation durations. `nr data
animations` writes `data/raw/animation_durations.json` (10,755 attack-animation
play lengths across 506 categories). This unlocks all packed content (motion
values live here too, though those came from the params).

**Menu icons** (`nr data icons` — `datagen/icons.py`, `io/tpf.py`, `io/atlas.py`):
the item-icon atlas `/menu/01_common_h.tpf.dcx` holds 26 BC7 pages (4096²); the
paired `01_common_h.sblytbnd.dcx` maps every `MENU_ItemIcon_{id}` to a rect on a
page. Real archive paths are recovered by hashing the community Nightreign
filelist (`inputs/nightreign_dictionary.txt`) against our BHD5 index; we decode
only the pages we touch (Pillow, build-time only — `pip install .[assets]`), crop
each weapon/relic icon and save a small WebP named by iconId. iconIds come from
`EquipParamWeapon.iconId` (weapons) and `EquipParamAntique.iconId` (relics).
Output: `nightreign/ui/static/assets/icons/*.webp` (gitignored, regenerable) +
`data/curated/icons.json`. The runtime UI just serves the files — runtime stays
stdlib; the offline web fonts (Cinzel, EB Garamond, OFL) are bundled under
`ui/static/assets/fonts/`.

**Character renders + illustrations** (`nr data art` — `datagen/art.py`, `io/bxf.py`):
`/menu/00_solo_h.tpfbhd`+`.tpfbdt` is a split **BXF4** bundle (1200+ menu
textures). It holds `MENU_Character_49{C}{G}0` — full-body Nightfarer renders on
transparent backgrounds (C = index in `runner.HERO_ORDER`, G = garb) — and
`MENU_ScenarioIllust_*` ink-on-parchment lore art. We read the BXF4 with
`io/bxf.read_bxf4`, decode the base-garb render per character + every
illustration, trim and downscale to WebP under
`ui/static/assets/art/{heroes,illust}/` (gitignored). These drive the SPA's
character-select. (No clean 2D Nightlord portrait exists — the bosses are
rendered in 3D in-game.)

## Deferred (non-blocking, absolute-number only)

These affect exact numbers but not build ranking, so they are left for later:

- **Attack cadence (DPS)** — free-mode now ranks by DPS = per-hit damage ×
  a per-class cadence (`weapon_types.CADENCE`, established ER weapon-class
  attack speeds), so the slowest big-hit weapons no longer top it (Jar Cannon
  drops below fast melee). The refinement still open: a **per-weapon**
  cadence from the extracted TAE durations — the animation lengths are in hand
  (`nr data animations`, ~1.5–5.3s spread that corroborates the class
  ordering), but each weapon's exact R1 animation lives in a shared TAE
  moveset category reached through the format's inheritance graph, still to be
  resolved. Class cadence is the working approximation.
- **Skill / weapon-art damage** — motion values per skill hit are wired
  (`resources/actions.py` skill class); the spell/art *base* damage still needs
  the Magic/SwordArts params (available in `regulation.bin`).
- **Exact HP/FP/stamina pools** — the stat→pool curves need locating; ranking uses the raw stats.
- ~~**Per-action buff gating**~~ — **done**: the SpEffect gates (attack
  sub-categories, stateInfo 367 for crits, magParamChange/miracleParamChange
  for spells) are decoded into per-effect `actions`, and offense is scored
  through a **play profile** (`--play "melee=0.7,skill=0.2,crit=0.1"`, default
  pure melee) — see `optimizer_mathematical_formulation.md` §2.1. The report's
  PLAY line shows counted effects, NOTE the ones your profile gates out.
- **Spell damage** — casters are ranked via their relic multipliers (school
  gates decoded), but the offense base is still weapon AR; real sorcery/
  incantation damage needs the spell params (same family as motion values).
