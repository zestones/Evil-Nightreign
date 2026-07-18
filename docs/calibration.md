# Calibration session — single checklist (~45-60 min in-game)

*All measurements at the Sparring Grounds (training dummy) unless noted. Record each EXACT value displayed. At the end, give me the raw list: each measurement goes into `data/ground_truth/` and recalibrates the constants marked "theoretical". A single session is enough — everything is grouped here.*

**Reminder of pending constants**: `SPELL_FACTOR` (absolute spell damage), effective skill MVs, FP formula (to be confirmed), multi-hit windows, and the full **stamina** model (section H — per-class costs, pool, regen).

---

## ALREADY CALIBRATED / CONFIRMED (user measurements + online research, 17/07)

- **SPELL_FACTOR** = AR_FACTOR 0.596 (Arc via base staff: 141 measured) ✓
- **SPELL_SCALING_CORRECTION** = 0.9027 (full curve 1→15, flat over INT 5→51) ✓
- **Catalyst ladders** (`correctSpellScalingRate`): 135/159/211/223/250 ✓
- **Linear stat interpolation** between breakpoints ✓
- **FP = 45 + 5×Mind** ✓ (2 NR sources + 4 exact pools)
- **Stamina = 48 + 2×Endurance** ✓ (2 NR sources + game8: Duchess 84/Recluse 94/Raider 122/Guardian 124)
- **Motion values**: extracted from the NR regulation.bin, validated (greatsword 125/126) — research confirmed they are correct, NOT to be replaced.
- **Poison** = 3.1% HP + 308 total ✓ (NR-confirmed, already matched) · **Rot** = 6% HP + 600 ✓ (recalibrated) · **frost debuff +15%** ✓

The caster foundation AND the resource formulas are established.

## Tension to resolve — 1 decisive measurement

**Is the damage model purely linear, or is there a defense multiplier?**

Evidence FOR linear: greatsword R1 = 125/126 (= its AR), spells = exact (141=141). Evidence AGAINST: your dagger R1 at 85 (with relics) implies a factor of ~0.84 — BUT on a target whose defense I don't know. **[TEST]** a bare R1 (no relic) on a target with known defense (training dummy): if damage = displayed AR → linear confirmed; otherwise we add the multiplier. ~2 min, settles the entire melee model.

## A. Spells — the SPELL_FACTOR constant (~10 min) 🎯 priority 1

Recommended character: **Recluse** (known INT). For EACH measurement record: spell, staff used (+upgrade level), character level, damage displayed on the dummy.

| #  | Measurement                                               | Record              |
|----|-----------------------------------------------------------|---------------------|
| A1 | **Glintstone Pebble** with a Common staff +0              | damage of one hit   |
| A2 | **Great Glintstone Shard**, same staff                    | damage              |
| A3 | Pebble with a **2nd different staff** (different scaling) | damage + staff name |
| A4 | Pebble at a **different character level** (e.g. lvl 10)   | damage + level      |
| A5 | **1 damage incantation** with a seal (e.g. Catch Flame)   | damage + seal name  |

→ Unlocks: `SPELL_FACTOR` (constants.py), catalyst scaling validation, the seal formula (FOI).

## B. Multi-hit & channeled — validate the re-hit windows (~8 min)

| #  | Spell                                             | Our prediction (to verify)                     |
|----|---------------------------------------------------|------------------------------------------------|
| B1 | **Glintblade Phalanx** (full cast on dummy)       | 10 hits                                        |
| B2 | **Triple Rings of Light** (1 cast, single target) | ~4 hits                                        |
| B3 | **Lightning Spear** (direct impact)               | ~3 hits (javelin + sparks)                     |
| B4 | **Comet Azur** held for 2 s                       | ~10 ticks (5/s), 10 FP/s drain                 |
| B5 | **Elden Stars** full cast on single target        | ??? (our count is unreliable — flag `assumed`) |
| B6 | **Star Shower** or **Crystal Release**            | ??? (same)                                     |

→ Unlocks: confirmation of the shared-window model; recalibration of the `assumed` spells.

## C. FP — confirm the formula (~2 min)

| #  | Measurement                                                     | Record            |
|----|-----------------------------------------------------------------|-------------------|
| C1 | Max FP displayed (menu) on **2 different characters** at lvl 15 | character + value |

→ Our formula: FP = 45 + 5×Mind (Duchess 180, Recluse 195 predicted).

## D. Skills & ultimates (~10 min)

