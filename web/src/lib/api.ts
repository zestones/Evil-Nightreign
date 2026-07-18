// Typed client for the nr ui JSON API (served by nightreign/ui/server.py).

export interface HeroMeta {
  name: string;
  levels: number[];
  vessels: string[];
}
export interface CurseMeta {
  key: string;
  label: string;
  group: "combat" | "survie" | "utilitaire";
  scored: boolean; // also weighs the score (worst-case) vs display-only
  count: number; // owned relics carrying it
}
export interface Archetype {
  name: string;
  play: Record<string, number>;
  toggles?: string[];
  weapon?: string; // weapon type the preset implies (e.g. "Dagger"); "" = auto
}
export interface KitMeta {
  passive: string | null;
  skill_paradigm: "strike" | "replay" | "utility";
  ultimate_paradigm: "strike" | "replay" | "utility";
  favored_sources: string[];
  archetypes: Archetype[];
}
export interface Meta {
  characters: HeroMeta[];
  bosses: string[];
  weapon_types: string[];
  toggles: Record<string, string>;
  actions: string[];
  don_levels: number[];
  relic_count: number;
  curses: CurseMeta[];
  cursed_relic_curses: string[][]; // per cursed relic: its curse keys (for exclusion count)
  kits: Record<string, KitMeta>; // per-Nightfarer kit sheet (archetype presets)
}

export interface Effect {
  text: string;
  active: boolean;
  icon: string | null;
  reason: string | null;
  tradeoff: boolean;
  char_locked?: boolean; // inactive because reserved to another Nightfarer (struck through)
  curse?: boolean; // Deep of Night debuff (blue line under its paired buff)
  pair?: number | null; // index of the buff this curse is paired to
  scored?: boolean; // folded into the score (vs surfaced-only, out of axis)
  note?: string | null; // FR explanation of the curse's status in the score
}
export interface Pick {
  kind: "normal" | "deep";
  slot_color: string;
  name: string;
  color: string;
  unique: boolean;
  grid: [number, number] | null;
  grid_by_color: [number, number] | null;
  icon: string | null;
  effects: Effect[];
}
export interface EffectRow {
  key: string;
  mult: number;
  action: string;
}
export interface StatusInfo {
  proc: number;
  first_hits: number;
  fight_procs: number;
}
export interface WeaponAlt {
  name: string;
  ratio: number; // damage ratio vs the picked weapon (< 1 = weaker)
  icon: string | null;
  spell: string | null; // the spell this catalyst would cast under the profile
}
export interface Build {
  score: number;
  absolute_offense: number;
  absolute_dps: number | null;
  weapon: string;
  weapon_icon: string | null;
  weapon_type: string;
  weapon_alternatives: WeaponAlt[];
  vessel: string;
  targets: string[];
  picks: Pick[];
  offense_ratio: number;
  survival_ratio: number;
  generic: boolean;
  ref_weapon: string | null;
  cadence: number | null;
  attack_multipliers: Record<string, number>;
  stat_bonuses: Record<string, number>;
  status: Record<string, StatusInfo>;
  affix_hunt: { label: string; gain: number }[];
  synergy: Synergy[];
  actions_hit: Record<string, number>;
  top_effects: EffectRow[];
  ignored_effects: EffectRow[];
  // multi-source engine surface
  sources: Record<string, SourceInfo>; // per sourced action (spells, skill, ult)
  fp: Record<string, FpClamp>; // FP-clamped actions ({} = profile sustainable)
  fp_pool: number | null; // the character's max FP (for the human-readable note)
  play: Record<string, number>; // EFFECTIVE profile (post FP clamp)
  kit: { factor: number; details: Record<string, { factor: number; source: string }> } | null;
  stamina: { pool: number; r1_cost: number; hits_per_bar: number } | null; // stamina economy (info)
  accessory_hunt: { id: string; name: string; gain: number; icon: string | null }[]; // talisman recos
}
export interface SourceInfo {
  label: string; // e.g. the resolved spell's name
  fp_cost: number;
  confidence: string | null; // params | params_interval | params_deferred | assumed
  guaranteed: boolean; // true = guaranteed slot-1 spell; false = needs a slot-2 roll
  spell_factor_calibrated: boolean; // false -> absolute numbers are theoretical
}
export interface FpClamp {
  requested: number;
  sustainable: number;
}
export type Synergy =
  | { kind: "damage"; type: string; mult: number }
  | { kind: "all"; mult: number }
  | { kind: "status"; type: string }
  | { kind: "stat"; type: string; value: number };
export type Mode = "auto" | "generic" | "fixed";
export interface OptimizeResponse {
  mode: Mode;
  results: Build[];
}

export interface OptimizeRequest {
  character: string;
  boss: string;
  weapon_type: string;
  level: number;
  don: number;
  weight: number;
  play: Record<string, number>;
  toggles: string[];
  top: number;
  beam: number;
  count_debuffs: boolean;
  refused_curses: string[];
}

export async function getMeta(): Promise<Meta> {
  const r = await fetch("/api/meta");
  if (!r.ok) throw new Error("meta failed");
  return r.json();
}

export async function optimize(req: OptimizeRequest): Promise<OptimizeResponse> {
  const r = await fetch("/api/optimize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

export const heroArt = (name: string) => `/assets/art/heroes/${name}.webp`;
export const faceArt = (name: string) => `/assets/art/faces/${name}.webp`;

// Lore illustrations (MENU_ScenarioIllust) used as a faint verdict backdrop.
const ILLUST = [40290, 40291, 40292, 40293, 40294, 40295, 40296, 40297, 40301, 40302, 40303, 40304, 40305];
// best-effort Nightlord -> illustration (roster order); faint background only.
const BOSS_ILLUST: Record<string, number> = {
  Gladius: 40290, Adel: 40291, Gnoster: 40292, Maris: 40293,
  Libra: 40294, Fulghor: 40295, Caligo: 40296, Heolstor: 40297,
};
// The selected boss's illustration, or a deterministic one for generalist.
export const bossArt = (boss: string, seed = 0) => {
  const id = BOSS_ILLUST[boss] ?? ILLUST[Math.abs(seed) % ILLUST.length];
  return `/assets/art/illust/${id}.webp`;
};
