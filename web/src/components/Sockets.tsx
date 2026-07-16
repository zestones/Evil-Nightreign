import { cn } from "@/lib/cn";
import { RELIC_HEX } from "@/lib/labels";
import type { Pick } from "@/lib/api";

const hide = (e: React.SyntheticEvent<HTMLImageElement>) => {
  e.currentTarget.style.display = "none";
};

function Socket({ p, grow }: { p: Pick; grow?: boolean }) {
  const c = RELIC_HEX[p.color] ?? "#c9a24a";
  const slot = RELIC_HEX[p.slot_color] ?? c;
  return (
    <div
      className={cn(
        "group relative flex flex-col border border-line/60 bg-night-800/50 p-3 transition-all duration-200 hover:-translate-y-0.5",
        grow && "h-full"
      )}
      style={{ ["--c" as string]: c } as React.CSSProperties}
    >
      <span className="absolute left-2.5 top-2.5 h-2 w-2 rounded-full" style={{ background: slot, boxShadow: `0 0 7px ${slot}` }} title={`slot ${p.slot_color}`} />
      {p.unique && (
        <span className="absolute right-2 top-2 border border-gold-deep/70 bg-black/40 px-1.5 py-px font-sans text-[9px] uppercase tracking-wider text-gold-bright">
          unique
        </span>
      )}
      <div
        className={cn("mx-auto mb-2 mt-1 flex items-center justify-center rounded-full border-2", grow ? "h-[68px] w-[68px]" : "h-[54px] w-[54px]")}
        style={{
          borderColor: c,
          boxShadow: `0 0 18px -3px ${c}, inset 0 0 12px rgba(0,0,0,0.7)`,
          background: "radial-gradient(circle at 50% 42%, rgba(255,255,255,0.05), rgba(6,8,12,0.92) 72%)",
        }}
      >
        {p.icon ? (
          <img src={p.icon} alt="" onError={hide} className={cn("object-contain", grow ? "h-14 w-14" : "h-11 w-11")} />
        ) : (
          <span style={{ color: c }}>◆</span>
        )}
      </div>
      <div className="flex min-h-[2.3em] items-center justify-center text-center font-serif text-[13.5px] leading-tight text-ink">{p.name}</div>
      <ul className={cn("mt-2 space-y-1 border-t border-line-soft pt-2", grow && "flex-1")}>
        {p.effects.map((e, i) => (
          <li
            key={i}
            className={cn("relative pl-3 text-[12px] leading-snug", e.active ? "text-silver" : "text-dim line-through opacity-50")}
            title={e.active ? undefined : "inactif dans ce contexte"}
          >
            <span className="absolute left-0" style={{ color: e.active ? c : "#465268" }}>
              ◦
            </span>
            {e.text}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function SocketRow({ picks, kind, label, grow }: { picks: Pick[]; kind: "normal" | "deep"; label: string; grow?: boolean }) {
  const list = picks.filter((p) => p.kind === kind);
  if (!list.length) return null;
  return (
    <div className={cn(grow && "flex min-h-0 flex-1 flex-col")}>
      <div className="mb-2 font-sans text-[10.5px] uppercase tracking-[0.14em] text-faint">{label}</div>
      <div className={cn("grid grid-cols-1 gap-2.5 sm:grid-cols-3", grow && "min-h-0 flex-1")}>
        {list.map((p, i) => (
          <Socket key={i} p={p} grow={grow} />
        ))}
      </div>
    </div>
  );
}
