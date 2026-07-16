import * as C from "@radix-ui/react-checkbox";
import { cn } from "@/lib/cn";

/** Diamond-shaped rune toggle. */
export function Toggle({
  checked,
  onCheckedChange,
  label,
}: {
  checked: boolean;
  onCheckedChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <label className="group flex cursor-pointer items-start gap-3 py-1.5">
      <C.Root
        checked={checked}
        onCheckedChange={(v) => onCheckedChange(Boolean(v))}
        className={cn(
          "mt-0.5 flex h-[15px] w-[15px] flex-none rotate-45 items-center justify-center border border-line bg-night-700 transition",
          "group-hover:border-line-bright",
          "data-[state=checked]:border-frost data-[state=checked]:bg-[radial-gradient(circle,#bcd6f2,#3a5a86)] data-[state=checked]:shadow-[0_0_9px_rgba(143,182,230,0.7)]"
        )}
      >
        <C.Indicator />
      </C.Root>
      <span className="text-[13.5px] leading-snug text-silver transition group-hover:text-ink">
        {label}
      </span>
    </label>
  );
}
