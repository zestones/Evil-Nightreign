// Typed client for the nr ui JSON API (served by nightreign/ui/server.py).

export interface HeroMeta {
  name: string;
  levels: number[];
  vessels: string[];
}
export interface Meta {
  characters: HeroMeta[];
  bosses: string[];
  weapon_types: string[];
  toggles: Record<string, string>;
  actions: string[];
  don_levels: number[];
  relic_count: number;
}

export interface Effect {
  text: string;
  active: boolean;
  icon: string | null;
  reason: string | null;
  tradeoff: boolean;
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
export interface Build {
  score: number;
  absolute_offense: number;
  absolute_dps: number | null;
  weapon: string;
  weapon_icon: string | null;
  weapon_type: string;
  weapon_alternatives: [string, number][];
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
