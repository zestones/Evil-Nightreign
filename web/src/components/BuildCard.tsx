import { useState } from "react";
import { Swords, ChevronDown } from "lucide-react";
import { RelicRow } from "./Sockets";
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
    return <span className="inline-flex items-center gap-1.5 border px-2.5 py-1 font-sans text-[12.5px] text-silver" style={{ borderColor: "#c9a24a66" }}><ElemImg type="phys" /> Tous types <b className="tabular-nums text-gold-bright">×{s.mult.toFixed(2)}</b></span>;
  if (s.kind === "damage")
    return <span className="inline-flex items-center gap-1.5 border px-2.5 py-1 font-sans text-[12.5px] text-silver" style={{ borderColor: `${ELEMENT_HEX[s.type] ?? "#c9a24a"}88` }}><ElemImg type={s.type} /> {FR_TYPES[s.type] ?? s.type} <b className="tabular-nums text-gold-bright">×{s.mult.toFixed(2)}</b></span>;
  if (s.kind === "status")
    return <span className="inline-flex items-center gap-1 border px-2.5 py-1 font-sans text-[12.5px] text-silver" style={{ borderColor: `${STATUS_COLOR[s.type] ?? "#c9a24a"}88` }}><span className="h-2 w-2 rotate-45" style={{ background: STATUS_COLOR[s.type] ?? "#c9a24a" }} /> Statut {FR_STATUS[s.type] ?? s.type}</span>;
  return <span className="inline-flex items-center gap-1 border border-line/70 bg-night-700/50 px-2.5 py-1 font-sans text-[12.5px] text-silver">Scaling {FR_STATS[s.type] ?? s.type}</span>;
}

const hide = (e: React.SyntheticEvent<HTMLImageElement>) => {
  e.currentTarget.style.display = "none";
};

function SubHead({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-2 flex items-center gap-2.5">
      <span className="font-display text-[11px] uppercase tracking-widest2 text-gold/80">{children}</span>
      <span className="h-px flex-1 bg-gradient-to-r from-gold-deep/30 to-transparent" />
    </div>
  );
}

function Chip({ children, ghost, color }: { children: React.ReactNode; ghost?: boolean; color?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 border px-3 py-1.5 font-sans text-[13px] tabular-nums",
        ghost ? "border-dashed border-line/60 text-dim" : "border-line/70 bg-night-700/50 text-silver"
      )}
      style={color ? { borderColor: color } : undefined}
    >
      {children}
    </span>
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

function BigStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-sm border border-line/50 bg-night-900/40 px-3 py-2.5 text-center">
      <div className="font-sans text-[26px] font-semibold leading-none tabular-nums text-gold-bright">{value}</div>
      <div className="mt-1 font-sans text-[10px] uppercase tracking-[0.14em] text-silver/70">{label}</div>
    </div>
  );
}

