import { useEffect, useState } from "react";
import { ChevronLeft, Info } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { BuildCard } from "./BuildCard";
import { Tip } from "./ui/Tooltip";
import { cn } from "@/lib/cn";
import { heroArt, type Build, type Mode } from "@/lib/api";

export function Verdict({
  results,
  mode,
  character,
  don,
  onBack,
}: {
  results: Build[];
  mode: Mode;
  character: string;
  don: number;
  onBack: () => void;
}) {
  const [active, setActive] = useState(0);
  useEffect(() => setActive(0), [results]);
  const b = results[active];
  if (!b) return null;

  const modeNote =
    mode === "auto"
      ? "Exploration libre : meilleur build par type d'arme, classés par DPS (dégâts/coup × cadence). Le score S mesure le gain vs l'arme nue du même type."
      : mode === "generic"
      ? "Mode générique : reliques pour n'importe quelle arme. Regarde les Multiplicateurs ; les valeurs marquées * sont indicatives (arme physique de référence)."
      : "S = amélioration vs l'arme nue du type. Effets barrés = inactifs dans ce contexte.";

  return (
    <div className="relative flex h-screen flex-col overflow-hidden px-4 pb-4 pt-3 sm:px-6">
      {/* top bar */}
      <div className="flex flex-wrap items-center gap-3 pb-3">
        <button
          onClick={onBack}
          className="group flex items-center gap-1.5 border border-line/70 bg-night-700/50 px-3 py-2 font-display text-[11.5px] uppercase tracking-widest2 text-silver transition hover:border-frost/50 hover:text-ink"
        >
          <ChevronLeft className="h-4 w-4 transition group-hover:-translate-x-0.5" /> Le Rite
        </button>
        <span className="relative h-10 w-10 overflow-hidden border border-line/60 bg-night-900">
          <img
            src={heroArt(character)}
            alt=""
            onError={(e) => (e.currentTarget.style.visibility = "hidden")}
            className="h-full w-full scale-[1.8] object-cover object-[50%_10%]"
          />
        </span>
        <div className="mr-1">
          <div className="eyebrow text-silver/70">Le Verdict</div>
          <div className="font-display text-[15px] leading-tight tracking-wide text-ink">
            {character}
            <span className="ml-2 font-serif text-[12.5px] italic text-dim">
              {b.targets.length > 1 ? "généraliste" : `vs ${b.targets[0]}`}
            </span>
          </div>
        </div>

        {/* pager */}
        <div className="ml-auto flex items-center gap-2">
          {results.map((r, i) => (
            <button
              key={i}
              onClick={() => setActive(i)}
              className={cn(
                "flex items-center gap-2 border px-3 py-1.5 font-sans text-[12px] tabular-nums transition",
                i === active
                  ? "border-gold/70 bg-gold/10 text-gold-bright shadow-[0_0_18px_-6px_rgba(201,162,74,0.6)]"
                  : "border-line/60 bg-night-700/40 text-silver hover:border-line-bright"
              )}
            >
              <span className={cn("font-display text-[12px] uppercase tracking-wider", i === 0 && "text-gold-bright")}>
                #{i + 1}
                {i === 0 ? "·Prime" : ""}
              </span>
              <span className="text-dim">S {r.score.toFixed(3)}</span>
            </button>
          ))}
          <Tip
            content={
              <div className="space-y-1.5">
                <div>{modeNote}</div>
                {don === 0 && (
                  <div className="text-[#d8c79a]">
                    ⚠ Expédition normale : les 3 slots profonds ne sont pas inclus (choisis Deep of Night ≥ 1).
                  </div>
                )}
              </div>
            }
          >
            <button className="flex h-8 w-8 items-center justify-center border border-line/60 bg-night-700/40 text-silver transition hover:border-frost/50 hover:text-ink">
              <Info className="h-4 w-4" />
            </button>
          </Tip>
        </div>
      </div>

      {don === 0 && (
        <div className="mb-2.5 border border-[#5a4a2a] bg-[#2a2210]/40 px-3 py-1.5 text-[12px] text-[#d8c79a]">
          ⚠ Expédition normale (Deep of Night « Non ») — 3 reliques seulement. Choisis un niveau ≥ 1 pour un build à 6.
        </div>
      )}

      {/* the active build fills the rest, no page scroll */}
      <div className="min-h-0 flex-1">
        <AnimatePresence mode="wait">
          <motion.div
            key={active}
            className="h-full"
            initial={{ opacity: 0, x: 14 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -14 }}
            transition={{ duration: 0.28, ease: [0.2, 0.7, 0.3, 1] }}
          >
            <BuildCard b={b} index={active} mode={mode} fill />
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
