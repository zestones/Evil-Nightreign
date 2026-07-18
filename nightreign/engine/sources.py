#!/usr/bin/env python3
"""Damage sources: per-action attack-power bases beyond the equipped weapon.

The optimizer's proven core aggregates relic multipliers per key and applies
them per action class (optimizer_mathematical_formulation.md §2.1). A
DamageSource supplies the CONSTANT base the multipliers act on for actions
whose damage does not come from the equipped weapon's own AR:

    OFF = Σ_a p_a · D( base_source(a) · exp(Σ_c Agg_c) )

Each source's `compute(stats_eff)` is a pure function of the (relic-boosted)
scaling stats — the same contract as attack_rating.attack_rating(), so the
Scorer memoizes every source on the same stat-bonus cache key (the §6.5
stat-feedback fixed point, second instance, zero new proof obligations).

Sources never touch the relic aggregation: adding one is adding a base, and
the search/pruning guarantees are untouched (math doc §4 mixture regime).
"""
from dataclasses import dataclass, field
from typing import Callable

from nightreign.engine import attack_rating
from nightreign.resources import constants


def max_fp(hero_stats):
    """Max FP pool from the Mind stat. FP = 45 + 5*Mind — CONFIRMED
    2026-07-17 by two Nightreign sources plus four per-character pools
    (Duchess 180, Recluse 195, Revenant 200, Wylder 140) that fall exactly
    on the line. No passive FP regen in Nightreign."""
    return constants.FP_BASE + constants.FP_PER_MIND * (hero_stats.get("statMind") or 0)


def max_stamina(hero_stats):
    """Max Stamina pool from Endurance. Stamina = 48 + 2*Endurance —
    CONFIRMED 2026-07-17 by two Nightreign sources plus the game8 per-character
    table (Duchess 84, Recluse 94, Raider 122, Guardian 124), all exact."""
    return constants.STAMINA_BASE + constants.STAMINA_PER_END * (hero_stats.get("statEndurance") or 0)


@dataclass(frozen=True)
class DamageSource:
    """One play-profile action's own attack-power base.

    action:   a resources.actions class name — ties the source into the relic
              gating (agg[("atk", t, action_class)]) and the play profile.
    compute:  stats_eff -> {phys/mag/fire/thunder/dark: attack power}.
    fp_cost:  FP per use (0 = free); feeds the sustain clamp (scoring.py).
    rate_hz:  uses per second for DPS ranking; None = unknown — the source
              still scores at its declared play weight but is excluded from
              the automatic DPS mixture (never a silent invented number).
    label:    human-readable provenance for breakdowns/UI.
    """
    action: str
    compute: Callable[[dict], dict]
    fp_cost: float = 0.0
    rate_hz: float | None = None
    label: str = ""
    meta: dict = field(default_factory=dict)


def character_skill_source(char_row, ar_tables, action="char_skill", label=""):
    """The character Skill as a hidden weapon (EquipParamWeapon 60xxxxxx):
    base + stat scaling are exact params; rate = 1/cooldown (HeroParam)."""
    weapon_id = str(char_row["skill_weapon"])
    cooldown = char_row.get("skill_cooldown") or 0.0

    def compute(stats_eff):
        return attack_rating.attack_rating(weapon_id, 0, stats_eff, ar_tables)

    # label stays empty unless a real name is passed: the raw hidden-weapon id
    # ("skill 60700000") is meaningless to a player, and the action name
    # ("Character Skill") already identifies the source in the UI.
    return DamageSource(action, compute, rate_hz=(1.0 / cooldown if cooldown > 0 else None),
                        label=label,
                        meta={"weapon_id": weapon_id, "cooldown_s": cooldown})


