import { AnimatePresence, motion } from "framer-motion";
import { Scene } from "./Scene";
import { Frame } from "./ui/Frame";
import { Roster } from "./Roster";
import { ContextPanel } from "./ContextPanel";
import { CHARACTER_LORE } from "@/lib/labels";
import type { Meta } from "@/lib/api";
import type { FormState } from "@/lib/form";

// Identity plate — CENTERED over the stage (the area left of the side panel),
// so it sits just left of the hero and never slides under the panel where the
// lore line used to be clipped.
function HeroName({ name }: { name: string }) {
  const lore = CHARACTER_LORE[name] ?? { title: name, role: "", line: "" };
  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-8 right-[484px] z-10 flex justify-center px-6">
      <AnimatePresence mode="wait">
        <motion.div
          key={name}
          className="w-[min(540px,100%)] text-center"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.4 }}
        >
          <div className="eyebrow text-gold/75">{lore.role}</div>
          <h2 className="mt-1 font-display text-[clamp(30px,3.6vw,48px)] font-semibold leading-none tracking-wider text-ink text-glow-cold">
            {name}
          </h2>
          <div className="mt-1.5 font-serif text-[15px] italic text-silver/80">{lore.title}</div>
          <p className="mx-auto mt-1.5 max-w-md text-[12.5px] leading-relaxed text-dim">{lore.line}</p>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

export function Rite({
  meta,
  form,
  patch,
  onOptimize,
  busy,
}: {
  meta: Meta;
  form: FormState;
  patch: (p: Partial<FormState>) => void;
  onOptimize: () => void;
  busy: boolean;
}) {
  const selectHero = (name: string) => {
    const hero = meta.characters.find((h) => h.name === name);
    const levels = hero?.levels ?? [15];
    const level = levels.includes(form.level) ? form.level : levels.includes(15) ? 15 : levels[levels.length - 1];
    patch({ character: name, level });
  };

  return (
    <div className="relative h-screen w-full overflow-hidden">
      <Scene name={form.character} />

      {/* title */}
      <div className="pointer-events-none absolute left-1/2 top-4 z-20 -translate-x-1/2 text-center">
        <h1 className="font-display text-[clamp(22px,2.6vw,32px)] font-semibold leading-none tracking-[0.16em] text-glow-gold">
          <span className="bg-gradient-to-b from-[#f0e6c8] via-gold to-gold-deep bg-clip-text text-transparent">EVIL</span>
          <span className="bg-gradient-to-b from-[#dfe6f2] via-silver to-[#5b6c86] bg-clip-text text-transparent">NIGHTREIGN</span>
        </h1>
      </div>

      {/* roster (left) — compact character-select grid */}
      <div className="absolute left-5 top-[86px] z-20 w-[336px]">
        <Frame className="p-3">
          <div className="mb-2.5 px-1">
            <span className="eyebrow text-silver/70">Nightfarer</span>
          </div>
          <Roster characters={meta.characters} value={form.character} onSelect={selectHero} />
        </Frame>
      </div>

      {/* context (right) — full-height side panel, flush to the edge */}
      <aside className="absolute inset-y-0 right-0 z-20 flex w-[484px] flex-col border-l border-gold-deep/45 bg-gradient-to-b from-night-900/88 to-night-900/94 px-7 pb-6 pt-7 shadow-[-24px_0_70px_-30px_rgba(0,0,0,0.85)] backdrop-blur-xl">
        <span aria-hidden className="pointer-events-none absolute inset-y-0 left-0 w-px bg-gradient-to-b from-transparent via-gold/40 to-transparent" />
        <ContextPanel meta={meta} form={form} patch={patch} onOptimize={onOptimize} busy={busy} />
      </aside>

      {/* hero name plate */}
      <HeroName name={form.character} />
    </div>
  );
}
