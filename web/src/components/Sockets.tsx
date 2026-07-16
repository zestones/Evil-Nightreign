import { Lock, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/cn";
import { RELIC_HEX } from "@/lib/labels";
import type { Pick, Effect } from "@/lib/api";

const hide = (e: React.SyntheticEvent<HTMLImageElement>) => {
  e.currentTarget.style.display = "none";
};

function EffectIcon({ url, active, color }: { url: string | null; active: boolean; color: string }) {
  if (url) {
    return <img src={url} alt="" onError={hide} className={cn("mt-px h-[24px] w-[24px] flex-none object-contain", !active && "opacity-40 grayscale")} />;
  }
  return <span className="mt-1.5 h-2 w-2 flex-none rotate-45" style={{ background: active ? color : "#465268" }} />;
}

// Deep of Night curse — the blue drawback the game shows under its paired buff.
// A curse that is scored AND applied here bites the score ("comptée"); an
// out-of-axis one is surfaced but not counted ("non chiffrée"); a situational
// one that isn't engaged shows plainly (its note explains when it would bite).
function CurseLine({ e }: { e: Effect }) {
  const counts = !!e.scored && e.active;
  return (
    <div className="ml-[36px] mt-1.5 flex items-start gap-1.5" title={e.note ?? undefined}>
      <span className="mt-px flex-none text-[#5b78a8]">↳</span>
      <span className={cn("text-[12.5px] leading-snug", counts ? "text-[#82a9de]" : "italic text-[#6f88b0]/75")}>
        {e.text}
        {counts && (
          <span className="ml-1.5 rounded-sm bg-[#2b3a55]/50 px-1 py-px align-middle text-[9.5px] uppercase tracking-wide text-[#9fc0ec] ring-1 ring-inset ring-[#3a557f]/50">
            comptée
          </span>
        )}
        {!e.scored && <span className="ml-1.5 align-middle text-[10px] not-italic text-dim/55">· non chiffrée</span>}
      </span>
    </div>
  );
}

function RelicCard({ p }: { p: Pick }) {
  const c = RELIC_HEX[p.color] ?? "#c9a24a";
  const slot = RELIC_HEX[p.slot_color] ?? c;
  return (
    <div
      className="group relative flex h-full items-center gap-5 rounded-sm border bg-gradient-to-b from-night-800/55 to-night-900/60 px-5 py-5 transition-all duration-200 hover:-translate-y-0.5"
      style={{ borderColor: `${c}4d`, boxShadow: `inset 0 0 46px -20px ${c}` }}
    >
      {/* square relic icon + colour diamond */}
      <div className="relative flex-none">
        <div
          className="flex h-[124px] w-[124px] items-center justify-center rounded-sm border-2"
          style={{ borderColor: c, boxShadow: `0 0 30px -6px ${c}, inset 0 0 14px rgba(0,0,0,0.75)`, background: "radial-gradient(circle at 50% 42%, rgba(255,255,255,0.06), rgba(6,8,12,0.92) 72%)" }}
        >
          {p.icon ? (
            <img src={p.icon} alt="" onError={hide} className="h-[100px] w-[100px] object-contain" />
          ) : (
            <span className="text-4xl" style={{ color: c }}>◆</span>
          )}
        </div>
        <span className="absolute -bottom-1.5 -right-1.5 h-4 w-4 rotate-45 border border-night-900" style={{ background: slot, boxShadow: `0 0 9px ${slot}` }} title={`slot ${p.slot_color}`} />
      </div>

      {/* name + effects */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-serif text-[20px] font-medium leading-tight text-ink">{p.name}</span>
          {p.unique && <span className="border border-gold-deep/70 bg-black/40 px-1.5 py-px font-sans text-[10px] uppercase tracking-wider text-gold-bright">unique</span>}
        </div>
        <ul className="mt-3.5 space-y-3">
          {p.effects.filter((e) => !e.curse).map((e, k) => (
            <li key={k} className="text-[14px] leading-snug">
              <div className="flex items-start gap-3">
                <EffectIcon url={e.icon} active={e.active} color={c} />
                <span className="pt-0.5">
                  <span className={cn(e.active ? "text-ink" : "text-faint line-through")}>{e.text}</span>
                  {e.active && e.tradeoff && (
                    <AlertTriangle className="ml-1.5 inline h-3.5 w-3.5 -translate-y-px text-[#d8a03a]" aria-label="compromis" />
                  )}
                  {!e.active && e.reason && (
                    <span className="ml-1.5 text-[11.5px] italic text-dim/70">— {e.reason}</span>
                  )}
                </span>
              </div>
              {p.effects
                .filter((cu) => cu.curse && cu.pair === k)
                .map((cu, j) => (
                  <CurseLine key={j} e={cu} />
                ))}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function LockedCard() {
  return (
    <div className="flex h-full items-center justify-center gap-3 rounded-sm border border-dashed border-line/40 bg-night-900/25 px-5 py-8">
      <Lock className="h-6 w-6 flex-none text-faint" />
      <span className="text-[13px] text-dim">Deep of Night ≥ 1 pour débloquer</span>
    </div>
  );
}

export function RelicRow({ label, relics, locked }: { label: string; relics: Pick[]; locked?: boolean }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="mb-2.5 flex items-center gap-2">
        <span className="font-display text-[11px] uppercase tracking-widest2 text-gold/85">{label}</span>
        <span className="h-px flex-1 bg-gradient-to-r from-gold-deep/40 to-transparent" />
      </div>
      <div className="grid min-h-0 flex-1 grid-cols-3 gap-3.5">
        {locked ? [0, 1, 2].map((i) => <LockedCard key={i} />) : relics.map((p, i) => <RelicCard key={i} p={p} />)}
      </div>
    </div>
  );
}
