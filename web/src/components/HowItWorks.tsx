import { useEffect } from "react";
import { X, Swords } from "lucide-react";
import { cn } from "@/lib/cn";
import { FR_ACTIONS, FR_TYPES, FR_STATS, FR_STATUS, STATUS_COLOR } from "@/lib/labels";
import { heroArt, type Build, type Mode } from "@/lib/api";

// The game's per-affinity damage icons; graceful text fallback.
const ElemImg = ({ type }: { type: string }) => (
  <img src={`/assets/element-icons/${type}.webp`} alt="" onError={(e) => (e.currentTarget.style.display = "none")} className="h-[16px] w-[16px] flex-none object-contain" />
);
const hide = (e: React.SyntheticEvent<HTMLImageElement>) => (e.currentTarget.style.display = "none");

function Section({ n, title, hint, children }: { n: number; title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-line/40 pt-6 first:border-t-0 first:pt-0">
      <div className="mb-3 flex items-baseline gap-3">
        <span className="font-display text-[13px] tabular-nums text-gold-deep/80">{String(n).padStart(2, "0")}</span>
        <h3 className="font-display text-[15px] uppercase tracking-widest2 text-gold-bright">{title}</h3>
      </div>
      {hint && <p className="mb-3 max-w-[70ch] text-[13px] leading-relaxed text-silver/75">{hint}</p>}
      {children}
    </section>
  );
}

function Chip({ children, ghost, color }: { children: React.ReactNode; ghost?: boolean; color?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 border px-2.5 py-1 font-sans text-[12.5px] tabular-nums",
        ghost ? "border-dashed border-line/60 text-dim" : "border-line/70 bg-night-700/40 text-silver"
      )}
      style={color ? { borderColor: color } : undefined}
    >
      {children}
    </span>
  );
}

// A visual stat tile — big number, small caption. The score/economy read as a
// dashboard, not a text ledger.
function Tile({ label, value, sub, tone = "ink" }: { label: string; value: string; sub?: string; tone?: "gold" | "green" | "frost" | "ink" }) {
  const color = tone === "gold" ? "text-gold-bright" : tone === "green" ? "text-relic-green" : tone === "frost" ? "text-frost" : "text-ink";
  return (
    <div className="rounded-sm border border-line/50 bg-night-900/50 px-3.5 py-3">
      <div className="font-sans text-[10px] uppercase tracking-[0.14em] text-silver/60">{label}</div>
      <div className={cn("mt-1 font-sans text-[24px] font-semibold leading-none tabular-nums", color)}>{value}</div>
      {sub && <div className="mt-1 text-[11px] leading-tight text-dim">{sub}</div>}
    </div>
  );
}

