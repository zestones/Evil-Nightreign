import { motion } from "framer-motion";
import { Swords } from "lucide-react";
import { Frame } from "./ui/Frame";
import { SocketRow } from "./Sockets";
import { cn } from "@/lib/cn";
import { FR_ACTIONS, FR_TYPES, FR_STATUS, STATUS_COLOR, pctDelta } from "@/lib/labels";
import type { Build, Mode } from "@/lib/api";

const hide = (e: React.SyntheticEvent<HTMLImageElement>) => {
  e.currentTarget.style.display = "none";
};

function SectionHead({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-3 flex items-center gap-2.5">
      <span className="eyebrow text-gold/75">{children}</span>
      <span className="h-px flex-1 bg-gradient-to-r from-gold-deep/30 to-transparent" />
    </div>
  );
}

function Chip({
  children,
  ghost,
  color,
}: {
  children: React.ReactNode;
  ghost?: boolean;
  color?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 border px-2.5 py-1 font-sans text-[12px] tabular-nums",
        ghost
          ? "border-dashed border-line/60 text-dim"
          : "border-line/70 bg-night-700/50 text-silver"
      )}
      style={color ? { borderColor: color } : undefined}
    >
      {children}
    </span>
  );
}

function Meter({ value, kind }: { value: number; kind: "off" | "srv" }) {
  return (
    <div className="h-[9px] overflow-hidden rounded-full border border-line-soft bg-night-700">
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

export function BuildCard({ b, index, mode, fill = false }: { b: Build; index: number; mode: Mode; fill?: boolean }) {
  const prime = index === 0;
  const star = b.generic ? "*" : "";

  const pill = (label: string, value: string) => (
    <span className="border border-line/70 bg-night-700/60 px-2.5 py-1 font-sans text-[12.5px] tabular-nums text-gold-bright">
      <span className="mr-1 text-[10px] uppercase tracking-wider text-dim">{label}</span>
      {value}
    </span>
  );

  const mults = Object.entries(b.attack_multipliers).filter(([, m]) => m > 1.001);
  const stats = Object.entries(b.stat_bonuses);
  const status = Object.entries(b.status);
  const actions = Object.entries(b.actions_hit);

  return (
      <Frame tone={prime ? "prime" : "cold"} className={cn("p-5 sm:p-6", fill && "flex h-full flex-col")}>
        {/* header */}
        <div className="flex flex-wrap items-center gap-3 border-b border-line-soft pb-4">
          <span
            className={cn(
              "font-display text-[14px] font-semibold uppercase tracking-wider",
              prime
                ? "border border-gold px-3 py-1 text-[#221a0a]"
                : "border border-gold-deep/70 px-3 py-1 text-gold-bright"
            )}
            style={
              prime
                ? { background: "linear-gradient(180deg,#e8cf8a,#7c6531)", boxShadow: "0 0 16px -4px rgba(201,162,74,0.8)" }
                : undefined
            }
          >
            #{index + 1}
            {prime ? " · Prime" : ""}
          </span>
          <span className="font-display text-[15px] tracking-wide text-ink">
            S <b className="text-gold-bright">{b.score.toFixed(3)}</b>
          </span>
          <div className="ml-auto flex flex-wrap gap-2">
            {b.generic && pill("boost", `×${b.offense_ratio.toFixed(2)}`)}
            {pill("dmg/coup", `${Math.round(b.absolute_offense)}${star}`)}
            {b.absolute_dps != null && pill("dmg/s", `${Math.round(b.absolute_dps)}${star}`)}
          </div>
        </div>

        <div className={cn("mt-5 grid grid-cols-1 gap-x-8 gap-y-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.22fr)]", fill && "min-h-0 flex-1 lg:overflow-hidden")}>
          {/* left: weapon + meters + chips */}
          <div className={cn(fill && "flex h-full flex-col justify-center overflow-hidden pr-1")}>
            <SectionHead>{mode === "generic" ? "Arme de référence" : "Arme à chasser"}</SectionHead>
            <div className="flex items-center gap-4">
              <div
                className="flex h-[72px] w-[72px] flex-none items-center justify-center border border-gold-deep/70 p-1.5"
                style={{
                  background: "radial-gradient(circle at 50% 40%, rgba(201,162,74,0.14), rgba(8,10,16,0.9) 70%)",
                  boxShadow: "inset 0 0 18px rgba(0,0,0,0.6), 0 0 18px -8px rgba(201,162,74,0.6)",
                }}
              >
                {b.weapon_icon ? (
                  <img src={b.weapon_icon} alt="" onError={hide} className="h-full w-full object-contain drop-shadow" />
                ) : (
                  <Swords className="h-7 w-7 text-gold-deep" />
                )}
              </div>
              <div className="min-w-0">
                <div className="font-display text-[19px] font-semibold leading-tight text-ink">{b.weapon}</div>
                <div className="font-serif text-[13px] italic text-gold/85">{b.weapon_type}</div>
                <div className="mt-0.5 text-[12px] text-dim">vs {b.targets.join(", ")}</div>
              </div>
            </div>

            {b.weapon_alternatives.length > 0 && (
              <div className="mt-3">
                <div className="mb-1.5 font-sans text-[10px] uppercase tracking-[0.14em] text-faint">Replis in-run</div>
                <div className="flex flex-wrap gap-2">
                  {b.weapon_alternatives.map(([n, r], i) => (
                    <span key={i} className="border border-line/60 bg-night-700/50 px-2.5 py-1 text-[12px] text-silver">
                      {n} <span className="font-sans tabular-nums text-dim">{pctDelta(r)}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-5 grid grid-cols-[auto_1fr_auto] items-center gap-x-3 gap-y-2.5">
              <span className="font-sans text-[10.5px] uppercase tracking-widest text-dim">Offense</span>
              <Meter value={b.offense_ratio} kind="off" />
              <span className="font-sans text-[12.5px] tabular-nums text-silver">×{b.offense_ratio.toFixed(2)}</span>
              <span className="font-sans text-[10.5px] uppercase tracking-widest text-dim">Survie</span>
              <Meter value={b.survival_ratio} kind="srv" />
              <span className="font-sans text-[12.5px] tabular-nums text-silver">×{b.survival_ratio.toFixed(2)}</span>
            </div>

            <div className="mt-5 space-y-3.5">
              {mults.length > 0 && (
                <ChipStrip title="Multiplicateurs">
                  {mults.map(([t, m]) => (
                    <Chip key={t}>
                      {FR_TYPES[t] ?? t} <b className="text-gold-bright">×{m.toFixed(3)}</b>
                    </Chip>
                  ))}
                </ChipStrip>
              )}
              {status.length > 0 && (
                <ChipStrip title="Statuts">
                  {status.map(([st, info]) => (
                    <Chip key={st} color={STATUS_COLOR[st]}>
                      {FR_STATUS[st] ?? st} : proc ~{Math.round(info.proc)}
                      <span className="ml-1 text-gold/80">
                        1er ≈ {Math.round(info.first_hits)} · {info.fight_procs.toFixed(1)}/combat
                      </span>
                    </Chip>
                  ))}
                </ChipStrip>
              )}
              {stats.length > 0 && (
                <ChipStrip title="Stats">
                  {stats.map(([f, v]) => (
                    <Chip key={f}>
                      {f.replace("stat", "")} <b className="text-gold-bright">+{v}</b>
                    </Chip>
                  ))}
                </ChipStrip>
              )}
              {actions.length > 0 && (
                <ChipStrip title="Actions">
                  {actions.map(([a, v]) => (
                    <Chip key={a}>
                      {FR_ACTIONS[a] ?? a} <b className="text-gold-bright">≈ {Math.round(v)}</b>
                      <span className="text-dim">/coup</span>
                    </Chip>
                  ))}
                </ChipStrip>
              )}
              {b.top_effects.length > 0 && (
                <ChipStrip title="Effets comptés">
                  {b.top_effects.map((e, i) => (
                    <Chip key={i}>
                      {e.key} <b className="text-gold-bright">×{e.mult.toFixed(2)}</b>
                      {e.action !== "*" && <span className="text-gold/80">{FR_ACTIONS[e.action] ?? e.action}</span>}
                    </Chip>
                  ))}
                </ChipStrip>
              )}
              {b.ignored_effects.length > 0 && (
                <ChipStrip title="Ignorés (profil)">
                  {b.ignored_effects.map((e, i) => (
                    <Chip key={i} ghost>
                      {e.key} ×{e.mult.toFixed(2)}
                      <span>{FR_ACTIONS[e.action] ?? e.action}</span>
                    </Chip>
                  ))}
                </ChipStrip>
              )}
            </div>
          </div>

          {/* right: vessel + relic sockets */}
          <div className={cn(fill && "flex h-full min-h-0 flex-col pr-1")}>
            <SectionHead>Vessel &amp; Reliques</SectionHead>
            <div className="mb-3 font-display text-[14px] tracking-wide text-gold-bright">◆ {b.vessel}</div>
            <div className={cn("space-y-4", fill && "flex min-h-0 flex-1 flex-col gap-4 space-y-0")}>
              <SocketRow picks={b.picks} kind="normal" label="Reliques normales" grow={fill} />
              <SocketRow picks={b.picks} kind="deep" label="Reliques profondes" grow={fill} />
            </div>
          </div>
        </div>
      </Frame>
  );
}

function ChipStrip({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 font-sans text-[10px] uppercase tracking-[0.14em] text-faint">{title}</div>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}
