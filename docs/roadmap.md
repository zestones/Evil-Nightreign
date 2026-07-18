# EvilNightreign — "Reference" Roadmap

*Established 2026-07-17, restructured the same day after critical review. Stated goal: to become **the reference tool** for Elden Ring Nightreign build optimization — no time constraint, no heuristic shortcut. Sources: exhaustive engine audit (file:line), complete UI inventory, exploration of the 252 regulation.bin params (read-only), 3 web searches (spells, kits of the 10 Nightfarers, state of the art), targeted param checks (catalysts, talismans).*

> **STATUS (2026-07-17 evening) — phases A/B/C delivered, tested (58 tests green, 6 invariants PASS, pruning proven intact):**
> ✅ Datagen for spells (127 quantified, shared re-hit window, 15/19 channeled), arts, talismans, catalysts (156 instances + rolled spells), Staff/Seal separated — `nr data magic|sword_arts|accessories`.
> ✅ Multi-source engine: `engine/sources.py`, `offense(source_power)`, profile-driven joint selection (a caster ranks catalysts by their SPELLS), casting without a catalyst = 0, FP = 45+5×Mind + transparent clamp, math doc extended (§2/§2.1), beam=exhaustive re-verified.
> ✅ Kits of the 10 Nightfarers (`resources/kits.py`): strike/replay/utility paradigms, sourced factors (Restage ×1.125, Marking ×1.10, Tenacity, Resolve), archetypes exposed in `/api/meta`.
> ✅ Talismans as recommendations (marginal gain via the exact engine); golden master 7 contexts; `data/ground_truth/` versioned.
> ⏳ **Critical path: the calibration session (`docs/calibration.md`)** — SPELL_FACTOR & co. remain "theoretical" until measured.
> 📦 Backlog (data ready, prioritized by the 17/07 evening audit matrix): **phys_subtype offense per weapon** (swings measured 35-44% on Maris/Caligo — the biggest remaining truth gain; requires the per-weapon subtype, not extracted), **channel of channeled spells** (channel.damage_per_s extracted but not scored — Azur undervalued), **charged casts** (69 spells, payload extracted but not read), weak_point (broken, never triggered), payload of rolled arts, stagger (superArmorDurability identified), party scaling, ammo/bows (E2 measurement decides), 200-NPC generalist, consumables model (pots/knives: NON_WEAPON_ACTIONS score 0 without a source), ult charge economy (ultChargeB extracted, conversion not validated), stamina (costs extracted; pool+regen = H measurements).
> 🧹 Debt flagged by the matrix: dead module `engine/effects.py` (superseded), `data["sword_arts"]` loaded but unread (waiting on the arts backlog), extracted-but-unused fields documented (finding #13).

---

## 0. Vision & principles

**Vision.** A player describes *who they play, how they play, against what, and what they tolerate*; the tool responds with the best complete game plan — relics, weapon(s) to hunt, spells/catalyst, share of each damage source, sustain, alternatives — quantified from the game's real data.

**Non-negotiable principles** (already in force, to maintain):
1. **Truth > heuristic**: every number comes from the params or an in-game measurement. What is not known is shown as such (never invented), or asked of the user.
2. **Measured calibration**: every new damage source enters the ground-truth bank (versioned in-game measurements, anchor tests).
3. **Explicit approximations**: every approximation is documented (what, why, impact on ranking) and listed in the §1 matrix.
4. Code/comments in English; player docs in French; never commit game files; read-only on local copies (`inputs/`).

**Positioning (verified state of the art)**: no public tool models spells/skills/ultimates from the params (the best competitor approximates from the wikis); relic stacking is debated on their side, **measured** on ours; the linear damage formula is our measurement against their prose. Every matrix cell we fill widens the gap.

---

## 1. Game coverage matrix

The exhaustive inventory: every game element → current state → target → data source → phase. This is the roadmap's completeness contract; any newly discovered mechanic must be added to it.

### 1.1 Characters (10 Nightfarers)

| Element | State | Target | Data | Phase |
|---|---|---|---|---|
| Stats per level (1-15) | ✅ exact (hero_stats, breakpoints 1/2/12/15) | + mid-level interpolation if needed | HeroStatusParam | — |
| Armor negation | ✅ exact (product of the 4 pieces) | — | EquipParamProtector | — |
| Real HP/FP/Stamina | ⛔ raw Vigor proxy | true HP/FP/Stamina curves (FP = f(Mind), no regen) | HeroStatusParam + measurement | B |
| **Passives** | ⛔ absent | quantified per sheet: Steel Guard ×5 guard, Fighter's Resolve +50% <25% HP, Tenacity +20% on proc, Sixth Sense (1 cheat-death → survival), Duchess's Poise (dodge/stamina), Eagle Eye (+30 discovery, out of combat)… | curated sheets + SpEffect when traceable | C |
| **Skills** (damage) | ⛔ 0 damage modeled | hidden weapons 60xxxxxx (exact base+scaling) × calibrated MV, DPS = damage/cooldown | EquipParamWeapon + HeroParam (cooldowns) + CoolTimeParam | B |
| **Ultimates** (damage) | ⛔ 0 damage | same + **charge economy** (ultChargeB/Exponent per weapon, ultimateChargeCorrection per attack, gauge buffs) | same + ultCharge* fields | B/D |
| Kit paradigms | ⛔ absent | 3 curated paradigms: intrinsic strike / parasite (Restage 50-60% window 3 s) / utility (Finale, fixed spirits) | curated sheets (17/07 research) | C |
| Kit team buffs | ⛔ absent | Marking +10% damage taken 17.5 s; Totem Stela +15% ally phys; auras | curated sheets | C |
| Cooldowns/uses | ✅ extracted, not consumed | consumed by skill DPS | characters.json | B |

### 1.2 Weapons & equipment

| Element | State | Target | Data | Phase |
|---|---|---|---|---|
| AR (base, reinforce, softcaps) | ✅ calibrated (0.596, <0.4 over 15 levels) | — | validated | — |
| MV melee/initial/skill/crit/GC | ✅ extracted (reproduce the measurements) | — | motion_values | — |
| Cadence | ⚠️ per-class table | per weapon if possible (animation_durations already extracted) | TAE durations | F |
| **Catalysts & spells** | ⛔ absent | 89+ droppable instances ranked by spell damage; **separate Staff (INT/sorceries) and Seal (FTH/incantations)** — the 2 families are merged in wepmotionCategory 41 (17 seals verified) | equippedSpell_R1/R2, magicTableId, Magic→AtkParam_Pc | A/B |
| **Weapon arts** | ⛔ absent | damage+FP per art, rolls of the drops | SwordArtsParam→AtkParam_Pc, SwordArtsTableParam | A/B |
| Weapon affixes | 🚫 disabled (extracted source ≠ game) | reactivate with a real source (in-game capture to request) | AttachEffectTable + player validation | F |
| Weapon status effects | ✅ modeled | + status effects carried by **spells** (Bullet.spEffectId0-4) | Bullet | A |
| Guard (block/boost) | ⛔ absent | guard axis for Guardian/shields (Steel Guard ×5) | weapons' guard* fields | C/D |
| **Dual wield / power-stance** | ⛔ absent | model (community: double status buildup) — to verify/measure | in-game measurement | D |
| Two-handing | ⛔ absent | STR ×1.5 bonus? to verify for NR | in-game measurement | D |
| Ammo (bows) | ⛔ absent | elemental share of arrows/bolts | rows [Ammo] + Bullet | D |
| Rarity gate per level | ⛔ absent | Common 1 / Uncommon 3 / Rare 7 / Legendary 10; under-level penalty (unpublished → measure) | rule + measurement | D |
| DLC reforge (forge table) | ⛔ absent | advice "reforge your skill toward X" (1×/run) | SwordArtsTable + rule | F |
| **Talismans** | ⛔ absent — **136 droppable accessories discovered** (EquipParamAccessory, spEffectId → magnitudes) | integrated into the score (the run's talisman slot); names via the Smithbox table to retrieve | EquipParamAccessory + SpEffectParam | A/D |
| weaponLevel 25 (variants) | 🚫 excluded (unknown semantics) | decide via loot tables | ItemLotParam/ItemTableParam | A |

### 1.3 Damage sources (the engine's core)

| Source | State | Target | Phase |
|---|---|---|---|
| Weapon hit (melee) | ✅ complete | — | — |
| Ranged (bows…) | ⚠️ AR only | + ammo, shot MV | D |
| **Spells** | ⛔ weapon AR, MV 1.0 | real damage per equipped spell: base AtkParam × catalyst scaling, FP cost, school (subCategory → relic gating already in place), per-hit exact / multi-hit approximated then calibrated | B |
| **Character skills/ults** | ⛔ absent | cf. §1.1 (hidden weapons + paradigms + ult charge) | B/C |
| **Weapon arts** | ⛔ absent | damage+FP, weighted by the profile (the `skill` action already gated) | B |
| **Consumables** | ⛔ absent | knives/pots/perfumes: Goods→Bullet→AtkParam chain (same mechanic as spells); greases = temporary element | D |
| Status effects (procs) | ✅ bleed/frost/poison/rot | + **sleep/madness**: control value → crit/riposte window (sleep); to model as a damage opportunity, not as a DoT | D |
| **Stagger/posture** | ⛔ absent (data ready) | posture axis: saWeaponDamage × MV vs ToughnessParam → stance-break → riposte (crit MV known). Major damage loop of the real game | D |

### 1.4 Enemies & expedition context

| Element | State | Target | Phase |
|---|---|---|---|
| 8 Nightlords (complete stats) | ✅ | — | — |
| Generalist | ⚠️ 8 Nightlords only | true generalist over the 200 extracted NPCs (npcs.json, never loaded) | B |
| Everdark Sovereign variants | ❓ to verify | their NpcParam rows if distinct; selectable target | D |
| Multi-hit survival | ⚠️ biggest single hit | sequences/combos (2-3 hits), player poise | F |
| Deep of Night | ✅ scaling + curses + veto | unlock levels 6-7 (engine OK, UI filters at ≤5) | B |
| **Shifting Earth** | ⛔ absent | expedition context (Crater/Mountaintop/Rotted Woods/Noklateo + DLC — names to verify): loot pool bias + elemental randomness; the Lot*/MapPattern* params exist (cf. thefifthmatt datamine) | D |
| In-run progression (3 days) | ⛔ absent (level 15 assumed) | per-day/level optimization (rarity gates, day boss) | F |
| Loot tables | ⛔ not extracted | ItemLotParam_map/enemy + ItemTableParam: what actually drops, where | A |

### 1.5 Team & economy

| Element | State | Target | Phase |
|---|---|---|---|
| Team size | ⛔ absent (coop toggle only) | solo/duo/trio: enemy scaling (MultiPlayCorrectionParam extracted), kit team buffs, value of utilities (rez) | D |
| FP | ⛔ absent | pool f(Mind), spell/art/skill costs, no passive regen → sustain constraint in the caster score | B |
| Stamina | ⛔ absent | per-action costs, Endurance, passives (Duchess) — secondary axis | F |
| HP/FP flasks | ⛔ absent | HPEstusFlaskRecoveryParam/MPEstus… (defs to find — 404 under that name on Paramdex) | F |
| Runes/murk | 🚫 out of scope (displayed) | — | — |

### 1.6 Relics (acquired)

Colors, chalices, measured σ aggregation, quantified curses + veto + master switch, proven pruning: ✅ **the project's acquired foundation**. Remaining: T4 (team) effects valued in phase D (party), and the relics↔new-sources link (e.g. "Improved Sorcery" → real spells) that falls out naturally with phase B.

---

## 2. Target engine architecture ("ultra clean")

The central refactor: **the damage source becomes the primary abstraction.**

```
DamageSource (protocol)
├─ WeaponAttack   (AR × MV × cadence)            — existing
├─ SpellCast      (equipped spell × catalyst scaling × FP cost)
├─ CharacterSkill (hidden weapon × calibrated MV / cooldown)
├─ UltimateArt    (same × charge economy)
├─ WeaponArt      (art × FP)
└─ ConsumableThrow(goods → bullet → atk)
```

- Each source exposes: `damage_by_type(agg, stats)`, `resource_cost`, `rate` (cadence/cooldown/FP limit), `gates` (actions/schools for relic gating — unchanged).
- **The play profile weights sources, no longer abstract actions**: "60% spells, 30% melee, 10% skill" becomes genuinely computable.
- **Selection becomes joint**: argmax over (main weapon, catalyst instance ↔ its rolled spells, relics) — a caster's picker ranks the 89+ staffs/seals by spell damage at the character's scaling, never again by raw AR.
- **The score extends cleanly**: S = w·OFF(source profile) + (1-w)·SURV, with optional axes displayed (posture DPS, FP sustain, team support) — the 2-axis core remains, the secondary axes inform without polluting.
- Sustain constraint: a caster profile is feasible if `Σ(FP cost × frequency) ≤ pool + refills`; otherwise the verdict shows it and proposes the optimal degraded mix.
- `optimizer-math.md` is updated at each extension (submodularity/monotonicity re-verified with the new dimensions; beam+pruning remain valid as long as per-key aggregation is unchanged — to re-prove otherwise).

---

## 3. Player profile — capturing how you play (UI)

The stepper becomes the profile questionnaire, curated per character:

1. **Who** — Nightfarer (current visual roster) → loads its kit sheet (passive, skill, ult, relevant schools, archetypes).
2. **How** — *the central new step*:
   - **Per-character preconfigured archetypes** (e.g. Recluse: "Glintstone caster", "Cocktail hybrid"; Ironeye: "Bow status effects", "Marked burst"; Duchess: "Bleed daggers", "INT caster") → pre-fill sources + actions + engagements, everything stays editable.
   - Source mix in % (melee / spells / ranged / skill-centric) — replaces the raw list of 27 uncurated actions.
   - Choice of spells/catalyst for casters (or "auto: best droppable rolls").
   - Current engagements (guard, status effects, low-HP…) kept.
3. **Against what** — Nightlord/generalist (200 NPCs)/Everdark, DoN 0-7, Shifting Earth, team size, target level.
4. **Tolerances** — offense↔survival slider, curses (acquired), risk (low-HP builds), minimal FP sustain.

**Enriched verdict (output side)**: damage breakdown **by source** (melee/spell/skill/status as % of total), indicative rotation, FP sustain gauge, estimated TTK per target, survival share (biggest hit vs HP), weapon AND catalyst alternatives, build export/share. Always: whatever is approximated carries an explicit note.

---

## 4. Phases

Each phase has **acceptance criteria**; a phase is only "done" when tested and documented.

### Phase A — Data foundations (params-only, zero risk)
Datagen: `magic.json` (spells: damage/type, FP, school, charged, status effects via Bullet), enrich `custom_weapons.json` (magicTableId → instance spells, swordArtsTableId), `skills.json` (hidden weapons 60xxxxxx + cooldowns), arts, **talismans** (EquipParamAccessory + Smithbox name table), consumables (Goods→Bullet), toughness, cooldowns, **loot tables** (ItemLot/ItemTable — decides weaponLevel 25 and prepares Shifting Earth), Staff/Seal separation in weapon_types.
**Acceptance**: `nr data` regenerates everything; counts logged; extended invariants (every droppable spell resolves to an AtkParam; every skill to a hidden weapon); cross-validation of at least 3 values against community sources (already: Pebble 152 ✅).

### Phase B — Multi-source engine (the core)
DamageSource abstraction; Spells source (per-hit exact); Skills/Ults source (strike paradigm, DPS per cooldown); **intent-driven joint selection** (fixes "Sorcery → Great Spear"); FP constraint; true 200-NPC generalist; physical subtypes + weak points (already coded, to wire in); DoN 6-7.
**Acceptance**: a "100% Carian sorcery" profile on Duchess/Recluse produces a catalyst + magic relics and a quantified spell damage; invariants PASS; pure melee mode reproduces the current results (non-regression).

### Phase C — Kits & per-Nightfarer customization
The 10 curated sheets (quantified passives, skill paradigms, team buffs, relevant schools/weapons, archetypes); injection into the score (Tenacity, Resolve, Restage as window multiplier, Marking as team multiplier); curated actions/archetypes exposed to the UI.
**Acceptance**: each character has ≥2 sensible archetypes; kit multipliers are sourced (params or referenced measurement); never an invented value (unknowns shown as "not quantified").

### Phase D — Extended game context
Team size (MultiPlayCorrection + kit buffs + value of utilities); stagger/riposte axis; sleep/madness as opportunity windows; ammo; dual-wield/two-handing (after measurement); talismans in the score; Shifting Earth (loot bias); Everdark; rarity gates.
**Acceptance**: each addition demonstrated on a real case (e.g. quantified Greatsword vs Gladius posture build) and covered by the ground-truth bank (§5) when a measurement was required.

### Phase E — "Reference" UI
The §3 profile-stepper, the enriched verdict, FR i18n of spells/skills/talismans, DoN 6-7, export/share. Always: ultra-clean UX, no catch-all, separated concerns (already established with the curses).
**Acceptance**: complete caster/melee/support flow in <2 min; every displayed number traceable (source/approximation tooltip).

### Phase F — Long-tail completeness
Per-weapon cadence (TAE durations), multi-hit survival, stamina, flasks, reactivated affixes (real source), DLC reforge, per-day in-run progression, multi-hit MV of channeled spells (targeted calibration or TAE — the only real TAE remnant).

**Order: A → B → C → E(v1) → D → E(v2) → F.** An intermediate UI pass (E v1) as soon as B/C deliver, so the tool stays continuously usable.

---

## 5. Calibration & ground-truth bank

Formalize what's acquired (dagger measurements lvl 1-15, backstab, stacking) into a **versioned bank**: `data/ground_truth/*.json` {context, measurement, date, patch} + anchor tests that fail if a formula deviates.

Measurements to schedule (Sparring Grounds, detailed protocol per measurement):
1. **Spells**: Pebble then Great Shard with 2 different staffs/INT → scaling constant + does AR_FACTOR apply to spells.
2. **Skills**: 1 measurement per paradigm (Retaliate lvl 15 vs community table 362; a burst ult) → effective MV.
3. **Linearity stress-test**: high-AR weapon (Jar Cannon ~348) → definitively buries the wiki defense curve.
4. **Power-stance / two-handing**: measured damage and buildup.
5. **Under-level weapon penalty** (2 measurements); **incantations** (1 seal); charged casts.

---

## 6. Engineering & quality

- **Per-patch versioning**: regulation.bin hash stored with each datagen; alert if the install diverges (MD5 verified 17/07: the 2 installs = our copy).
- **Tests**: ground-truth anchoring, data invariants (extended validate_invariants), ranking non-regression on frozen contexts, CLI/UI parity (types_count/max_weapon_level exposed everywhere or nowhere).
- **Living docs**: optimizer.md (already out of sync on generalist/affinity — to fix), math doc updated at each score extension.
- **Perf**: the search space grows (spells × weapons × relics) — profile the beam, memoize per source.

---

## 7. Watch & contested points

1. **Linear formula**: our measurement refutes the wiki curve (ratios ~1.0-1.2: damage = exact AR where the curve predicts ×0.40-0.45); stress-test §5.3 to be unassailable — then publish the refutation (reference positioning).
2. **Stacking**: measured on our side (σ=0/σ=1, ×1.452); the community still contradicts itself — our model is authoritative.
3. To settle by data/measurement (never by web consensus): "Single Shot ×2 on a marked target" (unsourced folklore), conflicting durations (Finale, Immortal March), charged Retaliate bonus (+50% wiki vs +24% measured on a dummy).

---

## 8. Pending decisions (the user decides)

1. Validate the order A → B → C → E(v1) → D → E(v2) → F.
2. Multi-hit of channeled spells: assumed approximation (1 hit) → targeted calibration → TAE (in that order?).
3. Team size: confirmed in scope (phase D)?
4. In-run progression (levels <15, days): phase F or out of scope?
5. In-game §5 measurements: the user does them as they go (the tool will list "missing measurements" the way it lists curses)?
