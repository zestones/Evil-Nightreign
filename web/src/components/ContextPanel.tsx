import { useState } from "react";
import { Plus, X, Sparkles, Crosshair, Scale, Gamepad2, ChevronLeft, ChevronRight, Skull, Check, Wand2 } from "lucide-react";
import { cn } from "@/lib/cn";
import type { Archetype, Meta } from "@/lib/api";
import type { FormState, PlayRow } from "@/lib/form";
import { FR_ACTIONS, SHORT_TOGGLES } from "@/lib/labels";
import { Select } from "./ui/Select";
import { Combobox } from "./ui/Combobox";
import { Gauge } from "./ui/Slider";
import { CursesSection } from "./CursesSection";

const PARADIGM_FR: Record<string, string> = {
  strike: "scored strike",
  replay: "replays damage",
  utility: "utility",
};

// One-line "what to do here" caption per step — the tabs alone didn't read as
// a click-through flow (user feedback).
const STEP_HINT: Record<string, string> = {
  style: "How you fight — pick a preset or set your own mix.",
  cible: "What you hunt — Nightlord, Deep of Night, weapon.",
  malus: "Which Deep of Night curses you'll tolerate.",
};

// An archetype is "active" when the form's play+toggles match it exactly.
function archetypeActive(a: Archetype, form: FormState): boolean {
  const play: Record<string, number> = {};
  for (const r of form.play) if (r.weight > 0) play[r.action] = (play[r.action] ?? 0) + r.weight;
  const total = Object.values(play).reduce((s, v) => s + v, 0) || 1;
  const norm = Object.fromEntries(Object.entries(play).map(([k, v]) => [k, v / total]));
  const keysA = Object.keys(a.play).sort();
  const keysF = Object.keys(norm).sort();
  if (keysA.join() !== keysF.join()) return false;
  if (!keysA.every((k) => Math.abs(a.play[k] - norm[k]) < 0.001)) return false;
  if (form.weaponType !== (a.weapon ?? "")) return false; // preset also sets the weapon type
  const ta = [...(a.toggles ?? [])].sort().join();
  return ta === [...form.toggles].sort().join();
}

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
  const [step, setStep] = useState(0);
  const hero = meta.characters.find((h) => h.name === form.character) ?? meta.characters[0];
  const levels = hero?.levels ?? [15];

  const GENERALIST = "__all__";
  const AUTO = "__auto__";
  const bossOptions = [{ value: GENERALIST, label: "Generalist — the 8 Nightlords" }, ...meta.bosses.map((b) => ({ value: b, label: b }))];
  const donOptions = [{ value: "0", label: "No — normal" }, ...meta.don_levels.map((d) => ({ value: String(d), label: `Level ${d}` }))];
  const weaponOptions = [
    { value: AUTO, label: "Auto — best types" },
    { value: "__generic__", label: "Generic — any weapon" },
    ...meta.weapon_types.map((t) => ({ value: t, label: t })),
  ];
  const actionOptions = meta.actions.map((a) => ({ value: a, label: FR_ACTIONS[a] ?? a }));

  const setPlay = (i: number, p: Partial<PlayRow>) => patch({ play: form.play.map((r, j) => (j === i ? { ...r, ...p } : r)) });
  const addPlay = () => patch({ play: [...form.play, { action: "skill", weight: 20 }] });
  const rmPlay = (i: number) => patch({ play: form.play.filter((_, j) => j !== i) });
  const toggle = (k: string) =>
    patch({ toggles: form.toggles.includes(k) ? form.toggles.filter((t) => t !== k) : [...form.toggles, k] });

  const weightHint = form.weight >= 65 ? "survival priority" : form.weight <= 35 ? "damage priority" : "balanced";

  const kit = meta.kits?.[form.character];
  const applyArchetype = (a: Archetype) =>
    patch({
      play: Object.entries(a.play).map(([action, weight]) => ({ action, weight: Math.round(weight * 100) })),
      toggles: a.toggles ?? [],
      weaponType: a.weapon ?? "", // pin the weapon type the preset implies (auto if none)
    });

  // stepper — profile-first (ROADMAP §3): HOW you play, then WHAT you hunt,
  // then what you tolerate. Curses only exists under Deep of Night.
  const hasMalus = form.don >= 1 && meta.curses.length > 0;
  const steps = [
    { key: "style", label: "Playstyle", icon: Gamepad2 },
    { key: "cible", label: "Target", icon: Crosshair },
    ...(hasMalus ? [{ key: "malus", label: "Curses", icon: Skull }] : []),
  ];
  const cur = Math.min(step, steps.length - 1);
  const curKey = steps[cur].key;

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 text-center">
        <div className="font-display text-[11px] uppercase tracking-widest2 text-silver/75">The Rite</div>
        <div className="mt-0.5 font-display text-[19px] tracking-wide text-ink">Hunt Context</div>
      </div>

      {/* stepper — a click-through flow; every tab is also directly clickable */}
      <div className="mb-2 flex items-stretch gap-1.5">
        {steps.map((s, i) => {
          const active = i === cur;
          const done = i < cur;
          const Icon = s.icon;
          return (
            <button
              key={s.key}
              onClick={() => setStep(i)}
              className={cn(
                "group relative flex flex-1 items-center justify-center gap-1.5 border px-2 py-2.5 text-[11.5px] leading-tight transition",
                active
                  ? "border-gold/70 bg-gold/12 text-gold-bright shadow-[0_0_18px_-8px_rgba(201,162,74,0.9)]"
                  : "border-line/45 bg-night-800/40 text-silver/70 hover:border-line-bright hover:bg-night-700/50 hover:text-ink"
              )}
            >
              <span className={cn("flex h-[18px] w-[18px] flex-none items-center justify-center rounded-full text-[9.5px] font-semibold", active ? "bg-gold/25 text-gold-bright" : done ? "bg-relic-green/25 text-relic-green" : "bg-night-700 text-silver/55")}>
                {done ? <Check className="h-2.5 w-2.5" strokeWidth={3} /> : i + 1}
              </span>
              <Icon className="h-3.5 w-3.5 flex-none" />
              <span className="truncate">{s.label}</span>
              {active && <span className="pointer-events-none absolute inset-x-3 -bottom-px h-0.5 bg-gold-bright/80" />}
            </button>
          );
        })}
      </div>
      <p className="mb-4 flex items-center justify-center gap-1.5 px-1 text-center text-[11.5px] leading-snug text-silver/60">
        <span className="flex-none font-medium text-gold/75">Step {cur + 1}/{steps.length}</span>
        <span className="flex-none text-line">·</span>
        <span>{STEP_HINT[curKey]}</span>
      </p>

      {/* current step content */}
      <div className="-mr-3 min-h-0 flex-1 space-y-5 overflow-y-auto pr-3">
        {curKey === "cible" && (
          <Section icon={Crosshair} title="Target">
            <Field label="Nightlord">
              <Select value={form.boss || GENERALIST} onValueChange={(v) => patch({ boss: v === GENERALIST ? "" : v })} options={bossOptions} />
            </Field>
            <div className="mt-3.5 grid grid-cols-2 gap-3">
              <Field label="Deep of Night">
                <Select value={String(form.don)} onValueChange={(v) => patch({ don: Number(v) })} options={donOptions} />
              </Field>
              <Field label="Level">
                <Select value={String(form.level)} onValueChange={(v) => patch({ level: Number(v) })} options={levels.map((l) => ({ value: String(l), label: `Level ${l}` }))} />
              </Field>
            </div>
            <div className="mt-3.5">
              <Field label="Weapon type">
                <Combobox value={form.weaponType || AUTO} onValueChange={(v) => patch({ weaponType: v === AUTO ? "" : v })} options={weaponOptions} />
              </Field>
            </div>
          </Section>
        )}

        {curKey === "style" && (
          <>
            {kit && kit.archetypes.length > 0 && (
              <Section icon={Wand2} title="Quick presets">
                <p className="mb-2.5 text-[12px] leading-snug text-silver/70">
                  Tap a preset to set the <span className="text-silver">Weapon</span>,{" "}
                  <span className="text-silver">Damage sources</span> &amp; <span className="text-silver">Commitments</span>{" "}
                  in one go — then tweak anything. Or skip and build your own.
                </p>
                <div className="grid grid-cols-1 gap-2">
                  {kit.archetypes.map((a) => {
                    const active = archetypeActive(a, form);
                    return (
                      <button
                        key={a.name}
                        onClick={() => applyArchetype(a)}
                        className={cn(
                          "flex items-center gap-2.5 border px-3 py-2.5 text-left transition",
                          active
                            ? "border-gold/60 bg-gold/10 text-gold-bright"
                            : "border-line/55 bg-night-700/40 text-silver hover:border-line-bright hover:text-ink"
                        )}
                      >
                        <span className={cn("flex h-4 w-4 flex-none rotate-45 items-center justify-center border transition", active ? "border-gold bg-gold/25" : "border-line/70 group-hover:border-line-bright")}>
                          {active && <Check className="h-2.5 w-2.5 -rotate-45 text-gold-bright" strokeWidth={3} />}
                        </span>
                        <span className="flex-none text-[13px]">{a.name}</span>
                        <span className="ml-auto min-w-0 truncate text-right font-sans text-[10.5px] uppercase tracking-wide text-dim">
                          {Object.entries(a.play)
                            .map(([k, v]) => `${FR_ACTIONS[k] ?? k} ${Math.round(v * 100)}%`)
                            .join(" · ")}
                        </span>
                      </button>
                    );
                  })}
                </div>
                {kit.passive && (
                  <p className="mt-2.5 text-[11.5px] leading-snug text-dim">
                    Passive: <span className="text-silver/80">{kit.passive}</span> · skill{" "}
                    <span className="text-silver/80">{PARADIGM_FR[kit.skill_paradigm]}</span> · ultimate{" "}
                    <span className="text-silver/80">{PARADIGM_FR[kit.ultimate_paradigm]}</span>
                  </p>
                )}
              </Section>
            )}

            <Section icon={Scale} title="Objective">
              <div className="flex items-baseline justify-between text-[12.5px]">
                <span className="uppercase tracking-wider text-gold">
                  Offense <b className="ml-0.5 font-sans text-[14px] tabular-nums text-gold-bright">{100 - form.weight}%</b>
                </span>
                <span className="uppercase tracking-wider text-relic-green">
                  <b className="mr-0.5 font-sans text-[14px] tabular-nums text-relic-green">{form.weight}%</b> Survival
                </span>
              </div>
              <Gauge value={form.weight} onValueChange={(v) => patch({ weight: v })} className="mt-2.5" />
              <div className="mt-2.5 text-center text-[12.5px] text-silver/75">Priority: {weightHint}.</div>
            </Section>

            <Section icon={Gamepad2} title="Damage sources">
              <Field label="Play profile">
                <p className="mb-2.5 text-[12px] leading-snug text-silver/70">
                  Your real mix: melee, spells (the catalyst will be chosen for its spells), skill, ultimate…
                  The "per-action" buffs only count for the declared actions.
                </p>
                <div className="space-y-2">
                  {form.play.map((row, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <div className="flex-1">
                        <Combobox value={row.action} onValueChange={(v) => setPlay(i, { action: v })} options={actionOptions} />
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
                        <button onClick={() => rmPlay(i)} className="flex-none p-1 text-faint transition hover:text-relic-red" title="remove">
                          <X className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                <button onClick={addPlay} className="mt-2.5 flex w-full items-center justify-center gap-1.5 border border-dashed border-line/70 py-2 text-[12.5px] tracking-wide text-silver/80 transition hover:border-gold-deep hover:text-gold">
                  <Plus className="h-4 w-4" /> add an action
                </button>
              </Field>

              <div className="mt-4">
                <div className="mb-2 font-sans text-[11px] uppercase tracking-[0.13em] text-silver/85">Commitments</div>
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
          </>
        )}

        {curKey === "malus" && <CursesSection meta={meta} form={form} patch={patch} />}
      </div>

      {/* footer: free step nav + advanced + an always-available invoke */}
      <div className="mt-4 space-y-3">
        <div className="flex items-center justify-between gap-2 text-[12px]">
          <button
            onClick={() => setStep(cur - 1)}
            disabled={cur === 0}
            className="flex items-center gap-1 text-silver/70 transition hover:text-ink disabled:pointer-events-none disabled:opacity-25"
          >
            <ChevronLeft className="h-4 w-4" /> Previous
          </button>
          <button
            onClick={() => setAdv((a) => !a)}
            className={cn("text-[11px] uppercase tracking-wider transition", adv ? "text-silver" : "text-silver/50 hover:text-silver")}
          >
            Advanced
          </button>
          <button
            onClick={() => setStep(cur + 1)}
            disabled={cur >= steps.length - 1}
            className="flex items-center gap-1 text-silver/70 transition hover:text-ink disabled:pointer-events-none disabled:opacity-25"
          >
            Next <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        {adv && (
          <div className="grid grid-cols-2 gap-3">
            <Field label="Builds shown">
              <input type="number" min={1} max={10} value={form.top} onChange={(e) => patch({ top: Number(e.target.value) })} className="w-full border border-line/70 bg-night-700/70 px-3 py-2 text-[14px] text-ink outline-none focus:border-frost/70" />
            </Field>
            <Field label="Beam width">
              <input type="number" min={4} max={40} value={form.beam} onChange={(e) => patch({ beam: Number(e.target.value) })} className="w-full border border-line/70 bg-night-700/70 px-3 py-2 text-[14px] text-ink outline-none focus:border-frost/70" />
            </Field>
          </div>
        )}

        <button
          onClick={onOptimize}
          disabled={busy}
          className={cn(
            "group relative flex w-full items-center justify-center gap-2 overflow-hidden border border-gold-deep/80 bg-gradient-to-b from-night-600/80 to-night-800/90 py-4 font-display text-[14px] uppercase tracking-widest2 text-gold-bright transition",
            "hover:border-gold hover:shadow-[0_0_28px_-6px_rgba(201,162,74,0.6)]",
            "disabled:cursor-wait disabled:opacity-60"
          )}
        >
          <Sparkles className="h-4 w-4" />
          {busy ? "Summoning…" : "Summon Build"}
          <span className="pointer-events-none absolute inset-y-0 -left-1/3 w-1/3 -skew-x-12 bg-white/10 transition-all duration-500 group-hover:left-[130%]" />
        </button>
      </div>
    </div>
  );
}
