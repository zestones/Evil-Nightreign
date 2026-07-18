import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Rite } from "./components/Rite";
import { Verdict } from "./components/Verdict";
import { ThemedTooltip } from "./components/ThemedTooltip";
import { TooltipRoot } from "./components/ui/Tooltip";
import { getMeta, optimize, bossArt, type Build, type Meta, type Mode } from "./lib/api";
import { toRequest, type FormState } from "./lib/form";

export default function App() {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [view, setView] = useState<"rite" | "verdict">("rite");
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState<Build[]>([]);
  const [mode, setMode] = useState<Mode>("auto");
  const [snapDon, setSnapDon] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMeta()
      .then((m) => {
        setMeta(m);
        const c = m.characters[0];
        setForm({
          character: c.name,
          boss: "",
          level: c.levels.includes(15) ? 15 : c.levels[c.levels.length - 1],
          don: 0,
          weaponType: "",
          weight: 50,
          play: [{ action: "melee", weight: 100 }],
          toggles: [],
          top: 3,
          beam: 12,
          countDebuffs: true,
          refusedCurses: [],
        });
      })
      .catch(() => setError("Failed to load data (is nr ui running?)"));
  }, []);

  const patch = (p: Partial<FormState>) => setForm((f) => (f ? { ...f, ...p } : f));

  const runOptimize = async () => {
    if (!form) return;
    setBusy(true);
    setError(null);
    try {
      const res = await optimize(toRequest(form));
      setResults(res.results);
      setMode(res.mode);
      setSnapDon(form.don);
      setView("verdict");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Summon failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <TooltipRoot>
      {!meta || !form ? (
        <Splash error={error} />
      ) : (
        <AnimatePresence mode="wait">
          {view === "rite" ? (
            <motion.div key="rite" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, filter: "blur(4px)" }} transition={{ duration: 0.4 }}>
              <Rite meta={meta} form={form} patch={patch} onOptimize={runOptimize} busy={busy} />
            </motion.div>
          ) : (
            <motion.div key="verdict" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.4 }}>
              <VerdictBackdrop boss={form.boss} character={form.character} />
              <Verdict results={results} mode={mode} character={form.character} don={snapDon} onBack={() => setView("rite")} />
            </motion.div>
          )}
        </AnimatePresence>
      )}

      <AnimatePresence>{busy && <Invoking />}</AnimatePresence>

      <ThemedTooltip />

      {error && meta && (
        <div className="fixed bottom-5 left-1/2 z-50 -translate-x-1/2 border border-[#6e3733] bg-[#3a1a1a]/95 px-5 py-3 text-[13.5px] text-[#f3c0bb] shadow-xl backdrop-blur">
          {error}
          <button className="ml-4 text-[#f3c0bb]/70 hover:text-[#f3c0bb]" onClick={() => setError(null)}>
            ✕
          </button>
        </div>
      )}
    </TooltipRoot>
  );
}

function VerdictBackdrop({ boss, character }: { boss: string; character: string }) {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden" style={{ background: "linear-gradient(180deg,#070a12,#05070c)" }}>
      {/* faint lore illustration (boss-themed) — kept a ghost so it lends
          atmosphere without ever fighting the build text for legibility */}
      <img
        src={bossArt(boss, character.length)}
        alt=""
        onError={(e) => (e.currentTarget.style.display = "none")}
        className="absolute right-[-4%] top-1/2 h-[112%] max-w-[62%] -translate-y-1/2 object-cover opacity-[0.26] mix-blend-screen"
        style={{ maskImage: "radial-gradient(75% 75% at 62% 50%, #000 42%, transparent 88%)", WebkitMaskImage: "radial-gradient(75% 75% at 62% 50%, #000 42%, transparent 88%)" }}
      />
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(120% 80% at 50% -10%, rgba(56,78,128,0.16), transparent 55%)," +
            "linear-gradient(90deg, #070a12 16%, transparent 48%, rgba(7,10,18,0.35) 92%)",
        }}
      />
    </div>
  );
}

function Splash({ error }: { error: string | null }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-void">
      {error ? (
        <div className="max-w-md border border-[#6e3733] bg-[#3a1a1a]/80 px-6 py-4 text-center text-[#f3c0bb]">{error}</div>
      ) : (
        <>
          <div className="h-12 w-12 animate-spin rounded-full border-2 border-line border-t-gold border-r-gold-deep" />
          <div className="font-display text-[12px] uppercase tracking-widest2 text-silver/80">Awakening the rite…</div>
        </>
      )}
    </div>
  );
}

// The original loading — a small centered ring with a rotating inner diamond
// and the "Summoning the build…" line (restored on request).
function Invoking() {
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-40 flex flex-col items-center justify-center bg-void/70 backdrop-blur-sm">
      <div className="relative h-16 w-16">
        <div className="absolute inset-0 animate-spin rounded-full border-2 border-line border-t-gold border-r-gold-deep shadow-[0_0_24px_-4px_rgba(201,162,74,0.6)]" />
        <div className="absolute inset-2 rotate-45 animate-breathe border border-frost/40" />
      </div>
      <div className="mt-5 animate-breathe font-display text-[13px] uppercase tracking-widest2 text-gold">Summoning the build…</div>
    </motion.div>
  );
}
