#!/usr/bin/env python3
"""Full pipeline demo: character stats + weapon + relics -> damage vs each Nightlord.

Run: python examples/pipeline_demo.py   (or `nr demo pipeline`)
"""
import json

from nightreign.engine import attack_rating, damage
from nightreign.resources import constants

BOSS_DEFENSE = 100  # Nightlords have uniform flat defense; weaknesses live in the cut rates


def boss_npc_row(boss):
    """Rebuild an npc-like row (defense + cut rates) the damage model can read."""
    row = {damage.CUT_RATE_FIELD[t]: boss["damage_multiplier"].get(t, 1.0) for t in damage.CUT_RATE_FIELD}
    row.update({damage.DEFENSE_FIELD[t]: BOSS_DEFENSE for t in damage.DEFENSE_FIELD})
    row["weakPartsDamageRate"] = boss["weak_point_multiplier"]
    return row


def main():
    tables = attack_rating.load_tables()
    weapons = tables[0]
    hero = json.load(open(constants.DATA_RAW / "hero_stats.json"))
    nightlords = json.load(open(constants.DATA_CURATED / "nightlords.json"))

    stats = hero["40003"]  # Duchess level 15
    print(f"Character: Duchess level {stats['totalLevel']} "
          f"(STR{stats['statStrength']} DEX{stats['statDexterity']})")

    weapon_id = next(wid for wid, w in weapons.items()
                     if (w.get("attackBasePhysics") or 0) > 90 and (w.get("reinforceTypeId") or 0) > 0)
    ar = attack_rating.attack_rating(weapon_id, 0, stats, tables)
    effective = dict(ar)  # relic multipliers now live in optimize/aggregation
    print(f"Weapon {weapon_id}: AR = {dict((k, round(v)) for k, v in effective.items())}\n")

    print(f"{'Nightlord':10} {'damage':>7} {'+weak point':>12}")
    print("-" * 32)
    for name, boss in nightlords.items():
        row = boss_npc_row(boss)
        total, _ = damage.damage_vs_enemy(effective, row)
        total_weak, _ = damage.damage_vs_enemy(effective, row, weak_point=True)
        print(f"{name:10} {total:7.0f} {total_weak:12.0f}")


if __name__ == "__main__":
    main()
