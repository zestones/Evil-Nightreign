import * as S from "@radix-ui/react-slider";
import { cn } from "@/lib/cn";

/** Offense <-> Survival gauge. Track shows gold (offense) to green (survival). */
export function Gauge({
  value,
  onValueChange,
  className,
}: {
  value: number; // 0..100
  onValueChange: (v: number) => void;
  className?: string;
}) {
  return (
    <S.Root
      className={cn("relative flex h-5 w-full touch-none select-none items-center", className)}
      value={[value]}
      onValueChange={([v]) => onValueChange(v)}
      min={0}
      max={100}
      step={1}
    >
      <S.Track className="relative h-[6px] w-full grow overflow-hidden rounded-full bg-gradient-to-r from-gold via-gold/40 to-relic-green opacity-90">
        <S.Range className="absolute h-full bg-transparent" />
      </S.Track>
      <S.Thumb
        aria-label="Offense / Survie"
        className="block h-4 w-4 rounded-full border border-black/40 bg-[radial-gradient(circle_at_35%_30%,#efd8a0,#7c6531)] shadow-[0_0_12px_rgba(201,162,74,0.8)] outline-none transition focus:shadow-[0_0_16px_rgba(201,162,74,1)]"
      />
    </S.Root>
  );
}
