import { useState } from "react";
import { Swords, Compass } from "lucide-react";
import { RelicRow } from "./Sockets";
import { HowItWorks } from "./HowItWorks";
import { cn } from "@/lib/cn";
import { FR_ACTIONS, FR_TYPES, FR_STATS, FR_STATUS, STATUS_COLOR, ELEMENT_HEX, pctDelta } from "@/lib/labels";
import type { Build, Mode, Synergy } from "@/lib/api";

// the game's per-affinity damage icons (fire/magic/lightning/holy + physical),
// extracted by `nr data icons` from SB_PropertyIcon; graceful text fallback.
const ElemImg = ({ type }: { type: string }) => (
  <img src={`/assets/element-icons/${type}.webp`} alt="" onError={(e) => (e.currentTarget.style.display = "none")} className="h-[18px] w-[18px] flex-none object-contain" />
);

function SynergyChip({ s }: { s: Synergy }) {
  if (s.kind === "all")
    return <span className="inline-flex items-center gap-1.5 border px-2.5 py-1 font-sans text-[12.5px] text-silver" style={{ borderColor: "#c9a24a66" }}><ElemImg type="phys" /> All types <b className="tabular-nums text-gold-bright">×{s.mult.toFixed(2)}</b></span>;
  if (s.kind === "damage")
    return <span className="inline-flex items-center gap-1.5 border px-2.5 py-1 font-sans text-[12.5px] text-silver" style={{ borderColor: `${ELEMENT_HEX[s.type] ?? "#c9a24a"}88` }}><ElemImg type={s.type} /> {FR_TYPES[s.type] ?? s.type} <b className="tabular-nums text-gold-bright">×{s.mult.toFixed(2)}</b></span>;
  if (s.kind === "status")
    return <span className="inline-flex items-center gap-1 border px-2.5 py-1 font-sans text-[12.5px] text-silver" style={{ borderColor: `${STATUS_COLOR[s.type] ?? "#c9a24a"}88` }}><span className="h-2 w-2 rotate-45" style={{ background: STATUS_COLOR[s.type] ?? "#c9a24a" }} /> {FR_STATUS[s.type] ?? s.type} status</span>;
  return <span className="inline-flex items-center gap-1 border border-line/70 bg-night-700/50 px-2.5 py-1 font-sans text-[12.5px] text-silver">Scaling {FR_STATS[s.type] ?? s.type}</span>;
}

const hide = (e: React.SyntheticEvent<HTMLImageElement>) => {
  e.currentTarget.style.display = "none";
};

function SubHead({ children, hint }: { children: React.ReactNode; hint?: string }) {
  return (
    <div className="mb-2 flex items-center gap-2.5" title={hint}>
      <span className={cn("font-display text-[11px] uppercase tracking-widest2 text-gold/80", hint && "cursor-help")}>{children}</span>
      {hint && <span className="flex h-3.5 w-3.5 flex-none items-center justify-center rounded-full border border-line/60 font-sans text-[9px] text-dim">?</span>}
      <span className="h-px flex-1 bg-gradient-to-r from-gold-deep/30 to-transparent" />
    </div>
  );
}

function Meter({ value, kind }: { value: number; kind: "off" | "srv" }) {
  return (
    <div className="h-3 overflow-hidden rounded-full border border-line-soft bg-night-700">
      <span
        className={cn(
          "block h-full rounded-full",
          kind === "off"
            ? "bg-gradient-to-r from-[#6f4a1e] to-gold-bright shadow-[0_0_10px_rgba(201,162,74,0.5)]"
            : "bg-gradient-to-r from-[#22503a] to-relic-green shadow-[0_0_10px_rgba(95,168,120,0.4)]"
        )}
        style={{ width: `${Math.min(100, (value / 3) * 100)}%` }}
      />
    </div>
  );
}

