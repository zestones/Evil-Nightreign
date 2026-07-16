import { cn } from "@/lib/cn";
import { faceArt, type HeroMeta } from "@/lib/api";

const dropOnError = (e: React.SyntheticEvent<HTMLImageElement>) => {
  e.currentTarget.remove();
};

/** Compact character-select grid (icon tiles + name), like the game. */
export function Roster({
  characters,
  value,
  onSelect,
}: {
  characters: HeroMeta[];
  value: string;
  onSelect: (name: string) => void;
}) {
  return (
    <div className="grid grid-cols-3 gap-2.5">
      {characters.map((h) => {
        const on = h.name === value;
        return (
          <button key={h.name} onClick={() => onSelect(h.name)} className="group flex flex-col items-center gap-1.5">
            <span
              className={cn(
                "relative aspect-square w-full overflow-hidden border bg-night-900 transition-all duration-200",
                on
                  ? "border-frost/70 shadow-[0_0_22px_-4px_rgba(143,182,230,0.85)]"
                  : "border-line/50 group-hover:border-line-bright"
              )}
            >
              <span className="absolute inset-0 flex items-center justify-center font-display text-xl text-silver/30">{h.name[0]}</span>
              <img
                src={faceArt(h.name)}
                alt=""
                onError={dropOnError}
                className={cn(
                  "absolute inset-0 h-full w-full object-cover object-[50%_32%] transition-transform duration-300",
                  on ? "scale-[1.06]" : "group-hover:scale-[1.08]"
                )}
              />
              {/* selected inner ring + corner ticks */}
              {on && (
                <>
                  <span className="pointer-events-none absolute inset-0 ring-1 ring-inset ring-frost/50" />
                  <span className="pointer-events-none absolute left-0 top-0 h-2 w-2 border-l border-t border-frost" />
                  <span className="pointer-events-none absolute right-0 top-0 h-2 w-2 border-r border-t border-frost" />
                  <span className="pointer-events-none absolute bottom-0 left-0 h-2 w-2 border-b border-l border-frost" />
                  <span className="pointer-events-none absolute bottom-0 right-0 h-2 w-2 border-b border-r border-frost" />
                </>
              )}
              {/* bottom fade so the name reads over the portrait */}
              <span className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-night-900/90 to-transparent" />
            </span>
            <span className={cn("font-display text-[10.5px] uppercase tracking-wide transition-colors", on ? "text-gold-bright" : "text-silver/80 group-hover:text-ink")}>
              {h.name}
            </span>
          </button>
        );
      })}
    </div>
  );
}
