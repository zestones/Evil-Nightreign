export const FR_ACTIONS: Record<string, string> = {
  melee: "Melee",
  char_skill: "Character Skill",
  ultimate_art: "Ultimate Art",
  initial: "First Hit",
  skill: "Weapon Skill",
  crit: "Critical Hits",
  guard_counter: "Guard Counter",
  throwing_knife: "Throwing Knives",
  throwing_pot: "Throwing Pots",
  glintstone_stones: "Glintstone / Gravity Stones",
  perfume: "Perfume Arts",
  roar_breath: "Roars & Breaths",
  chain_finisher: "Chain Finisher",
  stance_break: "Stance Break",
  sorcery_any: "Sorceries (all)",
  incant_any: "Incantations (all)",
  sorcery_carian: "Carian Sorcery",
  sorcery_glintblade: "Glintblade Sorcery",
  sorcery_stonedigger: "Stonedigger Sorcery",
  sorcery_crystalian: "Crystalian Sorcery",
  sorcery_thorn: "Thorn Sorcery",
  sorcery_gravity: "Gravity Sorcery",
  sorcery_invisibility: "Invisibility Sorcery",
  incant_godslayer: "Godslayer Incant.",
  incant_giants_flame: "Giants' Flame Incant.",
  incant_dragon_cult: "Dragon Cult Incant.",
  incant_bestial: "Bestial Incant.",
  incant_fundamentalist: "Fundamentalist Incant.",
  incant_dragon_communion: "Dragon Communion Incant.",
  incant_frenzied_flame: "Frenzied Flame Incant.",
};

export const FR_TYPES: Record<string, string> = {
  phys: "Physical",
  mag: "Magic",
  fire: "Fire",
  thunder: "Lightning",
  dark: "Holy",
};

export const FR_STATUS: Record<string, string> = {
  bleed: "Bleed",
  poison: "Poison",
  rot: "Rot",
  frost: "Frost",
};

export const ELEMENT_HEX: Record<string, string> = {
  phys: "#c3cede",
  mag: "#5f93cf",
  fire: "#cd6a5e",
  thunder: "#d8b657",
  dark: "#e8cf8a",
};

export const STATUS_COLOR: Record<string, string> = {
  bleed: "#cd6a5e",
  poison: "#5fa878",
  rot: "#d8b657",
  frost: "#5f93cf",
};

export const FR_STATS: Record<string, string> = {
  statStrength: "Strength",
  statDexterity: "Dexterity",
  statFaith: "Faith",
  statArcane: "Arcane",
  statVigor: "Vigor",
  statMind: "Mind",
  statIntelligence: "Intelligence",
  statEndurance: "Endurance",
};

export const RELIC_HEX: Record<string, string> = {
  Red: "#cd6a5e",
  Blue: "#5f93cf",
  Yellow: "#d8b657",
  Green: "#5fa878",
  Any: "#c3cede",
};

export interface Lore {
  title: string;
  role: string;
  line: string;
}

// Evocative flavour for the roster (lore-accurate but light).
export const CHARACTER_LORE: Record<string, Lore> = {
  Wylder: {
    title: "The Wylder",
    role: "Balanced · Swords",
    line: "A seasoned tracker, grapple in hand. Cheats death once — then hits hard.",
  },
  Guardian: {
    title: "The Guardian",
    role: "Tank · Halberds",
    line: "A winged warrior who shelters allies from the storm and breaks every assault.",
  },
  Ironeye: {
    title: "Ironeye",
    role: "Ranged · Bows",
    line: "A relentless archer: he exposes the enemy's weakness and never misses.",
  },
  Duchess: {
    title: "The Duchess",
    role: "Speed · Daggers",
    line: "A swift, veiled blade. She replays the wounds she deals and fades into shadow.",
  },
  Raider: {
    title: "The Raider",
    role: "Brute · Heavy weapons",
    line: "A colossus who soaks the night and returns every blow a hundredfold.",
  },
  Revenant: {
    title: "The Revenant",
    role: "Summoner · Support",
    line: "She calls the spirits of the dead to overwhelm and sustain the hunt.",
  },
  Recluse: {
    title: "The Recluse",
    role: "Mage · Spells",
    line: "A weaver of elemental magic, draining power from the afflictions she inflicts.",
  },
  Executor: {
    title: "The Executor",
    role: "Duelist · Katanas",
    line: "A possessed swordsman: he parries, counters, and unleashes the beast within.",
  },
  Scholar: {
    title: "The Scholar",
    role: "Savant · Spells",
    line: "A seeker of the Night's forgotten arcana.",
  },
  Undertaker: {
    title: "The Undertaker",
    role: "Dark · Versatile",
    line: "Keeper of the graves, walking between life and death.",
  },
};

// Short, scannable labels for the "Commitments" toggles (the server sends the
// long descriptive ones; these keep the panel clean).
export const SHORT_TOGGLES: Record<string, string> = {
  weak_point: "I aim for weak points",
  caster: "Spellcaster",
  low_hp: "Low-HP play",
  situational: "Counter-guard / afflicted enemy",
  status_build: "Status-focused build",
  starting_loadout: "Starting loadout",
  coop: "Co-op / allies",
  triple_loadout: "3+ weapons of the same type",
};

export const pctDelta = (x: number) =>
  `${(100 * (x - 1)).toFixed(1).replace("-", "−")} %`;
