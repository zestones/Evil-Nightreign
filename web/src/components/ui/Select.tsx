import * as S from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";

export interface Option {
  value: string;
  label: string;
}

export function Select({
  value,
  onValueChange,
  options,
  placeholder,
  className,
}: {
  value: string;
  onValueChange: (v: string) => void;
  options: Option[];
  placeholder?: string;
  className?: string;
}) {
  return (
    <S.Root value={value} onValueChange={onValueChange}>
      <S.Trigger
        className={cn(
          "group flex w-full items-center justify-between gap-2 border border-line/70 bg-night-700/70 px-3 py-2.5 text-[14.5px] text-ink outline-none transition",
          "hover:border-line-bright focus:border-frost/70 focus:shadow-[0_0_0_1px_rgba(143,182,230,0.25)] data-[placeholder]:text-dim",
          className
        )}
      >
        <S.Value placeholder={placeholder} />
        <S.Icon>
          <ChevronDown className="h-4 w-4 text-silver/70 transition group-data-[state=open]:rotate-180" />
        </S.Icon>
      </S.Trigger>
      <S.Portal>
        <S.Content
          position="popper"
          sideOffset={6}
          className="z-50 max-h-[320px] min-w-[var(--radix-select-trigger-width)] overflow-hidden border border-line/70 bg-night-800/95 shadow-2xl backdrop-blur-xl"
        >
          <S.Viewport className="p-1">
            {options.map((o) => (
              <S.Item
                key={o.value}
                value={o.value}
                className="relative flex cursor-pointer select-none items-center gap-2 px-3 py-2 text-[14px] text-silver outline-none data-[highlighted]:bg-night-600/80 data-[highlighted]:text-ink data-[state=checked]:text-gold-bright"
              >
                <S.ItemText>{o.label}</S.ItemText>
                <S.ItemIndicator className="ml-auto">
                  <Check className="h-3.5 w-3.5" />
                </S.ItemIndicator>
              </S.Item>
            ))}
          </S.Viewport>
        </S.Content>
      </S.Portal>
    </S.Root>
  );
}
