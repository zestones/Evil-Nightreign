import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { Upload, Sparkles, ArrowRight, Copy, Check, X } from "lucide-react";

const SAVE_DIR = "%APPDATA%\\Nightreign\\";

// First-run gate: pick a collection before entering. Two clear paths — import
// your own save, or explore the built-in demo. The save-folder path is the
// single most important thing (people won't find their save otherwise), so it's
// a prominent one-click-copy field. Closable only after a first choice was made
// (reopened via the "change" chip); on first visit a choice is required.
export function LandingOverlay({
  relicCount,
  importing,
  closable,
  onClose,
  onDemo,
  onImportSave,
}: {
  relicCount: number;
  importing: boolean;
  closable: boolean;
  onClose: () => void;
  onDemo: () => void;
  onImportSave: (file: File) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [copied, setCopied] = useState(false);

  const copyPath = async () => {
    try {
      await navigator.clipboard.writeText(SAVE_DIR);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked — no-op */
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.35 }}
      className="fixed inset-0 z-40 flex flex-col items-center justify-center overflow-y-auto bg-void/82 px-6 py-10 backdrop-blur-md"
      onClick={closable ? onClose : undefined}
    >
      {closable && (
        <button
          onClick={onClose}
          aria-label="Close"
          className="absolute right-5 top-5 flex h-9 w-9 items-center justify-center rounded-sm border border-line/60 bg-night-800/70 text-silver transition hover:border-frost/50 hover:text-ink"
        >
          <X className="h-4.5 w-4.5" />
        </button>
      )}

      <div onClick={(e) => e.stopPropagation()} className="flex w-full max-w-[720px] flex-col items-center">
        <div className="text-center">
          <h1 className="font-display text-[clamp(30px,4.4vw,52px)] font-semibold leading-none tracking-[0.16em] text-glow-gold">
            <span className="bg-gradient-to-b from-[#f0e6c8] via-gold to-gold-deep bg-clip-text text-transparent">EVIL</span>
            <span className="bg-gradient-to-b from-[#dfe6f2] via-silver to-[#5b6c86] bg-clip-text text-transparent">NIGHTREIGN</span>
          </h1>
          <p className="mt-3 font-sans text-[12px] uppercase tracking-[0.24em] text-silver/55">Relic build optimizer</p>
        </div>

        <div className="mt-9 grid w-full grid-cols-1 gap-4 sm:grid-cols-2">
          {/* Import — the primary path */}
          <div className="flex flex-col border border-gold-deep/50 bg-night-800/50 p-6 transition hover:border-gold/70">
            <Upload className="h-6 w-6 text-gold" />
            <div className="mt-3 font-display text-[17px] tracking-wide text-ink">Import your save</div>
            <p className="mt-2 text-[13px] leading-relaxed text-silver/70">
              Optimize <b className="text-silver">your own</b> relics. Find your save here:
            </p>

            {/* the star of the card: the save folder path, one-click copyable */}
            <div className="mt-3">
              <button
                onClick={copyPath}
                title="Copy the folder path"
                className="flex w-full items-center justify-between gap-2 rounded-sm border border-gold-deep/60 bg-night-900/70 px-3 py-2.5 font-mono text-[14px] text-gold-bright transition hover:border-gold hover:shadow-[0_0_18px_-8px_rgba(201,162,74,0.8)]"
              >
                <span className="truncate">{SAVE_DIR}</span>
                <span className="flex flex-none items-center gap-1 text-[11px] uppercase tracking-wide text-gold/85">
                  {copied ? <><Check className="h-3.5 w-3.5 text-relic-green" /> Copied</> : <><Copy className="h-3.5 w-3.5" /> Copy</>}
                </span>
              </button>
              <p className="mt-2 text-[11.5px] leading-relaxed text-silver/60">
                Paste it in Explorer, open your <b className="text-silver/80">&lt;id&gt;</b> folder, grab{" "}
                <b className="text-silver/80">NR0000.sl2</b>.
              </p>
            </div>

            <input
              ref={inputRef}
              type="file"
              accept=".sl2"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onImportSave(f);
                e.currentTarget.value = "";
              }}
            />
            <button
              onClick={() => inputRef.current?.click()}
              disabled={importing}
              className="mt-4 flex items-center justify-center gap-2 border border-gold-deep/80 bg-gradient-to-b from-night-600/80 to-night-800/90 py-3 font-display text-[13px] uppercase tracking-widest2 text-gold-bright transition hover:border-gold hover:shadow-[0_0_24px_-6px_rgba(201,162,74,0.6)] disabled:cursor-wait disabled:opacity-60"
            >
              {importing ? (
                <>
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border border-line border-t-gold" /> Reading save…
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" /> Choose save file
                </>
              )}
            </button>
          </div>

          {/* Demo — the secondary path */}
          <div className="flex flex-col border border-line/50 bg-night-800/40 p-6 transition hover:border-line-bright">
            <Sparkles className="h-6 w-6 text-frost/80" />
            <div className="mt-3 font-display text-[17px] tracking-wide text-ink">Try the demo</div>
            <p className="mt-2 flex-1 text-[13px] leading-relaxed text-silver/70">
              Explore with a sample collection of{" "}
              <b className="tabular-nums text-silver">{relicCount.toLocaleString()}</b> relics. No save needed.
            </p>
            <button
              onClick={onDemo}
              className="mt-5 flex items-center justify-center gap-2 border border-line/70 bg-night-700/50 py-3 font-display text-[13px] uppercase tracking-widest2 text-silver transition hover:border-frost/50 hover:text-ink"
            >
              Enter the demo <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="mt-8 flex max-w-[620px] flex-col items-center gap-2 rounded-sm border border-line/45 bg-night-900/55 px-6 py-3.5 text-center backdrop-blur-sm">
          <p className="text-[12px] leading-relaxed text-silver/75">
            Your save is read only to extract your relics — <b className="text-silver">never written to disk or shared</b>.
          </p>
          <p className="text-[12.5px] leading-relaxed text-silver/70">
            Fan-made · <b className="text-gold-bright">not affiliated with FromSoftware or Bandai Namco</b> · <span className="italic text-silver/85">Elden Ring</span> / <span className="italic text-silver/85">Nightreign</span> and all game data &amp; assets © their owners ·{" "}
            <a
              href="https://github.com/zestones/Evil-Nightreign"
              target="_blank"
              rel="noreferrer"
              className="font-medium text-gold underline decoration-dotted underline-offset-2 transition hover:text-gold-bright"
            >
              GitHub ↗
            </a>
          </p>
        </div>
      </div>
    </motion.div>
  );
}