export function HowItWorks({ b, mode, character, onClose }: { b: Build; mode: Mode; character: string; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Rebuild the effective source mix exactly as the card does (engine-supplied).
  const play = b.play ?? {};
  const shareTotal = Object.entries(b.actions_hit).reduce((s, [a, v]) => s + (play[a] ?? 0) * v, 0);
  const sourceRows = Object.entries(b.actions_hit)
    .map(([a, v]) => ({
      action: a,
      hit: v,
      share: shareTotal > 0 ? ((play[a] ?? 0) * v) / shareTotal : 0,
      weight: play[a] ?? 0,
      info: b.sources?.[a] ?? null,
    }))
    .filter((r) => r.weight > 0)
    .sort((x, y) => y.share - x.share);

  // only actual spells (label "Sorcery:/Incantation: …") make it a caster — a
  // melee weapon's skill/ultimate carries a source but is NOT a spell.
  const spellSrc = Object.values(b.sources ?? {}).find((s) => /^(Sorcery|Incantation):/.test(s.label));
  const isCaster = !!spellSrc;
  const guaranteed = spellSrc?.guaranteed !== false;
  const theoretical = sourceRows.some((r) => r.info && !r.info.spell_factor_calibrated);
  const isMelee = sourceRows.some((r) => !r.info); // an action with no resolved source = weapon strike

  const mults = Object.entries(b.attack_multipliers).filter(([, m]) => m > 1.001);
  const stats = Object.entries(b.stat_bonuses);
  const status = Object.entries(b.status);
  const fpClamps = Object.entries(b.fp ?? {});
  const star = b.generic ? "*" : "";

  const typeBuff = b.top_effects.find(
    (e) => e.action === "*" && e.key.toLowerCase().includes(b.weapon_type.toLowerCase()));

  // "Not modeled yet" as structured cards (never a bullet list) — only the ones
  // that actually apply to this build.
  const limits: { title: string; body: string }[] = [
    ...(isCaster ? [{ title: "Spell cadence", body: "Fast spells (Carian Slicer, Pebble) are undervalued — cast time isn't scored yet." }] : []),
    ...(isMelee ? [{ title: "Defense vs linear", body: "Melee absolutes await one clean measurement on a known-defense target." }] : []),
    { title: "Stamina regen", body: "Shown as info; the sustain constraint waits on a measured regen rate." },
    { title: "Stagger & party", body: "Posture damage and party scaling are extracted but not yet scored." },
    ...(isCaster && !guaranteed ? [{ title: "Slot-2 pool", body: "The random second-spell pool isn't fully decoded — we rank on the guaranteed slot-1 spell only." }] : []),
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-center bg-black/50 p-0 backdrop-blur-md sm:items-center sm:p-6" onClick={onClose}>
      <div
        className="relative flex h-full w-full max-w-[1400px] flex-col overflow-hidden border border-gold-deep/40 bg-night-900/50 shadow-[0_0_90px_-10px_rgba(0,0,0,0.9)] backdrop-blur-2xl sm:h-[92vh] sm:w-[95vw] sm:rounded-md"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ===== visual hero header — weapon big, character behind, score badge.
             Kept more opaque than the glass body so it anchors the panel. ===== */}
        <div className="relative flex-none overflow-hidden border-b border-gold-deep/30 bg-gradient-to-r from-night-800/95 via-night-900/92 to-night-900/85">
          {/* the Nightfarer, clearly visible on the right and blended into the
              header so it reads as a portrait, not a faint texture */}
          <img
            src={heroArt(character)}
            alt=""
            onError={hide}
            className="pointer-events-none absolute right-0 top-0 h-full w-[52%] object-cover object-[62%_18%] opacity-[0.9]"
            style={{ maskImage: "linear-gradient(90deg, transparent 0%, #000 46%)", WebkitMaskImage: "linear-gradient(90deg, transparent 0%, #000 46%)" }}
          />
          {/* keep the score corner readable over the portrait */}
          <span aria-hidden className="pointer-events-none absolute right-0 top-0 h-full w-[26%]" style={{ background: "linear-gradient(90deg, transparent, rgba(4,6,10,0.72))" }} />
          <div className="relative flex items-center gap-5 px-7 py-6">
            <div
              className="flex h-[100px] w-[100px] flex-none items-center justify-center rounded-sm border border-gold-deep/70 p-2.5"
              style={{ background: "radial-gradient(circle at 50% 40%, rgba(201,162,74,0.18), rgba(8,10,16,0.9) 70%)", boxShadow: "inset 0 0 22px rgba(0,0,0,0.6), 0 0 26px -8px rgba(201,162,74,0.6)" }}
            >
              {b.weapon_icon ? <img src={b.weapon_icon} alt="" onError={hide} className="h-full w-full object-contain drop-shadow" /> : <Swords className="h-10 w-10 text-gold-deep" />}
            </div>
            <div className="min-w-0">
              <div className="font-sans text-[10px] uppercase tracking-[0.2em] text-gold/70">How the engine found this</div>
              <div className="mt-1 truncate font-display text-[27px] font-semibold leading-tight text-ink">{b.weapon}</div>
              <div className="mt-1 truncate font-sans text-[12px] uppercase tracking-wide text-gold/85">
                {b.weapon_type} · {b.vessel} · vs {b.targets.join(", ")}
              </div>
            </div>
            <div className="ml-auto flex-none pr-10 text-right">
              <div className="font-display text-[36px] leading-none tabular-nums text-gold-bright text-glow-gold">{b.score.toFixed(3)}</div>
              <div className="mt-1 font-sans text-[10px] uppercase tracking-[0.18em] text-silver/55">Score S</div>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="absolute right-5 top-5 flex h-9 w-9 flex-none items-center justify-center rounded-sm border border-line/60 bg-night-700/50 text-silver transition hover:border-frost/50 hover:text-ink"
          >
            <X className="h-4.5 w-4.5" />
          </button>
        </div>

        {/* ===== scrollable body ===== */}
        <div className="min-h-0 flex-1 space-y-7 overflow-y-auto px-7 py-7">
          {/* 01 — the score */}
          <Section
            n={1}
            title="The score"
            hint="S is not raw damage. It's how much stronger this loadout is than the bare weapon of the same type — the reference the search compares every candidate against. Offense and survival combine under your damage/survival weight."
          >
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
              <Tile label="Offense" value={`×${b.offense_ratio.toFixed(2)}`} sub="vs the bare weapon" tone="gold" />
              <Tile label="Survival" value={`×${b.survival_ratio.toFixed(2)}`} sub="vs the target" tone="green" />
              {b.absolute_dps != null && <Tile label="Sustained DPS" value={`${Math.round(b.absolute_dps)}${star}`} sub="dmg/hit × cadence" />}
              <Tile label={sourceRows.length > 1 ? "Damage / use" : "Damage / hit"} value={`${Math.round(b.absolute_offense)}${star}`} sub="avg vs target" />
            </div>
            {b.generic && <p className="mt-2.5 text-[11.5px] text-dim">* values are indicative in generic mode (reference weapon: {b.ref_weapon ?? "physical"}).</p>}
          </Section>

          {/* 02 — weapon & payload */}
          <Section
            n={2}
            title={isCaster ? "Why this catalyst & spell" : "Why this weapon"}
            hint={
              mode === "auto"
                ? "In free exploration the optimizer keeps the best build for each weapon type, then ranks the types by sustained DPS."
                : "The optimizer picked the weapon your relic collection makes strongest — not the biggest weapon on paper."
            }
          >
            <div className="space-y-3">
              {typeBuff && (
                <div className="border-l-2 border-gold-deep/60 bg-gold/5 py-2.5 pl-3.5 pr-3 text-[12.5px] leading-relaxed text-silver/85">
                  Carried by <b className="text-gold-bright">your relics</b>: {typeBuff.key}{" "}
                  <b className="tabular-nums text-gold-bright">×{typeBuff.mult.toFixed(2)}</b>. A bigger weapon with no
                  matching relics would score lower — this is the collection talking, not the weapon.
                </div>
              )}
              {isCaster && spellSrc?.label && (
                <div className="border-l-2 border-frost/50 bg-frost/5 py-2.5 pl-3.5 pr-3 text-[12.5px] leading-relaxed text-silver/85">
                  The spell is the payload: <b className="text-frost">{spellSrc.label.replace(/^(Sorcery|Incantation): /, "")}</b>.{" "}
                  {guaranteed ? (
                    <><span className="text-relic-green">Guaranteed</span> on this catalyst — hunting this staff means getting this spell for sure.</>
                  ) : (
                    <><span className="text-[#e0c48a]">2nd, random spell</span> — this catalyst only carries it if you roll it on drop (its guaranteed spell is weaker).</>
                  )}{" "}
                  <span className="text-dim">Slot-1 = fixed by model · slot-2 = random roll. We rank on the guaranteed slot only.</span>
                </div>
              )}
            </div>
            {b.weapon_alternatives.length > 0 && (
              <div className="mt-4">
                <div className="mb-2 text-[11px] uppercase tracking-widest text-silver/55">Runners-up (same class)</div>
                <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                  {b.weapon_alternatives.map((a, i) => (
                    <div key={i} className="flex items-center justify-between gap-3 rounded-sm border border-line/40 bg-night-800/40 px-3 py-2">
                      <div className="min-w-0">
                        <div className="truncate text-[13px] text-silver">{a.name}</div>
                        {a.spell && <div className="truncate text-[10.5px] text-frost/70">{a.spell}</div>}
                      </div>
                      <span className="flex-none font-sans text-[13px] tabular-nums text-[#cf9074]">{`${(100 * (a.ratio - 1)).toFixed(1).replace("-", "−")} %`}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Section>

          {/* 03 — damage sources */}
          {sourceRows.length > 0 && (
            <Section
              n={3}
              title="Damage sources"
              hint="Every way you declared you'd play is replayed against the target and mixed by its share of your damage. Spells are budgeted against your FP pool over one fight — past that, the plan falls back to the weapon."
            >
              <div className="space-y-2.5">
                {sourceRows.map((r) => (
                  <div key={r.action} className="grid grid-cols-[minmax(0,170px)_1fr_auto] items-center gap-x-3.5">
                    <span className="truncate text-[12.5px] text-silver" title={r.info?.label || undefined}>
                      {FR_ACTIONS[r.action] ?? r.action}
                      {r.info?.label && <span className="block truncate text-[10.5px] text-dim">{r.info.label.replace(/^(Sorcery|Incantation): /, "")}</span>}
                    </span>
                    <div className="h-2.5 overflow-hidden rounded-full border border-line-soft bg-night-700">
                      <span className="block h-full rounded-full bg-gradient-to-r from-[#3d4f75] to-frost" style={{ width: `${Math.round(r.share * 100)}%` }} />
                    </div>
                    <span className="w-28 text-right font-sans text-[12px] tabular-nums text-silver/80">
                      {Math.round(r.share * 100)}% · ≈{Math.round(r.hit)}
                      {r.info && r.info.fp_cost > 0 && <span className="text-frost/80"> · {r.info.fp_cost} FP</span>}
                    </span>
                  </div>
                ))}
              </div>
              {theoretical && (
                <p className="mt-3 text-[11.5px] text-frost/80">Absolute spell numbers are theoretical for this build until SPELL_FACTOR is measured (docs/CALIBRATION.md §A).</p>
              )}
              {fpClamps.map(([a, c]) => {
                const gap = c.requested - c.sustainable;
                const spellName = b.sources?.[a]?.label?.replace(/^(Sorcery|Incantation): /, "");
                const msg = `Your FP pool (${b.fp_pool ?? "?"}) sustains ${Math.round(c.sustainable * 100)}% casts of ${spellName ?? FR_ACTIONS[a] ?? a} over a fight`;
                return gap > 0.15 ? (
                  <p key={a} className="mt-3 border border-[#6e5733]/60 bg-[#3a2f1a]/40 px-3 py-2 text-[12px] leading-relaxed text-[#e0c48a]">
                    ⚠ {msg}. You asked for {Math.round(c.requested * 100)}% — the game plan was clamped to what your FP allows.
                  </p>
                ) : (
                  <p key={a} className="mt-2 text-[11.5px] leading-relaxed text-dim">{msg}.</p>
                );
              })}
            </Section>
          )}

          {/* 04 — relics counted vs ignored */}
          <Section
            n={4}
            title="Relics — counted vs ignored"
            hint="Each relic effect is aggregated per damage key and applied to the matching source. Effects tied to an action you did not declare (e.g. critical hits when you never crit) are surfaced but never counted."
          >
            {b.top_effects.length > 0 && (
              <div className="mb-3">
                <div className="mb-1.5 text-[11px] uppercase tracking-widest text-silver/55">Counted — the heaviest effects</div>
                <div className="flex flex-wrap gap-2">
                  {b.top_effects.map((e, i) => (
                    <Chip key={i}>{e.key} <b className="text-gold-bright">×{e.mult.toFixed(2)}</b>{e.action !== "*" && <span className="text-gold/80">{FR_ACTIONS[e.action] ?? e.action}</span>}</Chip>
                  ))}
                </div>
              </div>
            )}
            {b.ignored_effects.length > 0 && (
              <div>
                <div className="mb-1.5 text-[11px] uppercase tracking-widest text-silver/55">Ignored by your profile</div>
                <div className="flex flex-wrap gap-2">
                  {b.ignored_effects.map((e, i) => (
                    <Chip key={i} ghost>{e.key} ×{e.mult.toFixed(2)}<span className="text-gold/70">{FR_ACTIONS[e.action] ?? e.action}</span></Chip>
                  ))}
                </div>
              </div>
            )}
            {b.top_effects.length === 0 && b.ignored_effects.length === 0 && (
              <p className="text-[12.5px] text-dim">No standout relic effects on this build — the score comes from the weapon and the base loadout.</p>
            )}
          </Section>

          {/* 05 — technical figures */}
          {(mults.length > 0 || status.length > 0 || stats.length > 0) && (
            <Section n={5} title="The numbers" hint="Everything the score is built from — relic multipliers by damage type, inflicted status, and stat bonuses.">
              {mults.length > 0 && (
                <div className="mb-4">
                  <div className="mb-1.5 text-[11px] uppercase tracking-widest text-silver/55" title="Cumulative relic bonuses per damage type — applied to the weapon AND to spells of that type.">Multipliers</div>
                  <div className="flex flex-wrap gap-2">{mults.map(([t, m]) => <Chip key={t}><ElemImg type={t} /> {FR_TYPES[t] ?? t} <b className="text-gold-bright">×{m.toFixed(3)}</b></Chip>)}</div>
                </div>
              )}
              {status.length > 0 && (
                <div className="mb-4">
                  <div className="mb-1.5 text-[11px] uppercase tracking-widest text-silver/55" title="Proc damage, hits to the first proc, procs per fight (the threshold rises with each proc).">Status</div>
                  <div className="flex flex-wrap gap-2">
                    {status.map(([st, info]) => (
                      <Chip key={st} color={STATUS_COLOR[st]}>
                        {FR_STATUS[st] ?? st}: proc ~{Math.round(info.proc)}
                        <span className="ml-1 text-gold/80">1st ≈ {Math.round(info.first_hits)} · {info.fight_procs.toFixed(1)}/fight</span>
                      </Chip>
                    ))}
                  </div>
                </div>
              )}
              {stats.length > 0 && (
                <div>
                  <div className="mb-1.5 text-[11px] uppercase tracking-widest text-silver/55">Stat bonuses</div>
                  <div className="flex flex-wrap gap-2">{stats.map(([f, v]) => <Chip key={f}>{FR_STATS[f] ?? f.replace("stat", "")} <b className="text-gold-bright">+{v}</b></Chip>)}</div>
                </div>
              )}
            </Section>
          )}

          {/* 06 — economy */}
          {(b.stamina || b.fp_pool != null || b.kit) && (
            <Section n={6} title="Economy" hint="Resource limits that shape the game plan.">
              <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
                {b.stamina && <Tile label="Stamina" value={`~${b.stamina.hits_per_bar}/bar`} sub={`pool ${b.stamina.pool} · R1 ${b.stamina.r1_cost} (regen unmeasured — info)`} />}
                {b.fp_pool != null && <Tile label="FP pool" value={String(b.fp_pool)} sub="45 + 5 × Mind — budgets casts" tone="frost" />}
                {b.kit && <Tile label="Kit factor" value={`×${b.kit.factor.toFixed(2)}`} sub={Object.entries(b.kit.details).map(([n, d]) => `${n} ×${d.factor}`).join(" · ")} />}
              </div>
            </Section>
          )}

          {/* 07 — grounding & limits (the truth-first section) */}
          <Section
            n={7}
            title="Grounding & limits"
            hint="This tool is built on Nightreign's own params (regulation.bin) and in-game measurements — never invented numbers. Here's what's solid and what isn't yet."
          >
            <div className="mb-4">
              <div className="mb-2 text-[11px] uppercase tracking-widest text-relic-green/70">Calibrated on real data</div>
              <div className="flex flex-wrap gap-2">
                <Chip color="#3f6b4f">Attack rating <span className="text-relic-green">✓</span></Chip>
                <Chip color="#3f6b4f">Spell damage {theoretical ? <span className="text-[#e0c48a]">(this build: theoretical)</span> : <span className="text-relic-green">✓</span>}</Chip>
                <Chip color="#3f6b4f">FP = 45 + 5×Mind <span className="text-relic-green">✓</span></Chip>
                <Chip color="#3f6b4f">Stamina = 48 + 2×END <span className="text-relic-green">✓</span></Chip>
                <Chip color="#3f6b4f">Poison / Rot / Frost <span className="text-relic-green">✓</span></Chip>
                <Chip color="#3f6b4f">Guaranteed vs rolled spell <span className="text-relic-green">✓</span></Chip>
              </div>
            </div>
            <div>
              <div className="mb-2 text-[11px] uppercase tracking-widest text-[#e0c48a]/70">Not modeled yet</div>
              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                {limits.map((l) => (
                  <div key={l.title} className="rounded-sm border border-line/45 bg-night-800/40 p-3">
                    <div className="flex items-center gap-2 text-[12.5px] font-medium text-silver">
                      <span className="h-1.5 w-1.5 flex-none rotate-45 bg-[#e0c48a]/70" />
                      {l.title}
                    </div>
                    <div className="mt-1.5 text-[11.5px] leading-relaxed text-silver/60">{l.body}</div>
                  </div>
                ))}
              </div>
            </div>
          </Section>
        </div>
      </div>
    </div>
  );
}