def ultimate_art_source(char_row, ar_tables, action="ultimate_art", label=""):
    """The Ultimate Art's strike component. rate_hz stays None: the charge
    GENERATION data exists (weapons carry ultChargeB/ultChargeExponent, the
    attack rows an ultimateChargeCorrection) but the gauge-capacity-to-
    seconds conversion is unwired/unvalidated — so the ult scores at its
    declared play weight only, honestly excluded from the automatic DPS
    mixture (backlog: charge-economy model). Returns None for transformation
    ults (id -1, e.g. Executor)."""
    weapon_id = char_row.get("ultimate_weapon")
    if weapon_id in (None, -1):
        return None
    weapon_id = str(weapon_id)

    def compute(stats_eff):
        return attack_rating.attack_rating(weapon_id, 0, stats_eff, ar_tables)

    return DamageSource(action, compute, label=label,  # no raw "ultimate 60xxxxxx" id
                        meta={"weapon_id": weapon_id})


def consumable_source(goods_entry, action, goods_id=None, tier=None):
    """A throwable consumable (pot/knife/perfume) as a damage source.

    Base = the resolved Goods->Bullet->AtkParam payload (data/curated/
    goods.json), FLAT v1: whether throwables scale with stats in Nightreign
    is unmeasured — flagged theoretical until the calibration session probes
    one. `tier` selects a Bagcraft level (Scholar) when present."""
    payload = goods_entry
    if tier and (goods_entry.get("tiers") or {}).get(str(tier)):
        payload = goods_entry["tiers"][str(tier)]
    damage = payload.get("damage")
    if not damage:
        return None
    base = {t: float(v) for t, v in damage.items()}

    def compute(_stats_eff):
        return dict(base)

    return DamageSource(action, compute, label=goods_entry.get("name", ""),
                        meta={"goods_id": goods_id, "tier": tier,
                              "confidence": payload.get("confidence"),
                              "theoretical": True})


def spell_source(spell, catalyst_id, catalyst_level, catalyst_type, ar_tables,
                 spell_id=None, guaranteed=True):
    """One spell of a catalyst instance as a source.

    spell: a data/curated/magic.json entry (needs "damage"; "action" is its
    school class so school-gated relic buffs bind mechanically). The absolute
    numbers are theoretical until SPELL_FACTOR is calibrated
    (resources/constants.py) — consumers must surface that flag.

    Mode selection (matrix audit findings #4/#6):
    - CHANNELED casts with a params-resolved channel become a per-SECOND
      source: base = damage_per_s, fp_cost = fp_per_s, rate_hz = 1 — the FP
      clamp then budgets seconds of sustain naturally (Comet Azur: 350 mag/s
      at 10 FP/s, not one 70-damage emission).
    - CHARGED casts materially stronger than the normal cast are played
      charged: base/fp take the stronger mode (a player charges when better).
    """
    damage = spell.get("damage")
    channel = spell.get("channel") or {}
    mode = "normal"
    fp_cost = float(spell.get("fp") or 0)
    rate_hz = None   # cast time: family approximation pending
    if channel.get("confidence") == "params" and channel.get("damage_per_s"):
        damage, mode = channel["damage_per_s"], "channel"
        fp_cost, rate_hz = float(channel.get("fp_per_s") or 0), 1.0
    else:
        charged = spell.get("charged") or {}
        if charged.get("damage") and \
                sum(charged["damage"].values()) > sum((damage or {}).values()):
            damage, mode = charged["damage"], "charged"
            fp_cost = float(spell.get("fp_charge") or spell.get("fp") or 0)
    if not damage:
        return None
    base = {t: float(v) for t, v in damage.items()}
    catalyst_id = str(catalyst_id)

    def compute(stats_eff):
        return attack_rating.spell_attack(base, catalyst_id, catalyst_level,
                                          stats_eff, ar_tables, catalyst_type)

    return DamageSource(spell["action"], compute,
                        fp_cost=fp_cost, rate_hz=rate_hz,
                        label=spell.get("name", ""),
                        meta={"spell_id": spell_id, "hits": spell.get("hits"),
                              "confidence": spell.get("confidence"),
                              "mode": mode, "channel": spell.get("channel"),
                              # slot-1 spell is guaranteed on the catalyst
                              # model; slot-2 needs the right roll at drop
                              "guaranteed": guaranteed})
