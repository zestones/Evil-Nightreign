#!/usr/bin/env python3
"""Optimization context: the situation everything is evaluated in.

A context fixes the character, the weapon type (for weapon-gated effects), the
gameplay toggles the player commits to, the target and the Deep-of-Night level.
Effect activation follows the condition taxonomy of resources/conditions.py:
  * dimension "weapon_type" : active iff the context's weapon type matches,
  * dimension "character"   : active iff the context's character matches,
  * gameplay dimensions     : active iff the toggle is committed (None = always on),
plus the per-effect `nightfarer` lock carried by the relic itself.
"""
from dataclasses import dataclass, field


#: gameplay toggles a player can commit to (see conditions.GAMEPLAY_CATEGORIES)
KNOWN_TOGGLES = {"caster", "low_hp", "situational", "status_build",
                 "starting_loadout", "coop"}


@dataclass(frozen=True)
class Context:
    character: str
    weapon_type: str | None = None          # None -> weapon-gated effects stay off
    toggles: frozenset = field(default_factory=frozenset)
    don_level: int = 1                      # Deep of Night ladder (1 = no scaling)
    count_debuffs: bool = True              # master switch for Deep-of-Night curses

    def effect_active(self, effect_info, relic_entry):
        """Is this effect instance active here? (optimizer_mathematical_formulation.md §1: cond(e))."""
        # master switch: with curses off, no debuff is scored or shown active
        if effect_info.get("is_debuff") and not self.count_debuffs:
            return False
        nightfarer = relic_entry.get("nightfarer")
        if nightfarer and nightfarer != self.character:
            return False
        state = effect_info.get("state_gate")
        if state and state not in self.toggles:
            return False   # e.g. "triple_loadout": needs 3+ armaments of the type
        cond = effect_info.get("condition") or {}
        dim = cond.get("dimension")
        if dim is None:
            return True
        if dim == "weapon_type":
            return cond.get("label") == self.weapon_type
        if dim == "character":
            return cond.get("label") == self.character
        return dim in self.toggles
