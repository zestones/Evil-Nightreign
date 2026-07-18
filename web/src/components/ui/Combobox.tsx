import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Check, ChevronDown, Search } from "lucide-react";
import { cn } from "@/lib/cn";
import type { Option } from "./Select";

// A searchable dropdown (type to filter) for the long lists — play-profile
// actions and weapon types. Same look as <Select>, but the panel is portaled
// to <body> with fixed positioning so the page scroll never clips it, and it
// carries a search box. No extra dependency.
export function Combobox({
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
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [rect, setRect] = useState<DOMRect | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const selected = options.find((o) => o.value === value);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? options.filter((o) => o.label.toLowerCase().includes(q)) : options;
  }, [options, query]);

  const place = () => {
    if (triggerRef.current) setRect(triggerRef.current.getBoundingClientRect());
  };
  useLayoutEffect(() => {
    if (open) place();
  }, [open]);
  useEffect(() => {
    if (!open) return;
    inputRef.current?.focus();
    const onScroll = () => place();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node;
      if (!panelRef.current?.contains(t) && !triggerRef.current?.contains(t)) setOpen(false);
    };
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", onScroll);
    window.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onDown, true);
    return () => {
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onScroll);
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onDown, true);
    };
  }, [open]);

  const pick = (v: string) => {
    onValueChange(v);
    setOpen(false);
    setQuery("");
  };

  // open upward when there isn't room below
  const below = rect ? window.innerHeight - rect.bottom : 0;
  const above = rect ? rect.top : 0;
  const dropUp = rect ? below < 260 && above > below : false;

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "group flex w-full items-center justify-between gap-2 border border-line/70 bg-night-700/70 px-3 py-2.5 text-[14.5px] text-ink outline-none transition",
          "hover:border-line-bright focus:border-frost/70 focus:shadow-[0_0_0_1px_rgba(143,182,230,0.25)]",
          open && "border-frost/70",
          className
        )}
      >
        <span className={cn("truncate", !selected && "text-dim")}>{selected ? selected.label : placeholder ?? "Select…"}</span>
        <ChevronDown className={cn("h-4 w-4 flex-none text-silver/70 transition", open && "rotate-180")} />
      </button>

      {open && rect &&
        createPortal(
          <div
            ref={panelRef}
            className="fixed z-[80] flex flex-col overflow-hidden border border-line/70 bg-night-800/97 shadow-2xl backdrop-blur-xl"
            style={{
              left: rect.left,
              width: rect.width,
              top: dropUp ? undefined : rect.bottom + 6,
              bottom: dropUp ? window.innerHeight - rect.top + 6 : undefined,
            }}
          >
            <div className="flex items-center gap-2 border-b border-line/50 px-3 py-2">
              <Search className="h-3.5 w-3.5 flex-none text-silver/50" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search…"
                className="w-full bg-transparent text-[13.5px] text-ink placeholder:text-dim outline-none"
              />
            </div>
            <div className="max-h-[260px] overflow-y-auto p-1">
              {filtered.length === 0 && <div className="px-3 py-4 text-center text-[12.5px] text-dim">No match</div>}
              {filtered.map((o) => (
                <button
                  key={o.value}
                  type="button"
                  onClick={() => pick(o.value)}
                  className={cn(
                    "flex w-full cursor-pointer select-none items-center gap-2 px-3 py-2 text-left text-[14px] outline-none transition",
                    o.value === value ? "text-gold-bright" : "text-silver hover:bg-night-600/80 hover:text-ink"
                  )}
                >
                  <span className="truncate">{o.label}</span>
                  {o.value === value && <Check className="ml-auto h-3.5 w-3.5 flex-none" />}
                </button>
              ))}
            </div>
          </div>,
          document.body
        )}
    </>
  );
}
