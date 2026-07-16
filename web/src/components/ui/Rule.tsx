import { cn } from "@/lib/cn";

/** Thin divider with a central diamond node. */
export function Rule({
  className,
  tone = "cold",
}: {
  className?: string;
  tone?: "cold" | "gold";
}) {
  const line = tone === "gold" ? "goldline" : "hairline";
  const node = tone === "gold" ? "bg-gold shadow-[0_0_8px_#c9a24a]" : "bg-silver/80 shadow-[0_0_8px_rgba(157,175,200,0.6)]";
  return (
    <div className={cn("flex items-center gap-3", className)}>
      <span className={cn("h-px flex-1", line)} />
      <span className={cn("h-[6px] w-[6px] rotate-45", node)} />
      <span className={cn("h-px flex-1", line)} />
    </div>
  );
}