function BigStat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-sm border border-line/50 bg-night-900/40 px-3 py-2.5 text-center" title={hint}>
      <div className="font-sans text-[26px] font-semibold leading-none tabular-nums text-gold-bright">{value}</div>
      <div className={cn("mt-1 font-sans text-[10px] uppercase tracking-[0.14em] text-silver/70", hint && "cursor-help")}>{label}{hint && " ⌄"}</div>
    </div>
  );
}

export function BuildCard({ b, index, mode, character }: { b: Build; index: number; mode: Mode; character: string }) {
  // The left column leads with the verdict (weapon, numbers, sources) and the
  // in-run hunt advice. Everything expert — multipliers, per-action figures,
  // relic counting, calibration limits — lives in the "How it works" modal so
  // the column stays clean (user feedback 17/07).
  const [explain, setExplain] = useState(false);
  const prime = index === 0;
  const star = b.generic ? "*" : "";
  const normal = b.picks.filter((p) => p.kind === "normal");
  const deep = b.picks.filter((p) => p.kind === "deep");

  // damage decomposition by source: share_a = play_a × hit_a / Σ (the
  // EFFECTIVE profile, post FP clamp, comes from the engine — never recomputed)
  const play = b.play ?? {};
  const shareTotal = Object.entries(b.actions_hit).reduce(
    (s, [a, v]) => s + (play[a] ?? 0) * v, 0);
  const sourceRows = Object.entries(b.actions_hit)
    .map(([a, v]) => ({
      action: a,
      hit: v,
      weight: play[a] ?? 0,
      share: shareTotal > 0 ? ((play[a] ?? 0) * v) / shareTotal : 0,
      info: b.sources?.[a] ?? null,
    }))
    .filter((r) => r.weight > 0)
    .sort((x, y) => y.share - x.share);
  const theoretical = sourceRows.some((r) => r.info && !r.info.spell_factor_calibrated);
  const fpClamps = Object.entries(b.fp ?? {});

  return (
    <div className="grid h-full grid-cols-1 gap-6 lg:grid-cols-[420px_1fr]">
      {/* ===== LEFT — arsenal ===== */}
      <div className="flex min-h-0 flex-col overflow-y-auto rounded-sm border border-line/50 bg-night-800/40 p-6">
        <div className="flex items-center gap-3 pb-5">
          <span
            className={cn("font-display text-[14px] font-semibold uppercase tracking-wider", prime ? "border border-gold px-3.5 py-1.5 text-[#221a0a]" : "border border-gold-deep/70 px-3.5 py-1.5 text-gold-bright")}
            style={prime ? { background: "linear-gradient(180deg,#e8cf8a,#7c6531)", boxShadow: "0 0 16px -4px rgba(201,162,74,0.8)" } : undefined}
          >
            #{index + 1}{prime ? " · Prime" : ""}
          </span>
          <span className="font-display text-[22px] tracking-wide text-ink">S <b className="text-gold-bright">{b.score.toFixed(3)}</b></span>
          {b.generic && <span className="ml-auto border border-line/70 bg-night-700/60 px-3 py-1.5 font-sans text-[13px] tabular-nums text-gold-bright">boost ×{b.offense_ratio.toFixed(2)}</span>}
        </div>

        <SubHead>{mode === "generic" ? "Reference weapon" : "Weapon to hunt"}</SubHead>
        <div className="flex items-center gap-4">
          <div
            className="flex h-[104px] w-[104px] flex-none items-center justify-center rounded-sm border border-gold-deep/70 p-2"
            style={{ background: "radial-gradient(circle at 50% 40%, rgba(201,162,74,0.16), rgba(8,10,16,0.9) 70%)", boxShadow: "inset 0 0 22px rgba(0,0,0,0.6), 0 0 24px -8px rgba(201,162,74,0.6)" }}
          >
            {b.weapon_icon ? <img src={b.weapon_icon} alt="" onError={hide} className="h-full w-full object-contain drop-shadow" /> : <Swords className="h-10 w-10 text-gold-deep" />}
          </div>
          <div className="min-w-0">
            <div className="font-display text-[23px] font-semibold leading-tight text-ink">{b.weapon}</div>
            <div className="mt-1 font-sans text-[13px] uppercase tracking-wide text-gold/85">{b.weapon_type}</div>
            <div className="mt-1.5 text-[13px] leading-snug text-silver/70">vs {b.targets.join(", ")}</div>
          </div>
        </div>
        {(() => {
          // WHY this weapon type: when the pick is carried by weapon-type
          // relics from the player's collection, say so — a plain Longsword
          // with +29% Straight Sword relics beats a naked Greatsword, and
          // that's the collection talking, not the weapon (user feedback)
          const typeBuff = b.top_effects.find((e) =>
            e.action === "*" && e.key.toLowerCase().includes(b.weapon_type.toLowerCase()));
          if (!typeBuff) return null;
          return (
            <p className="mt-2.5 border-l-2 border-gold-deep/60 bg-gold/5 py-1.5 pl-2.5 text-[12px] leading-snug text-silver/85">
              Chosen thanks to <b className="text-gold-bright">your relics</b>:{" "}
              {typeBuff.key} <b className="tabular-nums text-gold-bright">×{typeBuff.mult.toFixed(2)}</b> —
              a bigger weapon with no relics would do worse.
            </p>
          );
        })()}
        {(() => {
          // spell-driven build: the SPELL is the payload. Say whether it's the
          // catalyst's GUARANTEED slot-1 spell (reliable hunt) or a slot-2 ROLL.
          // Only ACTUAL spells qualify (label "Sorcery:/Incantation: …") — a
          // melee weapon's skill/ultimate is not a spell and must not show here.
          const spellSrc = Object.values(b.sources ?? {}).find((s) => /^(Sorcery|Incantation):/.test(s.label));
          const mainSpell = spellSrc?.label?.replace(/^(Sorcery|Incantation): /, "");
          if (!mainSpell) return null;
          const guaranteed = spellSrc?.guaranteed !== false;
          return (
            <p className="mt-2.5 border-l-2 border-frost/50 bg-frost/5 py-1.5 pl-2.5 text-[12px] leading-snug text-silver/85">
              The spell makes the build: <b className="text-frost">{mainSpell}</b>.
              {guaranteed ? (
                <> <span className="text-relic-green">Guaranteed</span> on this catalyst — hunting this staff means getting this spell for sure.</>
              ) : (
                <> <span className="text-[#e0c48a]">2nd, random spell</span>: this catalyst only carries it if you roll it on drop (its guaranteed spell is weaker).</>
              )}
              {" "}<span className="text-dim">Slot-1 = fixed by model · slot-2 = random roll.</span>
            </p>
          );
        })()}

        {b.weapon_alternatives.length > 0 && (
          <div className="mt-4">
            <div className="mb-2 font-sans text-[10.5px] uppercase tracking-widest text-silver/55">Alternatives</div>
            <div className="flex gap-2">
              {b.weapon_alternatives.map((a, i) => (
                <div key={i} className="flex min-w-0 flex-1 flex-col items-center gap-1.5 rounded-sm border border-line/50 bg-night-900/45 px-2 py-2.5 transition hover:border-line-bright" title={a.name}>
                  <div className="flex h-[46px] w-[46px] items-center justify-center rounded-sm border border-line/40 bg-night-800/70" style={{ boxShadow: "inset 0 0 12px rgba(0,0,0,0.6)" }}>
                    {a.icon ? <img src={a.icon} alt="" onError={hide} className="h-[40px] w-[40px] object-contain" /> : <Swords className="h-5 w-5 text-line" />}
                  </div>
                  <div className="line-clamp-2 h-[28px] w-full text-center text-[11px] leading-tight text-silver">{a.name}</div>
                  {a.spell && <div className="w-full truncate text-center text-[9.5px] leading-tight text-frost/75" title={a.spell}>{a.spell}</div>}
                  <div className="font-sans text-[12px] font-medium tabular-nums text-[#cf9074]">{pctDelta(a.ratio)}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="my-5 h-px bg-line-soft" />

        <div className="grid grid-cols-2 gap-3">
          {b.absolute_dps != null && <BigStat label="damage / s" value={`${Math.round(b.absolute_dps)}${star}`} hint="Sustained DPS = damage/hit × the weapon class's cadence." />}
          <BigStat
            label={sourceRows.length > 1 ? "damage / use (avg.)" : "damage / hit"}
            value={`${Math.round(b.absolute_offense)}${star}`}
            hint={sourceRows.length > 1
              ? `Weighted average of your declared actions (${sourceRows.map((r) => `${FR_ACTIONS[r.action] ?? r.action} ${Math.round(r.share * 100)}%`).join(", ")}) — not a single R1. The per-action breakdown is in "How it works".`
              : "Damage of one use against the target."}
          />
        </div>

        {b.stamina && (
          <p className="mt-2 text-[11px] leading-snug text-dim" title="Low Endurance + a heavy weapon = few hits before running dry. (Exact regen isn't measured yet, so it's indicative, not scored.)">
            Stamina: {b.stamina.pool} · R1 costs {b.stamina.r1_cost} → ~<b className="text-silver/80">{b.stamina.hits_per_bar} hits</b>/bar
          </p>
        )}

        {/* ---- damage decomposition by source (multi-source engine) ---- */}
        {sourceRows.length > 1 && (
          <div className="mt-5">
            <SubHead hint="The share of your damage carried by each declared way of playing (effective profile, after the FP constraint).">
              Damage sources
              {theoretical && (
                <span
                  className="ml-2 border border-frost/50 bg-frost/10 px-1.5 py-px align-middle font-sans text-[9.5px] normal-case tracking-wide text-frost"
                  title="Absolute spell damage is theoretical until SPELL_FACTOR is measured (docs/CALIBRATION.md §A)."
                >
                  spells: theoretical
                </span>
              )}
            </SubHead>
            <div className="space-y-2">
              {sourceRows.map((r) => (
                <div key={r.action} className="grid grid-cols-[auto_1fr_auto] items-center gap-x-2.5">
                  <span className="w-[130px] truncate font-sans text-[12px] text-silver" title={r.info?.label || undefined}>
                    {FR_ACTIONS[r.action] ?? r.action}
                    {r.info?.label && <span className="block truncate text-[10.5px] text-dim">{r.info.label.replace(/^(Sorcery|Incantation): /, "")}</span>}
                  </span>
                  <div className="h-2.5 overflow-hidden rounded-full border border-line-soft bg-night-700">
                    <span className="block h-full rounded-full bg-gradient-to-r from-[#3d4f75] to-frost" style={{ width: `${Math.round(r.share * 100)}%` }} />
                  </div>
                  <span className="font-sans text-[12.5px] tabular-nums text-ink">{Math.round(r.share * 100)} %</span>
                </div>
              ))}
            </div>
            {fpClamps.map(([a, c]) => {
              const gap = c.requested - c.sustainable;
              if (gap <= 0.15) return null; // passive note lives in "How it works"
              const spellName = b.sources?.[a]?.label?.replace(/^(Sorcery|Incantation): /, "");
              return (
                <p key={a} className="mt-2.5 border border-[#6e5733]/60 bg-[#3a2f1a]/40 px-2.5 py-2 text-[11.5px] leading-snug text-[#e0c48a]">
                  ⚠ Your FP pool ({b.fp_pool ?? "?"}) only sustains {Math.round(c.sustainable * 100)}% casts of{" "}
                  {spellName ?? FR_ACTIONS[a] ?? a} over a fight — you asked for {Math.round(c.requested * 100)}%, so the game plan was clamped.
                </p>
              );
            })}
          </div>
        )}

        <div className="mt-5 grid grid-cols-[auto_1fr_auto] items-center gap-x-3 gap-y-3">
          <span className="font-sans text-[11px] uppercase tracking-widest text-silver/75">Offense</span>
          <Meter value={b.offense_ratio} kind="off" />
          <span className="font-sans text-[14px] tabular-nums text-ink">×{b.offense_ratio.toFixed(2)}</span>
          <span className="font-sans text-[11px] uppercase tracking-widest text-silver/75">Survival</span>
          <Meter value={b.survival_ratio} kind="srv" />
          <span className="font-sans text-[14px] tabular-nums text-ink">×{b.survival_ratio.toFixed(2)}</span>
        </div>

        {b.kit && (
          <p className="mt-3 text-[11.5px] leading-snug text-dim">
            Kit: ×{b.kit.factor.toFixed(3)} on the shown damage (
            {Object.entries(b.kit.details).map(([n, d]) => `${n} ×${d.factor}`).join(" · ")})
          </p>
        )}

        {(b.synergy.length > 0 || b.accessory_hunt.length > 0) && (
          <div className="mt-5 rounded-sm border border-gold-deep/30 bg-night-900/40 p-4">
            <SubHead hint="During the expedition: what to pick up first to strengthen THIS build.">
              Hunt in-run
            </SubHead>
            {b.synergy.length > 0 && (
              <>
                <p className="mb-2 text-[12px] leading-snug text-silver/70">Weapon affinities & affixes to prioritize:</p>
                <div className="flex flex-wrap gap-2">
                  {b.synergy.map((s, i) => (
                    <SynergyChip key={i} s={s} />
                  ))}
                </div>
              </>
            )}
            {b.accessory_hunt.length > 0 && (
              <>
                <p className="mb-2 mt-3.5 text-[12px] leading-snug text-silver/70">Talismans (gain on the build's score):</p>
                <div className="flex flex-wrap gap-2.5">
                  {b.accessory_hunt.map((a) => (
                    <div key={a.id} className="flex w-[72px] flex-col items-center gap-1" title={a.name}>
                      <div className="flex h-[52px] w-[52px] items-center justify-center rounded-sm border border-line/50 bg-night-800/70" style={{ boxShadow: "inset 0 0 12px rgba(0,0,0,0.6)" }}>
                        {a.icon ? <img src={a.icon} alt="" onError={hide} className="h-[46px] w-[46px] object-contain" /> : <span className="text-[20px] text-gold-deep">◆</span>}
                      </div>
                      <span className="font-sans text-[11.5px] font-medium tabular-nums text-relic-green">+{(100 * a.gain).toFixed(0)} %</span>
                      <span className="line-clamp-2 w-full text-center text-[9.5px] leading-tight text-silver/70">{a.name}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        <div className="my-5 h-px bg-line-soft" />

        {/* everything expert now lives in a full-viewport modal — the column
            stays clean, the reasoning is one click away (user request 17/07) */}
        <button
          onClick={() => setExplain(true)}
          className="group flex items-center gap-2.5 border border-gold-deep/50 bg-night-900/40 px-4 py-3 font-display text-[12px] uppercase tracking-widest2 text-gold-bright transition hover:border-gold/70 hover:bg-gold/5"
        >
          <Compass className="h-4 w-4 transition group-hover:rotate-45" /> How it works
          <span className="font-sans text-[10px] normal-case tracking-normal text-dim">score · sources · relics · calibration</span>
        </button>
      </div>

      {/* ===== RIGHT — relics ===== */}
      <div className="flex min-h-0 flex-col">
        <div className="mb-4 flex items-baseline gap-2.5">
          <span className="font-display text-[18px] tracking-wide text-gold-bright">◆ {b.vessel}</span>
          <span className="font-sans text-[12.5px] text-silver/70">— {b.picks.length} relic{b.picks.length > 1 ? "s" : ""} equipped</span>
        </div>
        <div className="flex min-h-0 flex-1 flex-col gap-5">
          <RelicRow label="Normal relics" relics={normal} />
          <RelicRow label="Deep relics" relics={deep} locked={deep.length === 0} />
        </div>
      </div>

      {explain && <HowItWorks b={b} mode={mode} character={character} onClose={() => setExplain(false)} />}
    </div>
  );
}
