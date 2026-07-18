# EvilNightreign — Feuille de route « référence »

*Établi le 2026-07-17, restructuré le même jour après revue critique. Objectif assumé : devenir **l'outil de référence** de l'optimisation de build Elden Ring Nightreign — sans contrainte de temps, sans raccourci heuristique. Sources : audit exhaustif du moteur (file:line), inventaire complet de l'UI, exploration des 252 params du regulation.bin (lecture seule), 3 recherches web (sorts, kits des 10 Nightfarers, état de l'art), vérifications ciblées sur les params (catalyseurs, talismans).*

> **ÉTAT (2026-07-17 soir) — phases A/B/C livrées, testées (58 tests verts, 6 invariants PASS, pruning prouvé intact) :**
> ✅ Datagen sorts (127 chiffrés, fenêtre de re-hit partagée, canalisés 15/19), arts, talismans, catalyseurs (156 instances + sorts rollés), Staff/Seal séparés — `nr data magic|sword_arts|accessories`.
> ✅ Moteur multi-sources : `engine/sources.py`, `offense(source_power)`, sélection jointe pilotée par le profil (un caster classe les catalyseurs par leurs SORTS), cast sans catalyseur = 0, FP = 45+5×Mind + clamp transparent, math doc étendu (§2/§2.1), beam=exhaustif re-vérifié.
> ✅ Kits des 10 Nightfarers (`resources/kits.py`) : paradigmes strike/replay/utility, facteurs sourcés (Restage ×1.125, Marking ×1.10, Tenacity, Resolve), archétypes exposés dans `/api/meta`.
> ✅ Talismans en recommandation (gain marginal via le moteur exact) ; golden master 7 contextes ; `data/ground_truth/` versionné.
> ⏳ **Chemin critique : la session de calibration (`docs/CALIBRATION.md`)** — SPELL_FACTOR & co restent « théoriques » jusqu'aux mesures.
> 📦 Backlog (données prêtes, priorisé par la matrice d'audit du 17/07 soir) : **phys_subtype offense par arme** (swings mesurés 35-44 % sur Maris/Caligo — le plus gros gain de vérité restant ; nécessite le sous-type par arme, non extrait), **canal des sorts canalisés** (channel.damage_per_s extrait mais non scoré — Azur sous-évalué), **charged casts** (69 sorts, payload extrait non lu), weak_point (plombé, jamais déclenché), payload des arts rollés, stagger (superArmorDurability identifié), party scaling, munitions/arcs (mesure E2 tranche), généraliste 200 NPCs, modèle consommables (pots/couteaux : NON_WEAPON_ACTIONS scorent 0 sans source), économie de charge d'ult (ultChargeB extrait, conversion non validée), stamina (coûts extraits ; pool+régén = mesures H).
> 🧹 Dette relevée par la matrice : module mort `engine/effects.py` (superseded), `data["sword_arts"]` chargé non lu (attend le backlog arts), champs extraits-inutilisés documentés (finding #13).

---

## 0. Vision & principes

**Vision.** Un joueur décrit *qui il joue, comment il joue, contre quoi, et ce qu'il tolère* ; l'outil répond avec le meilleur plan de jeu complet — reliques, arme(s) à chasser, sorts/catalyseur, part de chaque source de dégâts, sustain, alternatives — chiffré depuis les données réelles du jeu.

**Principes non négociables** (déjà en vigueur, à maintenir) :
1. **Vérité > heuristique** : chaque nombre vient des params ou d'une mesure in-game. Ce qui n'est pas connu est affiché comme tel (jamais inventé), ou demandé à l'utilisateur.
2. **Calibration mesurée** : toute nouvelle source de dégâts entre dans la banque de vérité terrain (mesures in-game versionnées, tests d'ancrage).
3. **Approximations explicites** : chaque approximation est documentée (quoi, pourquoi, impact sur le classement) et listée dans la matrice §1.
4. Code/commentaires en anglais ; docs joueur en français ; jamais de fichiers du jeu commités ; lecture seule sur copies locales (`inputs/`).

**Positionnement (état de l'art vérifié)** : aucun outil public ne modélise sorts/skills/ultimates depuis les params (le meilleur concurrent approxime depuis les wikis) ; le stacking des reliques est débattu chez eux, **mesuré** chez nous ; la formule de dégâts linéaire est notre mesure contre leur prose. Chaque case de la matrice qu'on remplit creuse l'écart.

---

## 1. Matrice de couverture du jeu

L'inventaire exhaustif : chaque élément du jeu → état actuel → cible → source de données → phase. C'est le contrat de complétude de la roadmap ; une nouvelle mécanique découverte doit y entrer.

### 1.1 Personnages (10 Nightfarers)

| Élément                    | État                                          | Cible                                                          | Données                                              | Phase |
|----------------------------|-----------------------------------------------|----------------------------------------------------------------|------------------------------------------------------|-------|
| Stats par niveau (1-15)    | ✅ exact (hero_stats, breakpoints 1/2/12/15)   | + interpolation mid-level si besoin                            | HeroStatusParam                                      | —     |
| Négation d'armure          | ✅ exact (produit des 4 pièces)                | —                                                              | EquipParamProtector                                  | —     |
| PV/FP/Stamina réels        | ⛔ proxy Vigor brut                            | vraies courbes PV/FP/Stamina (FP = f(Mind), pas de régén)      | HeroStatusParam + mesure                             | B     |
| **Passifs**                | ⛔ absents                                     | chiffrés par fiche : Steel Guard ×5 guard, Fighter's Resolve +50 % <25 % PV, Tenacity +20 % au proc, Sixth Sense (1 cheat-death → survie), Poise de Duchess (esquive/stamina), Eagle Eye (+30 discovery, hors combat)… | fiches curées + SpEffect quand traçable              | C     |
| **Skills** (dégâts)        | ⛔ 0 dégât modélisé                            | armes cachées 60xxxxxx (base+scaling exacts) × MV calibré, DPS = dégât/cooldown | EquipParamWeapon + HeroParam (cooldowns) + CoolTimeParam | B     |
| **Ultimates** (dégâts)     | ⛔ 0 dégât                                     | idem + **économie de charge** (ultChargeB/Exponent par arme, ultimateChargeCorrection par attaque, buffs de jauge) | idem + champs ultCharge*                             | B/D   |
| Paradigmes de kit          | ⛔ absents                                     | 3 paradigmes curés : frappe intrinsèque / parasite (Restage 50-60 % fenêtre 3 s) / utilitaire (Finale, spirits fixes) | fiches curées (recherche 17/07)                      | C     |
| Buffs d'équipe du kit      | ⛔ absents                                     | Marking +10 % dégâts subis 17,5 s ; Totem Stela +15 % phys allié ; auras | fiches curées                                        | C     |
| Cooldowns/usages           | ✅ extraits, non consommés                     | consommés par le DPS de skill                                  | characters.json                                      | B     |

### 1.2 Armes & équipement

| Élément                        | État                                    | Cible                                                        | Données                                       | Phase |
|--------------------------------|-----------------------------------------|--------------------------------------------------------------|-----------------------------------------------|-------|
| AR (base, reinforce, softcaps) | ✅ calibré (0.596, <0,4 sur 15 niveaux)  | —                                                            | validé                                        | —     |
| MV mêlée/initial/skill/crit/GC | ✅ extraits (reproduisent les mesures)   | —                                                            | motion_values                                 | —     |
| Cadence                        | ⚠️ table par classe                      | par arme si possible (animation_durations déjà extraites)     | TAE durations                                 | F     |
| **Catalyseurs & sorts**        | ⛔ absents                               | 89+ instances droppables classées par dégât de sort ; **séparer Staff (INT/sorceries) et Seal (FOI/incantations)** — les 2 familles sont fusionnées dans wepmotionCategory 41 (17 seals vérifiés) | equippedSpell_R1/R2, magicTableId, Magic→AtkParam_Pc | A/B   |
| **Arts d'arme**                | ⛔ absents                               | dégât+FP par art, rolls des drops                            | SwordArtsParam→AtkParam_Pc, SwordArtsTableParam | A/B   |
| Affixes d'arme                 | 🚫 désactivés (source extraite ≠ jeu)    | réactiver avec vraie source (capture in-game à demander)      | AttachEffectTable + validation joueur         | F     |
| Statuts d'arme                 | ✅ modélisés                             | + statuts portés par les **sorts** (Bullet.spEffectId0-4)     | Bullet                                        | A     |
| Guard (garde/boost)            | ⛔ absent                                | axe garde pour Guardian/boucliers (Steel Guard ×5)            | champs guard* des armes                       | C/D   |
| **Double tenue / power-stance**| ⛔ absent                                | modéliser (communauté : double buildup de statut) — à vérifier/mesurer | mesure in-game                                | D     |
| Two-handing                    | ⛔ absent                                | bonus STR ×1.5 ? à vérifier pour NR                           | mesure in-game                                | D     |
| Munitions (arcs)               | ⛔ absent                                | part élémentaire des flèches/carreaux                         | rows [Ammo] + Bullet                          | D     |
| Gate de rareté par niveau      | ⛔ absent                                | Common 1 / Uncommon 3 / Rare 7 / Legendary 10 ; pénalité sous-niveau (non publiée → mesurer) | règle + mesure                                | D     |
| Reforge DLC (table de forge)   | ⛔ absent                                | conseil « reforge ton skill vers X » (1×/run)                 | SwordArtsTable + règle                        | F     |
| **Talismans**                  | ⛔ absents — **136 accessoires droppables découverts** (EquipParamAccessory, spEffectId → magnitudes) | intégrés au score (slot talisman du run) ; noms via table Smithbox à récupérer | EquipParamAccessory + SpEffectParam           | A/D   |
| weaponLevel 25 (variantes)     | 🚫 exclus (semantics inconnues)          | trancher via loot tables                                     | ItemLotParam/ItemTableParam                   | A     |

### 1.3 Sources de dégâts (le cœur du moteur)

| Source               | État                          | Cible                                                                | Phase |
|----------------------|-------------------------------|----------------------------------------------------------------------|-------|
| Coup d'arme (mêlée)  | ✅ complet                     | —                                                                    | —     |
| Distance (arcs…)     | ⚠️ AR seul                     | + munitions, MV tir                                                  | D     |
| **Sorts**            | ⛔ AR de l'arme, MV 1.0        | dégât réel par sort équipé : base AtkParam × scaling catalyseur, coût FP, école (subCategory → gating reliques déjà en place), per-hit exact / multi-hit approximé puis calibré | B     |
| **Skills/Ults perso**| ⛔ absents                     | cf. §1.1 (armes cachées + paradigmes + charge d'ult)                  | B/C   |
| **Arts d'arme**      | ⛔ absents                     | dégât+FP, pondérés par le profil (action `skill` déjà gâtée)          | B     |
| **Consommables**     | ⛔ absents                     | couteaux/pots/parfums : chaîne Goods→Bullet→AtkParam (même mécanique que les sorts) ; graisses = élément temporaire | D     |
| Statuts (procs)      | ✅ bleed/frost/poison/rot      | + **sleep/madness** : valeur de contrôle → fenêtre de crit/riposte (sleep) ; à modéliser comme opportunité de dégâts, pas comme DoT | D     |
| **Stagger/posture**  | ⛔ absent (données prêtes)     | axe posture : saWeaponDamage × MV vs ToughnessParam → stance-break → riposte (MV crit connu). Boucle de dégâts majeure du jeu réel | D     |

### 1.4 Ennemis & contexte d'expédition

| Élément                       | État                          | Cible                                                        | Phase |
|-------------------------------|-------------------------------|--------------------------------------------------------------|-------|
| 8 Nightlords (stats complètes)| ✅                             | —                                                            | —     |
| Généraliste                   | ⚠️ 8 Nightlords seulement      | vrai généraliste sur les 200 NPCs extraits (npcs.json, jamais chargé) | B     |
| Variantes Everdark Sovereign  | ❓ à vérifier                  | leurs rows NpcParam si distinctes ; cible sélectionnable      | D     |
| Survie multi-coups            | ⚠️ plus gros coup unique       | séquences/combos (2-3 coups), poise du joueur                 | F     |
| Deep of Night                 | ✅ scaling + curses + veto     | débloquer niveaux 6-7 (moteur OK, UI filtre à ≤5)             | B     |
| **Terres changeantes**        | ⛔ absentes                    | contexte d'expédition (Crater/Mountaintop/Rotted Woods/Noklateo + DLC — noms à vérifier) : biais des pools de loot + hasards élémentaires ; les params Lot*/MapPattern* existent (cf. datamine thefifthmatt) | D     |
| Progression in-run (3 jours)  | ⛔ absent (niveau 15 assumé)   | optimisation par jour/niveau (gates de rareté, boss de jour)  | F     |
| Loot tables                   | ⛔ non extraites               | ItemLotParam_map/enemy + ItemTableParam : qu'est-ce qui droppe vraiment, où | A     |

### 1.5 Équipe & économie

| Élément            | État                          | Cible                                                     | Phase |
|--------------------|-------------------------------|-----------------------------------------------------------|-------|
| Taille d'équipe    | ⛔ absente (toggle coop only)  | solo/duo/trio : scaling ennemi (MultiPlayCorrectionParam extrait), buffs d'équipe du kit, valeur des utilitaires (rez) | D     |
| FP                 | ⛔ absent                      | pool f(Mind), coûts sorts/arts/skills, pas de régén passive → contrainte de sustain dans le score caster | B     |
| Stamina            | ⛔ absent                      | coûts par action, Endurance, passifs (Duchess) — axe secondaire | F     |
| Fioles HP/FP       | ⛔ absent                      | HPEstusFlaskRecoveryParam/MPEstus… (defs à retrouver — 404 sous ce nom sur Paramdex) | F     |
| Runes/murk         | 🚫 hors périmètre (affiché)    | —                                                         | —     |

### 1.6 Reliques (acquis)

Couleurs, calices, agrégation σ mesurée, curses chiffrées + veto + master switch, pruning prouvé : ✅ **le socle acquis du projet**. Reste : effets T4 (équipe) valorisés en phase D (party), et le lien reliques↔nouvelles sources (ex. « Improved Sorcery » → sorts réels) qui tombe naturellement avec la phase B.

---

## 2. Architecture cible du moteur (« ultra clean »)

Le refactor central : **la source de dégâts devient l'abstraction première.**

```
DamageSource (protocole)
├─ WeaponAttack   (AR × MV × cadence)            — existant
├─ SpellCast      (sort équipé × scaling cata × coût FP)
├─ CharacterSkill (arme cachée × MV calibré / cooldown)
├─ UltimateArt    (idem × économie de charge)
├─ WeaponArt      (art × FP)
└─ ConsumableThrow(goods → bullet → atk)
```

- Chaque source expose : `damage_by_type(agg, stats)`, `resource_cost`, `rate` (cadence/cooldown/limite FP), `gates` (actions/écoles pour le gating des reliques — inchangé).
- **Le profil de jeu pondère des sources, plus des actions abstraites** : « 60 % sorts, 30 % mêlée, 10 % skill » devient calculable réellement.
- **La sélection devient jointe** : argmax sur (arme principale, instance de catalyseur ↔ ses sorts rollés, reliques) — le picker d'un caster classe les 89+ staffs/seals par dégât de sort au scaling du perso, plus jamais par AR brut.
- **Le score s'étend proprement** : S = w·OFF(profil de sources) + (1-w)·SURV, avec axes optionnels affichés (posture DPS, sustain FP, support équipe) — le cœur 2-axes reste, les axes annexes informent sans polluer.
- Contrainte de sustain : un profil caster est faisable si `Σ(coût FP × fréquence) ≤ pool + refills` ; sinon le verdict l'affiche et propose le mix dégradé optimal.
- `optimizer_mathematical_formulation.md` est mis à jour à chaque extension (submodularité/monotonie re-vérifiées avec les nouvelles dimensions ; le beam+pruning restent valides tant que l'agrégation par clé est inchangée — à re-prouver sinon).

---

## 3. Profil joueur — capturer la manière de jouer (UI)

Le stepper devient le questionnaire de profil, curé par personnage :

1. **Qui** — Nightfarer (roster visuel actuel) → charge sa fiche kit (passif, skill, ult, écoles pertinentes, archétypes).
2. **Comment** — *l'étape nouvelle centrale* :
   - **Archétypes préconfigurés par perso** (ex. Recluse : « Caster glintstone », « Hybride cocktail » ; Ironeye : « Statuts à l'arc », « Burst marqué » ; Duchess : « Dagues saignement », « Caster INT ») → pré-remplissent sources + actions + engagements, tout reste éditable.
   - Mix de sources en % (mêlée / sorts / distance / skill-centré) — remplace la liste brute de 27 actions non curées.
   - Choix de sorts/catalyseur pour les casters (ou « auto : meilleurs rolls droppables »).
   - Engagements actuels (garde, statuts, low-HP…) conservés.
3. **Contre quoi** — Nightlord/généraliste (200 NPCs)/Everdark, DoN 0-7, Terre changeante, taille d'équipe, niveau visé.
4. **Tolérances** — curseur offense↔survie, malédictions (acquis), risque (low-HP builds), sustain FP minimal.

**Verdict enrichi (côté sortie)** : décomposition des dégâts **par source** (mêlée/sort/skill/statuts en % du total), rotation indicative, jauge de sustain FP, TTK estimé par cible, part de la survie (plus gros coup vs PV), alternatives d'armes ET de catalyseurs, export/partage de build. Toujours : ce qui est approximé porte une note explicite.

---

## 4. Phases

Chaque phase a des **critères d'acceptation** ; une phase n'est « faite » que testée et documentée.

### Phase A — Fondations data (params-only, zéro risque)
Datagen : `magic.json` (sorts : dégâts/type, FP, école, charged, statuts via Bullet), enrichir `custom_weapons.json` (magicTableId → sorts des instances, swordArtsTableId), `skills.json` (armes cachées 60xxxxxx + cooldowns), arts, **talismans** (EquipParamAccessory + table de noms Smithbox), consommables (Goods→Bullet), toughness, cooldowns, **loot tables** (ItemLot/ItemTable — tranche weaponLevel 25 et prépare les Terres changeantes), séparation Staff/Seal dans weapon_types.
**Acceptation** : `nr data` régénère tout ; comptes loggés ; invariants étendus (chaque sort droppable résout vers un AtkParam ; chaque skill vers une arme cachée) ; validation croisée d'au moins 3 valeurs contre les sources communautaires (déjà : Pebble 152 ✅).

### Phase B — Moteur multi-sources (le cœur)
Abstraction DamageSource ; source Sorts (per-hit exact) ; source Skills/Ults (paradigme frappe, DPS par cooldown) ; **sélection jointe pilotée par l'intention** (corrige « Sorcellerie → Great Spear ») ; contrainte FP ; vrais généraliste 200 NPCs ; sous-types physiques + weak points (déjà codés, à brancher) ; DoN 6-7.
**Acceptation** : un profil « 100 % sorcellerie carienne » sur Duchess/Recluse produit catalyseur + reliques magie et un dégât de sort chiffré ; invariants PASS ; le mode mêlée pur reproduit les résultats actuels (non-régression).

### Phase C — Kits & personnalisation par Nightfarer
Les 10 fiches curées (passifs chiffrés, paradigmes de skill, buffs d'équipe, écoles/armes pertinentes, archétypes) ; injection dans le score (Tenacity, Resolve, Restage en multiplicateur de fenêtre, Marking en multiplicateur d'équipe) ; actions/archétypes curés exposés à l'UI.
**Acceptation** : chaque perso a ≥2 archétypes sensés ; les multiplicateurs de kit sont sourcés (params ou mesure référencée) ; jamais de valeur inventée (les inconnus affichés « non chiffré »).

### Phase D — Contexte de jeu étendu
Taille d'équipe (MultiPlayCorrection + buffs kit + valeur des utilitaires) ; axe stagger/riposte ; sleep/madness comme fenêtres d'opportunité ; munitions ; double-tenue/two-handing (après mesure) ; talismans dans le score ; Terres changeantes (biais loot) ; Everdark ; gates de rareté.
**Acceptation** : chaque ajout démontré sur un cas réel (ex. build posture Greatsword vs Gladius chiffré) et couvert par la banque de vérité (§5) quand une mesure était requise.

### Phase E — UI « référence »
Le stepper-profil de §3, le verdict enrichi, i18n FR des sorts/skills/talismans, DoN 6-7, export/partage. Toujours : UX ultra clean, pas de fourre-tout, concerns séparés (acquis des malédictions).
**Acceptation** : parcours complet caster/mêlée/support en <2 min ; chaque nombre affiché traçable (tooltip source/approximation).

### Phase F — Complétude longue traîne
Cadence par arme (TAE durations), survie multi-coups, stamina, fioles, affixes réactivés (vraie source), reforge DLC, progression in-run par jour, MV multi-hit des sorts canalisés (calibration ciblée ou TAE — seul vrai reliquat TAE).

**Ordre : A → B → C → E(v1) → D → E(v2) → F.** Une passe UI intermédiaire (E v1) dès que B/C livrent, pour que l'outil reste utilisable en continu.

---

## 5. Calibration & banque de vérité terrain

Formaliser l'acquis (mesures dagues niv 1-15, backstab, stacking) en **banque versionnée** : `data/ground_truth/*.json` {contexte, mesure, date, patch} + tests d'ancrage qui échouent si une formule dévie.

Mesures à programmer (Sparring Grounds, protocole détaillé par mesure) :
1. **Sorts** : Pebble puis Great Shard avec 2 staffs/INT différents → constante de scaling + AR_FACTOR s'applique-t-il aux sorts.
2. **Skills** : 1 mesure par paradigme (Retaliate niv 15 vs table communautaire 362 ; un ult de burst) → MV effectifs.
3. **Stress-test linéarité** : arme haute AR (Jar Cannon ~348) → enterre définitivement la courbe de défense wiki.
4. **Power-stance / two-handing** : dégât et buildup mesurés.
5. **Pénalité d'arme sous-niveau** (2 mesures) ; **incantations** (1 seal) ; charged casts.

---

## 6. Ingénierie & qualité

- **Versionnage par patch** : hash du regulation.bin stocké avec chaque datagen ; alerte si l'install diverge (MD5 vérifié le 17/07 : les 2 installs = notre copie).
- **Tests** : ancrage vérité terrain, invariants data (validate_invariants étendu), non-régression du classement sur contextes figés, parité CLI/UI (types_count/max_weapon_level exposés partout ou nulle part).
- **Docs vivantes** : optimizer.md (déjà en écart sur le généraliste/affinité — à corriger), math doc mis à jour à chaque extension du score.
- **Perf** : l'espace de recherche grandit (sorts × armes × reliques) — profiler le beam, mémoïser par source.

---

## 7. Veille & points contestés

1. **Formule linéaire** : notre mesure réfute la courbe wiki (ratios ~1.0-1.2 : dégât = AR exact là où la courbe prédit ×0.40-0.45) ; stress-test §5.3 pour être inattaquable — puis publier la réfutation (positionnement référence).
2. **Stacking** : mesuré chez nous (σ=0/σ=1, ×1.452) ; la communauté se contredit encore — notre modèle fait foi.
3. À trancher par data/mesure (jamais par consensus web) : « Single Shot ×2 sur cible marquée » (folklore non sourcé), durées conflictuelles (Finale, Immortal March), bonus Retaliate chargé (+50 % wiki vs +24 % mesuré par dummy).

---

## 8. Décisions en attente (l'utilisateur tranche)

1. Valider l'ordre A → B → C → E(v1) → D → E(v2) → F.
2. Multi-hit des sorts canalisés : approximation assumée (1 hit) → calibration ciblée → TAE (dans cet ordre ?).
3. Taille d'équipe : confirmée dans le périmètre (phase D) ?
4. Progression in-run (niveaux <15, jours) : phase F ou hors périmètre ?
5. Mesures in-game §5 : l'utilisateur les fait au fil de l'eau (l'outil listera les « mesures manquantes » comme il liste les malédictions) ?
