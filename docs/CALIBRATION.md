# Session de calibration — checklist unique (~45-60 min en jeu)

*Toutes les mesures au Sparring Grounds (mannequin d'entraînement) sauf mention.
Noter chaque valeur EXACTE affichée. À la fin, me donner la liste brute : chaque
mesure entre dans `data/ground_truth/` et recale les constantes marquées
« théoriques ». Une seule session suffit — tout est regroupé ici.*

**Rappel des constantes en attente** : `SPELL_FACTOR` (dégâts de sorts absolus),
MV effectifs des skills, formule FP (à confirmer), fenêtres multi-hit, et le
modèle **stamina** complet (section H — coûts par classe, pool, régén).

---

## ✅ DÉJÀ CALIBRÉ / CONFIRMÉ (mesures user + recherche en ligne, 17/07)

- **SPELL_FACTOR** = AR_FACTOR 0.596 (Arc via staff de base : 141 mesuré) ✓
- **SPELL_SCALING_CORRECTION** = 0.9027 (courbe complète 1→15, plate sur INT 5→51) ✓
- **Ladders des catalyseurs** (`correctSpellScalingRate`) : 135/159/211/223/250 ✓
- **Interpolation linéaire des stats** entre breakpoints ✓
- **FP = 45 + 5×Mind** ✓ (2 sources NR + 4 pools exacts)
- **Stamina = 48 + 2×Endurance** ✓ (2 sources NR + game8 : Duchess 84/Recluse 94/Raider 122/Guardian 124)
- **Motion values** : extraites de la regulation.bin NR, validées (greatsword 125/126) — la recherche a confirmé qu'elles sont justes, PAS à remplacer.
- **Poison** = 3,1% PV + 308 total ✓ (NR-confirmé, correspondait déjà) · **Pourriture** = 6% PV + 600 ✓ (recalé) · **debuff gel +15%** ✓
Le socle caster ET les formules de ressources sont acquis.

## ⚠️ Tension à trancher — 1 mesure décisive
**Le modèle de dégâts est-il purement linéaire, ou y a-t-il un multiplicateur de défense ?**
Preuves POUR le linéaire : greatsword R1 = 125/126 (= son AR), sorts = exacts (141=141).
Preuve CONTRE : ton R1 de dague à 85 (avec reliques) implique un facteur ~0.84 — MAIS sur une cible dont je ne connais pas la défense. **[TEST]** un R1 nu (sans relique) sur une cible à défense connue (mannequin d'entraînement) : si dégât = AR affiché → linéaire confirmé ; sinon on ajoute le multiplicateur. ~2 min, tranche tout le modèle mêlée.

## A. Sorts — la constante SPELL_FACTOR (~10 min) 🎯 priorité 1

Perso conseillé : **Recluse** (INT connu). Pour CHAQUE mesure noter : sort, staff
utilisé (+niveau d'amélioration), niveau du perso, dégât affiché sur le mannequin.

| #  | Mesure                                                     | Noter                |
|----|------------------------------------------------------------|----------------------|
| A1 | **Glintstone Pebble** avec un staff Common +0              | dégât d'un hit       |
| A2 | **Great Glintstone Shard**, même staff                     | dégât                |
| A3 | Pebble avec un **2ᵉ staff différent** (autre scaling)      | dégât + nom du staff |
| A4 | Pebble à un **autre niveau de perso** (ex. niv 10)         | dégât + niveau       |
| A5 | **1 incantation** de dégâts avec un seal (ex. Catch Flame) | dégât + nom seal     |

→ Débloque : `SPELL_FACTOR` (constants.py), validation du scaling catalyseur, la
formule seal (FOI).

## B. Multi-hit & canalisés — valider les fenêtres de re-hit (~8 min)

| #  | Sort                                                | Notre prédiction (à vérifier)                     |
|----|-----------------------------------------------------|---------------------------------------------------|
| B1 | **Glintblade Phalanx** (cast complet sur mannequin) | 10 hits                                           |
| B2 | **Triple Rings of Light** (1 cast, cible unique)    | ~4 touches                                        |
| B3 | **Lightning Spear** (impact direct)                 | ~3 touches (javelot + étincelles)                 |
| B4 | **Comet Azur** maintenu 2 s                         | ~10 ticks (5/s), drain 10 FP/s                    |
| B5 | **Elden Stars** cast complet sur cible unique       | ??? (notre count est non fiable — flag `assumed`) |
| B6 | **Star Shower** ou **Crystal Release**              | ??? (idem)                                        |

→ Débloque : confirmation du modèle fenêtre partagée ; recalage des sorts `assumed`.

## C. FP — confirmer la formule (~2 min)

| #  | Mesure                                                      | Noter          |
|----|-------------------------------------------------------------|----------------|
| C1 | FP max affiché (menu) sur **2 persos différents** au niv 15 | perso + valeur |

→ Notre formule : FP = 45 + 5×Mind (Duchess 180, Recluse 195 prévus).

## D. Skills & ultimates (~10 min)

| #  | Mesure                                                                                                                                           | Noter                                                 |
|----|--------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------|
| D1 | **Retaliate** (Raider niv 15, non chargé) sur mannequin                                                                                          | dégât (communauté : ~362)                             |
| D2 | **Retaliate chargé** (après avoir absorbé des coups)                                                                                             | dégât (tranche : +50 % wiki vs +24 % mesuré ailleurs) |
| D3 | **Un ultimate de burst** (ex. Totem Stela à l'impact, ou Single Shot)                                                                            | dégât + perso + niveau                                |
| D4 | **Skill avec/sans un buff mêlée générique actif** (ex. relique « attaque au corps à corps améliorée » équipée) : le skill profite-t-il du buff ? | les 2 dégâts                                          |

→ Débloque : MV effectifs des armes cachées ; décision `MELEE_PERFORMED` pour
char_skill (aujourd'hui : conservateur, pas d'héritage).

## E. Linéarité — enterrer la courbe de défense (~3 min)

| #  | Mesure                                                    | Noter              |
|----|-----------------------------------------------------------|--------------------|
| E1 | **Jar Cannon** (AR affiché ~348) : 1 tir sur le mannequin | AR affiché + dégât |
| E2 | **Un arc** (Ironeye) : AR affiché à l'équipement + dégât d'un tir | AR + dégât (tranche si les flèches ajoutent une part non modélisée — les arcs semblent sous-évalués) |

→ Si dégât ≈ AR affiché : la courbe atk/def du wiki est définitivement réfutée à
haute AR (nos mesures existantes sont à ratio ~1.0-1.2).

## F. Mécaniques d'armes (~8 min)

| #  | Mesure                                                           | Noter                                |
|----|------------------------------------------------------------------|--------------------------------------|
| F1 | **Two-handing** : même arme à 1 main puis 2 mains, même R1       | les 2 dégâts                         |
| F2 | **Power-stance** (2 armes identiques), L1                        | dégât + nb de hits affichés          |
| F3 | **Pénalité sous-niveau** : équiper une arme Rare (niv 7) à niv 5 | dégât vs le même R1 au niveau requis |
| F4 | idem avec une Legendary sous-niveau                              | dégât                                |

→ Débloque : modélisation two-handing/power-stance (étape 5 backlog) + gates de
rareté.

## G. Vérifications rapides in-game (~5 min, pas de mesure chiffrée)

| #  | Question                                                                          | Répondre                                       |
|----|-----------------------------------------------------------------------------------|------------------------------------------------|
| G1 | **Slots de talisman** : combien peut-on en équiper en run ?                       | nombre                                         |
| G2 | **Carian Regal Scepter** (si droppé un jour) : le 2ᵉ sort est-il parfois absent ? | oui/non (tranche la sémantique du `weight` 10) |
| G3 | La durée de **Finale** (Duchess)                                                  | secondes approx.                               |

## H. Stamina — il ne reste qu'UNE mesure (~1 min)

*Pool = 48 + 2×Endurance : **CONFIRMÉ** (recherche en ligne). Coûts par attaque :
**extraits** (dague R1 = 9, greatsword 15, colossale 20). Le SEUL inconnu restant
= la régén (aucune source en ligne fiable).*

| #  | Mesure                                                          | Noter    |
|----|-----------------------------------------------------------------|----------|
| H1 | **Régén stamina** : barre vidée → pleine, à l'arrêt (chrono)    | secondes |

→ Débloque la contrainte « DPS soutenu = min(cadence, régén/coût) » — pénalisera
honnêtement les armes lourdes sur faible Endurance (pool + coûts déjà en place).

## I. Catalyseurs — réparer la formule de scaling (~8 min) 🎯 nouvelle priorité 1

*Tes screenshots Lusat's (221 @+0, 243 @+1) ont prouvé que notre formule sous-estime
(~30 %) et que la ladder de renforcement des staffs est mal résolue. Il faut peu de
points pour tout recaler — le NIVEAU du perso doit être visible sur chaque capture.*

| #  | Capture (menu équipement, la fiche de l'arme)                     | Noter                              |
|----|--------------------------------------------------------------------|------------------------------------|
| I1 | **2-3 staffs différents** : « Sorcery Scaling » affiché            | staff + valeur + niveau perso      |
| I2 | **Le même staff à +0 et +1** (ou +2) si tu en as                   | valeurs par niveau de renforcement |
| I3 | **1-2 seals** : « Incant Scaling » affiché                         | seal + valeur                      |
| I4 | Chaque staff croisé : **ses 2 sorts** (photo rapide de la fiche)   | alimente le pool réel du slot 2    |

→ Débloque : la formule de scaling corrigée (gate AEC/FOI), la ladder des staffs,
et le pool des sorts variables. N'importe quel perso convient si son niveau est
visible (Recluse idéale : son INT haut fait bouger le scaling).

---

## Après la session

Me transmettre les valeurs brutes (photo/notes, peu importe le format). Je fais :
1. `data/ground_truth/*.json` : chaque mesure versionnée (avec le MD5 du patch) ;
2. recalage de `SPELL_FACTOR` & co ; les flags « théorique » tombent ;
3. les tests d'ancrage se durcissent sur tes mesures ;
4. les items F/G débloquent leurs chantiers backlog respectifs.
