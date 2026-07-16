import { useState } from "react";
import { Plus, X, Sparkles, Crosshair, Scale, Gamepad2, ChevronDown, Check } from "lucide-react";
import { cn } from "@/lib/cn";
import type { Meta } from "@/lib/api";
import type { FormState, PlayRow } from "@/lib/form";
import { FR_ACTIONS, SHORT_TOGGLES } from "@/lib/labels";
import { Select } from "./ui/Select";
import { Gauge } from "./ui/Slider";

function Section({ icon: Icon, title, children }: { icon: typeof Crosshair; title: string; children: React.ReactNode }) {
  return (
    <section>
      <div className="mb-2.5 flex items-center gap-2">
        <Icon className="h-4 w-4 text-gold" />
        <span className="font-display text-[12px] uppercase tracking-widest2 text-gold">{title}</span>
        <span className="h-px flex-1 bg-gradient-to-r from-gold-deep/50 to-transparent" />
      </div>
      <div className="rounded-sm border border-line/50 bg-night-800/45 p-4">{children}</div>
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 font-sans text-[11px] uppercase tracking-[0.13em] text-silver/85">{label}</div>
      {children}
    </div>
  );
}

export function ContextPanel({
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
  const [adv, setAdv] = useState(false);
  const hero = meta.characters.find((h) => h.name === form.character) ?? meta.characters[0];
  const levels = hero?.levels ?? [15];

  const GENERALIST = "__all__";
  const AUTO = "__auto__";
  const bossOptions = [{ value: GENERALIST, label: "Généraliste — les 8 Nightlords" }, ...meta.bosses.map((b) => ({ value: b, label: b }))];
  const donOptions = [{ value: "0", label: "Non — normale" }, ...meta.don_levels.map((d) => ({ value: String(d), label: `Niveau ${d}` }))];
  const weaponOptions = [
    { value: AUTO, label: "Auto — meilleurs types" },
    { value: "__generic__", label: "Générique — toute arme" },
    ...meta.weapon_types.map((t) => ({ value: t, label: t })),
  ];
  const actionOptions = meta.actions.map((a) => ({ value: a, label: FR_ACTIONS[a] ?? a }));

  const setPlay = (i: number, p: Partial<PlayRow>) => patch({ play: form.play.map((r, j) => (j === i ? { ...r, ...p } : r)) });
  const addPlay = () => patch({ play: [...form.play, { action: "skill", weight: 20 }] });
  const rmPlay = (i: number) => patch({ play: form.play.filter((_, j) => j !== i) });
  const toggle = (k: string) =>
    patch({ toggles: form.toggles.includes(k) ? form.toggles.filter((t) => t !== k) : [...form.toggles, k] });

  const weightHint = form.weight >= 65 ? "priorité à la survie" : form.weight <= 35 ? "priorité aux dégâts" : "équilibré";

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 text-center">
        <div className="font-display text-[11px] uppercase tracking-widest2 text-silver/75">Le Rite</div>
        <div className="mt-0.5 font-display text-[19px] tracking-wide text-ink">Contexte de la traque</div>
      </div>

      {/* scrolls internally only when the viewport is too short — the page never scrolls */}
      <div className="-mr-3 min-h-0 flex-1 space-y-5 overflow-y-auto pr-3">
        <Section icon={Crosshair} title="Cible">
          <Field label="Nightlord">
            <Select value={form.boss || GENERALIST} onValueChange={(v) => patch({ boss: v === GENERALIST ? "" : v })} options={bossOptions} />
          </Field>
          <div className="mt-3.5 grid grid-cols-2 gap-3">
            <Field label="Deep of Night">
              <Select value={String(form.don)} onValueChange={(v) => patch({ don: Number(v) })} options={donOptions} />
            </Field>
            <Field label="Niveau">
              <Select value={String(form.level)} onValueChange={(v) => patch({ level: Number(v) })} options={levels.map((l) => ({ value: String(l), label: `Niveau ${l}` }))} />
            </Field>
          </div>
          <div className="mt-3.5">
            <Field label="Type d'arme">
              <Select value={form.weaponType || AUTO} onValueChange={(v) => patch({ weaponType: v === AUTO ? "" : v })} options={weaponOptions} />
            </Field>
          </div>
        </Section>

        <Section icon={Scale} title="Objectif">
          <div className="flex items-baseline justify-between text-[12.5px]">
            <span className="uppercase tracking-wider text-gold">Offense</span>
            <span className="font-sans text-[15px] font-semibold tabular-nums text-gold-bright">{form.weight}%</span>
            <span className="uppercase tracking-wider text-relic-green">Survie</span>
          </div>
          <Gauge value={form.weight} onValueChange={(v) => patch({ weight: v })} className="mt-2.5" />
          <div className="mt-2.5 text-center text-[12.5px] italic text-silver/75">Curseur : {weightHint}.</div>
        </Section>

        <Section icon={Gamepad2} title="Style de jeu">
          <Field label="Profil de jeu">
            <p className="mb-2.5 text-[12px] italic leading-snug text-silver/70">Les buffs « par action » ne comptent que pour les actions déclarées.</p>
            <div className="space-y-2">
              {form.play.map((row, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="flex-1">
                    <Select value={row.action} onValueChange={(v) => setPlay(i, { action: v })} options={actionOptions} />
                  </div>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={row.weight}
                    onChange={(e) => setPlay(i, { weight: Number(e.target.value) })}
                    className="w-14 border border-line/70 bg-night-700/70 px-2 py-2 text-center text-[14px] text-ink outline-none focus:border-frost/70"
                  />
                  <span className="text-[13px] text-silver/80">%</span>
                  {form.play.length > 1 && (
                    <button onClick={() => rmPlay(i)} className="flex-none p-1 text-faint transition hover:text-relic-red" title="retirer">
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <button onClick={addPlay} className="mt-2.5 flex w-full items-center justify-center gap-1.5 border border-dashed border-line/70 py-2 text-[12.5px] tracking-wide text-silver/80 transition hover:border-gold-deep hover:text-gold">
              <Plus className="h-4 w-4" /> ajouter une action
            </button>
          </Field>

          <div className="mt-4">
            <div className="mb-2 font-sans text-[11px] uppercase tracking-[0.13em] text-silver/85">Engagements</div>
            <div className="grid grid-cols-2 gap-2.5">
              {Object.entries(meta.toggles).map(([k, label]) => {
                const on = form.toggles.includes(k);
                return (
                  <button
                    key={k}
                    onClick={() => toggle(k)}
                    title={label}
                    className={cn(
                      "flex items-center gap-2.5 border px-3 py-2.5 text-left text-[12.5px] leading-tight transition",
                      on ? "border-frost/55 bg-frost/10 text-ink" : "border-line/55 bg-night-700/40 text-silver hover:border-line-bright hover:text-ink"
                    )}
                  >
                    <span className={cn("flex h-4 w-4 flex-none rotate-45 items-center justify-center border", on ? "border-frost bg-frost/30 shadow-[0_0_7px_rgba(143,182,230,0.7)]" : "border-line")}>
                      {on && <Check className="h-2.5 w-2.5 -rotate-45 text-frost" strokeWidth={3} />}
                    </span>
                    {SHORT_TOGGLES[k] ?? label}
                  </button>
                );
              })}
            </div>
          </div>
        </Section>

        {/* advanced (search knobs) — collapsed by default to keep it clean */}
        <div>
          <button onClick={() => setAdv((a) => !a)} className="flex items-center gap-1.5 font-sans text-[11px] uppercase tracking-[0.15em] text-silver/70 transition hover:text-silver">
            <ChevronDown className={cn("h-4 w-4 transition", adv && "rotate-180")} /> Avancé
          </button>
          {adv && (
            <div className="mt-2.5 grid grid-cols-2 gap-3">
              <Field label="Builds affichés">
                <input type="number" min={1} max={10} value={form.top} onChange={(e) => patch({ top: Number(e.target.value) })} className="w-full border border-line/70 bg-night-700/70 px-3 py-2 text-[14px] text-ink outline-none focus:border-frost/70" />
              </Field>
              <Field label="Largeur beam">
                <input type="number" min={4} max={40} value={form.beam} onChange={(e) => patch({ beam: Number(e.target.value) })} className="w-full border border-line/70 bg-night-700/70 px-3 py-2 text-[14px] text-ink outline-none focus:border-frost/70" />
              </Field>
            </div>
          )}
        </div>
      </div>

      <button
        onClick={onOptimize}
        disabled={busy}
        className={cn(
          "group relative mt-4 flex items-center justify-center gap-2 overflow-hidden border border-gold-deep/80 bg-gradient-to-b from-night-600/80 to-night-800/90 py-4 font-display text-[14px] uppercase tracking-widest2 text-gold-bright transition",
          "hover:border-gold hover:shadow-[0_0_28px_-6px_rgba(201,162,74,0.6)]",
          "disabled:cursor-wait disabled:opacity-60"
        )}
      >
        <Sparkles className="h-4 w-4" />
        {busy ? "Invocation…" : "Invoquer le build"}
        <span className="pointer-events-none absolute inset-y-0 -left-1/3 w-1/3 -skew-x-12 bg-white/10 transition-all duration-500 group-hover:left-[130%]" />
      </button>
    </div>
  );
}
