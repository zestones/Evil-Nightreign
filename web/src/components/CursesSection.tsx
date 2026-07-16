import { useState } from "react";
import { Skull, Swords, Droplet, Coins, Check, Ban, AlertTriangle, ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";
import type { CurseMeta, Meta } from "@/lib/api";
import type { FormState } from "@/lib/form";

const GROUPS: { key: string; label: string; icon: typeof Swords }[] = [
  { key: "combat", label: "Combat", icon: Swords },
  { key: "survie", label: "Survie & statut", icon: Droplet },
  { key: "utilitaire", label: "Utilitaire", icon: Coins },
];

// The Deep-of-Night curse controls — a concern of its own, shown only under Deep
// of Night. A master switch governs the whole concern (score + veto); below it,
// the curses present in the owned relics, grouped by concern in collapsible
// groups so it never becomes a wall of text.
export function CursesSection({ meta, form, patch }: {
  meta: Meta;
  form: FormState;
  patch: (p: Partial<FormState>) => void;
}) {
  const on = form.countDebuffs;
  const refused = new Set(form.refusedCurses);
  const [open, setOpen] = useState<Record<string, boolean>>({ combat: true });

  const setRefused = (keys: string[]) => patch({ refusedCurses: keys });
  const toggleCurse = (k: string) =>
    setRefused(refused.has(k) ? form.refusedCurses.filter((x) => x !== k) : [...form.refusedCurses, k]);

  const byGroup: Record<string, CurseMeta[]> = {};
  for (const c of meta.curses) (byGroup[c.group] ??= []).push(c);
  const excluded = on ? meta.cursed_relic_curses.filter((s) => s.some((k) => refused.has(k))).length : 0;

  const groupRefusedCount = (g: string) => (byGroup[g] ?? []).filter((c) => refused.has(c.key)).length;
  const refuseAll = (g: string, refuse: boolean) => {
    const keys = (byGroup[g] ?? []).map((c) => c.key);
    setRefused(refuse ? [...new Set([...form.refusedCurses, ...keys])] : form.refusedCurses.filter((k) => !keys.includes(k)));
  };

  return (
    <section>
      <div className="mb-2.5 flex items-center gap-2">
        <Skull className="h-4 w-4 text-gold" />
        <span className="font-display text-[12px] uppercase tracking-widest2 text-gold">Malédictions</span>
        <span className="font-sans text-[10px] uppercase tracking-[0.13em] text-silver/45">Deep of Night</span>
        <span className="h-px flex-1 bg-gradient-to-r from-gold-deep/50 to-transparent" />
      </div>
      <div className="rounded-sm border border-line/50 bg-night-800/45 p-4">
        {/* master switch — governs the whole concern (score + veto) */}
        <button
          onClick={() => patch({ countDebuffs: !on })}
          title="Prendre en compte les malédictions : score des malus chiffrables (pire cas) + exclusion des malus refusés"
          className={cn(
            "flex w-full items-center gap-2.5 border px-3 py-2.5 text-left text-[13px] leading-tight transition",
            on ? "border-frost/55 bg-frost/10 text-ink" : "border-line/55 bg-night-700/40 text-silver hover:border-line-bright hover:text-ink"
          )}
        >
          <span className={cn("flex h-4 w-4 flex-none rotate-45 items-center justify-center border", on ? "border-frost bg-frost/30 shadow-[0_0_7px_rgba(143,182,230,0.7)]" : "border-line")}>
            {on && <Check className="h-2.5 w-2.5 -rotate-45 text-frost" strokeWidth={3} />}
          </span>
          Prendre en compte les malédictions
        </button>

        {on ? (
          <>
            <p className="mt-2.5 text-[12px] leading-snug text-dim">
              Les malus <span className="text-frost/80">chiffrables</span> pèsent le score ; refuse ceux que tu ne tolères pas pour exclure leurs reliques.
            </p>

            {GROUPS.map(({ key: g, label, icon: Icon }) => {
              const list = byGroup[g];
              if (!list?.length) return null;
              const rc = groupRefusedCount(g);
              const isOpen = open[g];
              return (
                <div key={g} className="mt-3 border-t border-line/30 pt-2.5 first:mt-3.5">
                  <div className="flex items-center gap-2">
                    <button onClick={() => setOpen((o) => ({ ...o, [g]: !o[g] }))} className="flex flex-1 items-center gap-2 text-left">
                      <ChevronDown className={cn("h-4 w-4 flex-none text-silver/60 transition", isOpen && "rotate-180")} />
                      <Icon className="h-4 w-4 flex-none text-silver/80" />
                      <span className="font-sans text-[12.5px] font-medium text-silver">{label}</span>
                      <span className="text-[11px] text-dim/70">{list.length}{rc > 0 && <span className="text-[#d99]"> · {rc} refusé{rc > 1 ? "s" : ""}</span>}</span>
                    </button>
                    {isOpen && (
                      <button
                        onClick={() => refuseAll(g, rc < list.length)}
                        className="flex-none text-[11px] text-silver/60 underline-offset-2 hover:text-silver hover:underline"
                      >
                        {rc < list.length ? "tout refuser" : "tout accepter"}
                      </button>
                    )}
                  </div>
                  {isOpen && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {list.map((c) => {
                        const off = refused.has(c.key);
                        return (
                          <button
                            key={c.key}
                            onClick={() => toggleCurse(c.key)}
                            title={off ? "Refusé — reliques exclues (clique pour accepter)" : c.scored ? "Compté dans le score (pire cas). Clique pour refuser." : "Affiché, non chiffré. Clique pour refuser."}
                            className={cn(
                              "flex items-center gap-1.5 rounded-sm border px-2 py-1 text-[12px] leading-tight transition",
                              off
                                ? "border-[#8f4747]/70 bg-[#3a1e1e]/50 text-[#dca0a0] line-through"
                                : "border-line/50 bg-night-700/40 text-silver hover:border-line-bright hover:text-ink"
                            )}
                          >
                            {off ? <Ban className="h-3 w-3 flex-none text-[#c97b7b]" /> : <Check className="h-3 w-3 flex-none text-frost/70" />}
                            <span className="no-underline">{c.label}</span>
                            {c.scored && !off && (
                              <span className="rounded-sm bg-frost/15 px-1 py-px text-[8.5px] uppercase tracking-wide text-frost/80">chiffré</span>
                            )}
                            <span className="text-[10px] text-dim/50">×{c.count}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}

            {excluded > 0 && (
              <div className="mt-3.5 flex items-center gap-2 border-t border-line/40 pt-2.5 text-[12.5px] text-[#d8a878]">
                <AlertTriangle className="h-4 w-4 flex-none" />
                {excluded} relique{excluded > 1 ? "s" : ""} exclue{excluded > 1 ? "s" : ""} du pool
              </div>
            )}
          </>
        ) : (
          <p className="mt-2.5 text-[12px] italic leading-snug text-dim/70">
            Malédictions ignorées — ni comptées dans le score, ni exclues. Réactive pour gérer les malus.
          </p>
        )}
      </div>
    </section>
  );
}
