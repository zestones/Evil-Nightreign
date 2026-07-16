import { cn } from "@/lib/cn";

type Tone = "cold" | "gold" | "prime";

const TONE: Record<Tone, string> = {
  cold: "border-line/50",
  gold: "border-gold-deep/60",
  prime: "border-gold-deep/70",
};

function Corner({ pos, tone }: { pos: string; tone: Tone }) {
  const color = tone === "cold" ? "border-silver/45" : "border-gold/55";
  return (
    <span
      aria-hidden
      className={cn(
        "pointer-events-none absolute h-3.5 w-3.5",
        color,
        pos.includes("t") ? "top-[-1px] border-t" : "bottom-[-1px] border-b",
        pos.includes("l") ? "left-[-1px] border-l" : "right-[-1px] border-r"
      )}
    />
  );
}

export function Frame({
  className,
  children,
  tone = "cold",
}: {
  className?: string;
  children: React.ReactNode;
  tone?: Tone;
}) {
  return (
    <div
      className={cn(
        "relative border bg-night-800/70 backdrop-blur-md",
        TONE[tone],
        tone === "prime" &&
          "shadow-[0_0_46px_-18px_rgba(201,162,74,0.55)]",
        className
      )}
    >
      {/* faint inner keyline */}
      <span
        aria-hidden
        className="pointer-events-none absolute inset-[5px] border border-white/[0.04]"
      />
      <Corner pos="tl" tone={tone} />
      <Corner pos="tr" tone={tone} />
      <Corner pos="bl" tone={tone} />
      <Corner pos="br" tone={tone} />
      {children}
    </div>
  );
}
