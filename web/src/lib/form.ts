import type { OptimizeRequest } from "./api";

export interface PlayRow {
  action: string;
  weight: number;
}

export interface FormState {
  character: string;
  boss: string;
  level: number;
  don: number;
  weaponType: string;
  weight: number; // 0..100 (offense→survival)
  play: PlayRow[];
  toggles: string[];
  top: number;
  beam: number;
  countDebuffs: boolean; // score the chiffrable Deep of Night curses (worst-case)
  refusedCurses: string[]; // curse keys the player vetoes (exclude those relics)
}

export function toRequest(f: FormState): OptimizeRequest {
  const play: Record<string, number> = {};
  for (const r of f.play) if (r.weight > 0) play[r.action] = (play[r.action] ?? 0) + r.weight;
  return {
    character: f.character,
    boss: f.boss,
    weapon_type: f.weaponType,
    level: f.level,
    don: f.don,
    weight: f.weight / 100,
    play: Object.keys(play).length ? play : { melee: 1 },
    toggles: f.toggles,
    top: f.top,
    beam: f.beam,
    count_debuffs: f.countDebuffs,
    refused_curses: f.refusedCurses,
  };
}
