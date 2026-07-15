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
nr ui                # the same engine behind a local web UI (stdlib http.server,
                     # offline, French labels) — every option as a form control
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

| File                                 | Role                                                         |
|--------------------------------------|--------------------------------------------------------------|
| `relics.json`                        | owned relics: color, type (normal/deep/unique), grid coords  |
| `effects.json`                       | 460 resolved effects: magnitude + condition + user dimension |
| `weapons.json`                       | 2317 weapons incl. affinities: base damage + scaling → AR    |
| `weapon_affixes.json`                | 263 possible in-run weapon affixes (rolls to hunt for)       |
| `characters.json`                    | stats (via `hero_stats`), armor negation, ability metadata   |
| `nightlords.json`                    | 8 Nightlords: weaknesses (damage + status) + attacks + poise |
| `npcs.json`                          | 200 enemies for the generalist target                        |
| `vessels.json`                       | chalices: 3 normal + 3 deep colored slots + `owned` (save-derived; the unobtainable "Chalices" are `owned: false`) |
| `mode_scaling.json`                  | Deep of Night ladder (x1.0 → x1.45)                          |
| `nightreign/resources/conditions.py` | condition taxonomy → the user toggles                        |

## Deferred (non-blocking, absolute-number only)

These affect exact numbers but not build ranking, so they are left for later:

- **Motion values** (per-attack damage %) — need animation/TAE data from the game archives.
- **Skill / weapon-art damage** — same TAE wall (skill *effects* and names are available).
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
