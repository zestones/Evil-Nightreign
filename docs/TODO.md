# TODO — ce qu'il reste à faire

*État au 2026-07-17. Le socle (AR, dégâts de sorts, FP, stamina pool, statuts, sélection multi-sources, reliques) est calibré et testé. Ce qui suit est le reliquat, par catégorie.*

## 🎯 Mesures in-game restantes (checklist docs/CALIBRATION.md)
- [ ] **Régén de stamina** (barre vide→pleine, chrono) — le SEUL inconnu pour la contrainte de sustain complète. Pool + coûts déjà en place.
- [ ] **Linéaire vs multiplicateur de défense** — 1 R1 nu sur mannequin à défense connue. Greatsword (125/126) et sorts (141) disent linéaire ; un R1 dague à 85 (cible inconnue) fait douter. Tranche tout le modèle mêlée.
- [ ] **Une incantation (sceau/Foi)** — valide que SPELL_SCALING_CORRECTION s'applique aux incantations (aujourd'hui supposé).
- [ ] **Comptes de hits des sorts multi-hit `assumed`** (Elden Stars, Glintstone Stars, Star Shower…) + **base de Night Comet** (surestimée) + Rancorcall/Stars of Ruin (déjà mesurés, à appliquer).
- [ ] **Bleed % réel NR**, **frost proc HP**, **sleep/madness** — faible priorité.

## 🔧 Chantiers data (pas de mesure, pur décodage)
- [ ] **ItemLotParam → pool complet du slot-2** des catalyseurs (on sait slot-1 fixe / slot-2 roll, mais le pool exact du roll n'est pas décodé).
- [ ] **Payloads des arts d'arme rollés** (SwordArtsTable → drop ; comme les affixes). Rebrancher `data["sword_arts"]`.
- [ ] **Affixes d'arme** : réactiver avec une source player-visible fiable (désactivé depuis 16/07).
- [ ] Variantes weaponLevel 25 (trancher via loot tables).

## ⚙️ Features moteur (données prêtes, non branchées)
- [ ] **Contrainte de stamina** (DPS soutenu = min(cadence, régén/coût)) — dès que la régén est mesurée.
- [ ] **Cadence des sorts** — les sorts rapides (Carian Slicer, Pebble) sont sous-évalués faute de rate_hz. Modéliser cast time (animation_durations extraits).
- [ ] **Économie de charge d'ult** (ultChargeB extrait ; formule charge→temps à établir).
- [ ] **Axe stagger/posture** (saWeaponDamage/ToughnessParam extraits, jamais scorés).
- [ ] **Taille d'équipe / party scaling** (MultiPlayCorrectionParam extrait).
- [ ] **Munitions** (part élémentaire flèches), **two-handing / power-stance** (après mesure), **gates de rareté par niveau**.
- [ ] **Généraliste sur les 200 NPCs** (npcs.json extrait, non utilisé — chantier perf).

## 🖥️ UI/UX
- [x] **Passe anglais** — tout le chrome en anglais (game data déjà en anglais). *(fait 17/07)*
- [x] **Modal « How it works »** plein écran — explique comment le moteur a trouvé chaque résultat (score, arme, sorts garanti/roll, sources, reliques, stamina, FP, calibré vs théorique, non-modélisé). Épure la colonne gauche. *(fait 17/07 — `web/src/components/HowItWorks.tsx`, 7 sections ; détails techniques sortis de BuildCard vers le modal)*

## Acquis (ne pas refaire)

AR 0.596 · SPELL_FACTOR 0.596 · SPELL_SCALING_CORRECTION 0.9027 · ladders catalyseurs · interpolation stats linéaire · FP=45+5×Mind · Stamina=48+2×END · poison/pourriture/gel · slot-1 garanti vs slot-2 roll · sous-types physiques · arcs (flat) · canalisés · consommables · talismans · kits · malédictions.