| #  | Measurement                                                                                                                             | Record                                                 |
|----|-----------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------|
| D1 | **Retaliate** (Raider lvl 15, uncharged) on dummy                                                                                       | damage (community: ~362)                               |
| D2 | **Charged Retaliate** (after absorbing hits)                                                                                            | damage (settles: +50% wiki vs +24% measured elsewhere) |
| D3 | **A burst ultimate** (e.g. Totem Stela on impact, or Single Shot)                                                                       | damage + character + level                             |
| D4 | **Skill with/without a generic melee buff active** (e.g. "improved melee attack" relic equipped): does the skill benefit from the buff? | both damage values                                     |

→ Unlocks: effective MVs of the hidden weapons; `MELEE_PERFORMED` decision for char_skill (currently: conservative, no inheritance).

## E. Linearity — bury the defense curve (~3 min)

| #  | Measurement                                                     | Record                                                                               |
|----|-----------------------------------------------------------------|--------------------------------------------------------------------------------------|
| E1 | **Jar Cannon** (displayed AR ~348): 1 shot on the dummy         | displayed AR + damage                                                                |
| E2 | **A bow** (Ironeye): displayed AR on equip + damage of one shot | AR + damage (settles whether arrows add an unmodeled portion — bows seem underrated) |

→ If damage ≈ displayed AR: the wiki's atk/def curve is definitively refuted at high AR (our existing measurements are at a ratio of ~1.0-1.2).

## F. Weapon mechanics (~8 min)

| #  | Measurement                                                   | Record                                      |
|----|---------------------------------------------------------------|---------------------------------------------|
| F1 | **Two-handing**: same weapon 1-handed then 2-handed, same R1  | both damage values                          |
| F2 | **Power-stance** (2 identical weapons), L1                    | damage + number of hits displayed           |
| F3 | **Under-level penalty**: equip a Rare weapon (lvl 7) at lvl 5 | damage vs the same R1 at the required level |
| F4 | same with an under-level Legendary                            | damage                                      |

→ Unlocks: two-handing/power-stance modeling (backlog step 5) + rarity gates.

## G. Quick in-game checks (~5 min, no numeric measurement)

| #  | Question                                                                       | Answer                                        |
|----|--------------------------------------------------------------------------------|-----------------------------------------------|
| G1 | **Talisman slots**: how many can be equipped in a run?                         | number                                        |
| G2 | **Carian Regal Scepter** (if ever dropped): is the 2nd spell sometimes absent? | yes/no (settles the semantics of `weight` 10) |
| G3 | Duration of **Finale** (Duchess)                                               | approx. seconds                               |

## H. Stamina — only ONE measurement left (~1 min)

*Pool = 48 + 2×Endurance: **CONFIRMED** (online research). Per-attack costs: **extracted** (dagger R1 = 9, greatsword 15, colossal 20). The ONLY remaining unknown = regen (no reliable online source).*

| #  | Measurement                                                         | Record  |
|----|---------------------------------------------------------------------|---------|
| H1 | **Stamina regen**: bar emptied → full, while standing still (timed) | seconds |

→ Unlocks the constraint "sustained DPS = min(cadence, regen/cost)" — will honestly penalize heavy weapons at low Endurance (pool + costs already in place).

## I. Catalysts — fix the scaling formula (~8 min) 🎯 new priority 1

*Your Lusat's screenshots (221 @+0, 243 @+1) proved that our formula underestimates (~30%) and that the staff upgrade ladder is poorly resolved. It takes few points to recalibrate everything — the character LEVEL must be visible in each screenshot.*

| #  | Screenshot (equipment menu, the weapon's stat sheet)                | Record                          |
|----|---------------------------------------------------------------------|---------------------------------|
| I1 | **2-3 different staffs**: "Sorcery Scaling" displayed               | staff + value + character level |
| I2 | **The same staff at +0 and +1** (or +2) if you have one             | values per upgrade level        |
| I3 | **1-2 seals**: "Incant Scaling" displayed                           | seal + value                    |
| I4 | Each staff encountered: **its 2 spells** (quick photo of the sheet) | feeds the real pool of slot 2   |

→ Unlocks: the corrected scaling formula (AEC/FOI gate), the staff ladder, and the pool of variable spells. Any character works as long as its level is visible (Recluse ideal: its high INT moves the scaling).

---

## After the session

Send me the raw values (photo/notes, any format). I will do:

1. `data/ground_truth/*.json`: each measurement versioned (with the patch MD5);
2. recalibration of `SPELL_FACTOR` & co; the "theoretical" flags drop;
3. the anchor tests harden against your measurements;
4. the F/G items unlock their respective backlog work.
