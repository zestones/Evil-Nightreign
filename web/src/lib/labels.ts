export const FR_ACTIONS: Record<string, string> = {
  melee: "Mêlée",
  initial: "Première attaque",
  skill: "Art d'arme",
  crit: "Coups critiques",
  guard_counter: "Guard counter",
  throwing_knife: "Couteaux de lancer",
  throwing_pot: "Pots de lancer",
  glintstone_stones: "Pierres (glintstone/gravité)",
  perfume: "Arts de parfum",
  roar_breath: "Rugissements & souffles",
  chain_finisher: "Finisher de chaîne",
  stance_break: "Déséquilibre",
  sorcery_any: "Sorcelleries (toutes)",
  incant_any: "Incantations (toutes)",
  sorcery_carian: "Sorcellerie carienne",
  sorcery_glintblade: "Sorcellerie lame-scintillante",
  sorcery_stonedigger: "Sorcellerie fouilleuse",
  sorcery_crystalian: "Sorcellerie cristalline",
  sorcery_thorn: "Sorcellerie épineuse",
  sorcery_gravity: "Sorcellerie gravitationnelle",
  sorcery_invisibility: "Sorcellerie d'invisibilité",
  incant_godslayer: "Incant. tueuse de dieux",
  incant_giants_flame: "Incant. flamme des géants",
  incant_dragon_cult: "Incant. culte draconique",
  incant_bestial: "Incant. bestiale",
  incant_fundamentalist: "Incant. fondamentaliste",
  incant_dragon_communion: "Incant. communion draconique",
  incant_frenzied_flame: "Incant. flamme frénétique",
};

export const FR_TYPES: Record<string, string> = {
  phys: "Physique",
  mag: "Magie",
  fire: "Feu",
  thunder: "Foudre",
  dark: "Sacré",
};

export const FR_STATUS: Record<string, string> = {
  bleed: "Saignement",
  poison: "Poison",
  rot: "Écarlate",
  frost: "Gel",
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
  statStrength: "Force",
  statDexterity: "Dextérité",
  statFaith: "Foi",
  statArcane: "Arcane",
  statVigor: "Vigueur",
  statMind: "Esprit",
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

// Evocative French flavour for the roster (kept lore-accurate but light).
export const CHARACTER_LORE: Record<string, Lore> = {
  Wylder: {
    title: "Le Rôdeur",
    role: "Équilibré · Épées",
    line: "Un traqueur aguerri, grappin au poing. Trompe la mort une fois — puis frappe fort.",
  },
  Guardian: {
    title: "Le Gardien",
    role: "Tank · Hallebardes",
    line: "Guerrier ailé qui abrite ses alliés sous la tempête et brise les assauts.",
  },
  Ironeye: {
    title: "Œil-de-Fer",
    role: "Distance · Arcs",
    line: "Archer implacable : il révèle les failles de l'ennemi et ne rate jamais.",
  },
  Duchess: {
    title: "La Duchesse",
    role: "Vélocité · Dagues",
    line: "Lame véloce et voilée. Elle rejoue les blessures infligées et s'efface dans l'ombre.",
  },
  Raider: {
    title: "Le Pillard",
    role: "Brute · Armes lourdes",
    line: "Colosse qui encaisse la nuit et rend chaque coup au centuple.",
  },
  Revenant: {
    title: "La Revenante",
    role: "Invocation · Soutien",
    line: "Elle appelle les esprits des défunts pour submerger et soutenir la traque.",
  },
  Recluse: {
    title: "La Recluse",
    role: "Mage · Sorts",
    line: "Tisseuse de magies élémentaires, elle draine la puissance des affres qu'elle inflige.",
  },
  Executor: {
    title: "L'Exécuteur",
    role: "Duelliste · Katanas",
    line: "Épéiste possédé : il pare, contre, et libère la bête tapie en lui.",
  },
  Scholar: {
    title: "L'Érudit",
    role: "Savant · Sorts",
    line: "Chercheur des arcanes oubliés de la Nuit.",
  },
  Undertaker: {
    title: "Le Fossoyeur",
    role: "Sombre · Polyvalent",
    line: "Gardien des tombes, il marche entre la vie et le trépas.",
  },
};

// Short, scannable labels for the "Engagements" toggles (the server sends long
// descriptive ones; these keep the panel clean).
export const SHORT_TOGGLES: Record<string, string> = {
  caster: "Lanceur de sorts",
  low_hp: "Jeu à PV bas",
  situational: "Contre-garde / ennemi affligé",
  status_build: "Build orienté statuts",
  starting_loadout: "Loadout de départ",
  coop: "Coop / alliés",
  triple_loadout: "3+ armes du même type",
};

export const pctDelta = (x: number) =>
  `${(100 * (x - 1)).toFixed(1).replace("-", "−")} %`;
