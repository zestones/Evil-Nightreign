#!/usr/bin/env python3
"""Anchors for the multi-source datagen (magic / sword arts / accessories).

Cross-validation values: Glintstone Pebble's AtkParam base (152 magic) and
Great Glintstone Shard (190) match the community-established spell formula
worked example, independently of our extraction — a strong two-source check.
Counts pin the extraction so a silent regression (filter change, def drift)
fails loudly. Regenerate data with `nr data magic|weapons|sword_arts|accessories`.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nightreign.resources import constants  # noqa: E402


def _curated(name):
    return json.load(open(constants.DATA_CURATED / name))


def _raw(name):
    return json.load(open(constants.DATA_RAW / name))


class MagicCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.magic = _curated("magic.json")

    def test_pebble_matches_community_base(self):
        p = self.magic["4000"]
        self.assertEqual(p["name"], "Sorcery: Glintstone Pebble")
        self.assertEqual(p["damage"], {"mag": 152})   # community worked example
        self.assertEqual(p["fp"], 7)
        self.assertEqual(p["hits"], 1)
        self.assertEqual(p["confidence"], "params")

    def test_great_shard_matches_community_base(self):
        gs = self.magic["4001"]
        self.assertEqual(gs["damage"], {"mag": 190})
        self.assertEqual(gs["fp"], 12)

    def test_multi_hit_resolution(self):
        # A Phalanx sorcery summons multiple blades — the bullet recursion
        # must resolve more than one hit per cast, params-confident.
        phalanxes = [m for m in self.magic.values() if "Phalanx" in m["name"]]
        self.assertGreaterEqual(len(phalanxes), 3)
        for ph in phalanxes:
            self.assertGreater(ph["hits"], 1, ph["name"])
            self.assertEqual(ph["confidence"], "params", ph["name"])

    def test_deferred_cast_fallback(self):
        # Magic Glintblade's blade bullet carries no atkId; the damage lives
        # on Magic.atkParamId (182 magic) — the deferred-cast fallback.
        gb = self.magic["4390"]
        self.assertEqual(gb["name"], "Sorcery: Magic Glintblade")
        self.assertEqual(gb["damage"], {"mag": 182})
        self.assertEqual(gb["confidence"], "params_deferred")

    def test_school_gating_space(self):
        # Spell subCategory1 lives in the SAME id space as relic-effect gates:
        # Magic Glintblade must land on the glintblade school action.
        self.assertEqual(self.magic["4390"]["action"], "sorcery_glintblade")
        # every damaging spell carries a play-profile action class
        for sid, m in self.magic.items():
            if "damage" in m:
                self.assertTrue(m["action"].startswith(("sorcery_", "incant_")), sid)

    def test_catalog_counts(self):
        damaging = sum(1 for m in self.magic.values() if "damage" in m)
        self.assertEqual(len(self.magic), 176)
        # 100 tree-resolved + the deferred-fallback spells
        self.assertGreaterEqual(damaging, 100)
        self.assertLessEqual(damaging, 176 - 30)   # a real utility tail remains

    def test_channeled_spells(self):
        # Channeled casts resolve sustained DPS from params: FP drain from
        # consumeLoopMP_forMenu (cross-validated: Comet Azur 40+10/s matches
        # the in-game display) and tick rate from dmgHitRecordLifeTime.
        azur = self.magic["4200"]
        self.assertEqual(azur["channel"]["fp_per_s"], 10)
        self.assertEqual(azur["channel"]["hits_per_s"], 5.0)
        self.assertAlmostEqual(azur["channel"]["damage_per_s"]["mag"], 350.0, places=3)
        self.assertEqual(azur["channel"]["confidence"], "params")
        # breaths emit from refId2 (refId1 is a primer): Dragonfire 600 fire/s
        df = self.magic["7000"]
        self.assertEqual(df["channel"]["damage_per_s"], {"fire": 600.0})
        # coverage: at most a handful of channeled casts stay unresolved
        chans = [m["channel"] for m in self.magic.values() if "channel" in m]
        self.assertEqual(len(chans), 19)
        unresolved = sum(1 for c in chans if c["confidence"] == "assumed")
        self.assertLessEqual(unresolved, 4)


class CatalystInstances(unittest.TestCase):
    def test_every_rolled_spell_resolves(self):
        magic = _curated("magic.json")
        cw = _raw("custom_weapons.json")
        catalysts = {k: v for k, v in cw.items() if v.get("spells")}
        self.assertEqual(len(catalysts), 156)
        for k, v in catalysts.items():
            for s in v["spells"]:
                self.assertIn(str(s["id"]), magic, f"instance {k}: spell {s['id']} unresolved")
                # weight semantics are NOT established (values 10..110 observed;
                # 110 refutes the probability reading) — only positivity is a
                # data invariant here. See datagen/weapons.py.
                self.assertGreater(s["weight"], 0)


class HiddenSkillWeapons(unittest.TestCase):
    def test_every_character_skill_resolves_to_a_weapon(self):
        chars = _curated("characters.json")
        weapons = _raw("weapons.json")
        self.assertEqual(len(chars), 10)
        for name, c in chars.items():
            for field in ("skill_weapon", "ultimate_weapon"):
                wid = c.get(field)
                if wid in (None, -1):   # Executor's ultimate is a transformation
                    continue
                row = weapons.get(str(wid))
                self.assertIsNotNone(row, f"{name}.{field} {wid} not in weapons.json")
                base = sum(row.get(f, 0) or 0 for f in
                           ("attackBasePhysics", "attackBaseMagic", "attackBaseFire",
                            "attackBaseThunder", "attackBaseDark"))
                self.assertGreater(base, 0, f"{name}.{field} {wid} has no attack base")


class SwordArts(unittest.TestCase):
    def test_catalog(self):
        arts = _curated("sword_arts.json")
        self.assertEqual(len(arts), 194)
        with_damage = sum(1 for a in arts.values() if a.get("damage"))
        self.assertEqual(with_damage, 50)


class Accessories(unittest.TestCase):
    def test_catalog(self):
        acc = _curated("accessories.json")
        self.assertEqual(len(acc), 118)
        with_mag = sum(1 for a in acc.values() if a.get("magnitude"))
        self.assertEqual(with_mag, 101)


class CatalystSplit(unittest.TestCase):
    def test_seals_are_not_staffs(self):
        from nightreign.resources import weapon_types
        weapons = _raw("weapons.json")
        names = {e["ID"]: e["Entries"][0]
                 for e in json.load(open(constants.NAMES / "EquipParamWeapon.json"))["Entries"]
                 if e.get("Entries") and e["Entries"][0]}
        labels = {}
        for wid, w in weapons.items():
            if w.get("wepmotionCategory") == 41:
                labels.setdefault(weapon_types.weapon_type(w), []).append(int(wid))
        self.assertIn("Sacred Seal", labels)
        self.assertIn("Staff", labels)
        # every weapon NAMED "Seal" must be labeled Sacred Seal, never Staff
        for wid in labels["Staff"]:
            self.assertNotIn("Seal", names.get(wid, ""),
                             f"{names.get(wid)} ({wid}) mislabeled as Staff")
        seal_names = [names.get(wid, "") for wid in labels["Sacred Seal"]]
        self.assertTrue(any("Finger Seal" in n for n in seal_names), seal_names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