export function BuildCard({ b, index, mode }: { b: Build; index: number; mode: Mode }) {
  const [details, setDetails] = useState(true);
  const prime = index === 0;
  const star = b.generic ? "*" : "";
  const normal = b.picks.filter((p) => p.kind === "normal");
  const deep = b.picks.filter((p) => p.kind === "deep");

  const mults = Object.entries(b.attack_multipliers).filter(([, m]) => m > 1.001);
  const stats = Object.entries(b.stat_bonuses);
  const status = Object.entries(b.status);
  const actions = Object.entries(b.actions_hit);

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

        <SubHead>{mode === "generic" ? "Arme de référence" : "Arme à chasser"}</SubHead>
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
                  <div className="font-sans text-[12px] font-medium tabular-nums text-[#cf9074]">{pctDelta(a.ratio)}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {b.synergy.length > 0 && (
          <div className="mt-5">
            <SubHead>Synergies à chasser</SubHead>
            <p className="mb-2.5 text-[12.5px] leading-snug text-silver/75">Sur les armes trouvées en run, priorise l'affinité et les affixes :</p>
            <div className="flex flex-wrap gap-2">
              {b.synergy.map((s, i) => (
                <SynergyChip key={i} s={s} />
              ))}
            </div>
          </div>
        )}

        <div className="my-5 h-px bg-line-soft" />

        <div className="grid grid-cols-2 gap-3">
          {b.absolute_dps != null && <BigStat label="dégâts / s" value={`${Math.round(b.absolute_dps)}${star}`} />}
          <BigStat label="dégâts / coup" value={`${Math.round(b.absolute_offense)}${star}`} />
        </div>

        <div className="mt-5 grid grid-cols-[auto_1fr_auto] items-center gap-x-3 gap-y-3">
          <span className="font-sans text-[11px] uppercase tracking-widest text-silver/75">Offense</span>
          <Meter value={b.offense_ratio} kind="off" />
          <span className="font-sans text-[14px] tabular-nums text-ink">×{b.offense_ratio.toFixed(2)}</span>
          <span className="font-sans text-[11px] uppercase tracking-widest text-silver/75">Survie</span>
          <Meter value={b.survival_ratio} kind="srv" />
          <span className="font-sans text-[14px] tabular-nums text-ink">×{b.survival_ratio.toFixed(2)}</span>
        </div>

        <div className="my-5 h-px bg-line-soft" />

        <button
          onClick={() => setDetails((d) => !d)}
          className="flex items-center gap-2 font-display text-[12px] uppercase tracking-widest2 text-silver/80 transition hover:text-ink"
        >
          <ChevronDown className={cn("h-4 w-4 transition", details && "rotate-180")} /> Détails du build
        </button>

        {details && (
          <div className="mt-4 space-y-4">
            {mults.length > 0 && (
              <div>
                <SubHead>Multiplicateurs</SubHead>
                <div className="flex flex-wrap gap-2">{mults.map(([t, m]) => <Chip key={t}><ElemImg type={t} /> {FR_TYPES[t] ?? t} <b className="text-gold-bright">×{m.toFixed(3)}</b></Chip>)}</div>
              </div>
            )}
            {status.length > 0 && (
              <div>
                <SubHead>Statuts</SubHead>
                <div className="flex flex-wrap gap-2">
                  {status.map(([st, info]) => (
                    <Chip key={st} color={STATUS_COLOR[st]}>
                      {FR_STATUS[st] ?? st} : proc ~{Math.round(info.proc)}
                      <span className="ml-1 text-gold/80">1er ≈ {Math.round(info.first_hits)} · {info.fight_procs.toFixed(1)}/combat</span>
                    </Chip>
                  ))}
                </div>
              </div>
            )}
            {stats.length > 0 && (
              <div>
                <SubHead>Stats</SubHead>
                <div className="flex flex-wrap gap-2">{stats.map(([f, v]) => <Chip key={f}>{f.replace("stat", "")} <b className="text-gold-bright">+{v}</b></Chip>)}</div>
              </div>
            )}
            {actions.length > 0 && (
              <div>
                <SubHead>Actions</SubHead>
                <div className="flex flex-wrap gap-2">{actions.map(([a, v]) => <Chip key={a}>{FR_ACTIONS[a] ?? a} <b className="text-gold-bright">≈ {Math.round(v)}</b><span className="text-dim">/coup</span></Chip>)}</div>
              </div>
            )}
            {b.top_effects.length > 0 && (
              <div>
                <SubHead>Effets comptés</SubHead>
                <div className="flex flex-wrap gap-2">
                  {b.top_effects.map((e, i) => (
                    <Chip key={i}>{e.key} <b className="text-gold-bright">×{e.mult.toFixed(2)}</b>{e.action !== "*" && <span className="text-gold/80">{FR_ACTIONS[e.action] ?? e.action}</span>}</Chip>
                  ))}
                </div>
              </div>
            )}
            {b.ignored_effects.length > 0 && (
              <div>
                <SubHead>Ignorés par ton profil</SubHead>
                <p className="mb-2.5 text-[12.5px] leading-snug text-silver/70">Effets liés à une action que tu n'as pas déclarée (ex. critiques) — ils ne comptent pas ici.</p>
                <div className="flex flex-wrap gap-2">
                  {b.ignored_effects.map((e, i) => (
                    <Chip key={i} ghost>{e.key} ×{e.mult.toFixed(2)}<span className="text-gold/70">{FR_ACTIONS[e.action] ?? e.action}</span></Chip>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ===== RIGHT — relics ===== */}
      <div className="flex min-h-0 flex-col">
        <div className="mb-4 flex items-baseline gap-2.5">
          <span className="font-display text-[18px] tracking-wide text-gold-bright">◆ {b.vessel}</span>
          <span className="font-sans text-[12.5px] text-silver/70">— {b.picks.length} relique{b.picks.length > 1 ? "s" : ""} équipée{b.picks.length > 1 ? "s" : ""}</span>
        </div>
        <div className="flex min-h-0 flex-1 flex-col gap-5">
          <RelicRow label="Reliques normales" relics={normal} />
          <RelicRow label="Reliques profondes" relics={deep} locked={deep.length === 0} />
        </div>
      </div>
    </div>
  );
}
