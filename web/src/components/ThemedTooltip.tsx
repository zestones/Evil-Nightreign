import { useEffect, useRef, useState } from "react";

// One global tooltip that replaces the browser's default gray `title=` box with
// a themed one — WITHOUT touching the ~30 `title=` call sites. On hover it reads
// the element's native `title`, stashes it, strips the attribute (so the OS
// tooltip never shows), and renders our own box positioned to the element.
type TipState = { text: string; left: number; top: number; above: boolean } | null;

const STASH = "data-native-title";

export function ThemedTooltip() {
  const [tip, setTip] = useState<TipState>(null);
  const active = useRef<HTMLElement | null>(null);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    const restore = (el: HTMLElement) => {
      const n = el.getAttribute(STASH);
      if (n && !el.getAttribute("title")) el.setAttribute("title", n);
      el.removeAttribute(STASH);
    };
    const hide = () => {
      if (timer.current) {
        clearTimeout(timer.current);
        timer.current = null;
      }
      if (active.current) {
        restore(active.current);
        active.current = null;
      }
      setTip(null);
    };
    const show = (el: HTMLElement) => {
      const text = el.getAttribute("title");
      if (!text) return;
      el.setAttribute(STASH, text);
      el.removeAttribute("title"); // kill the native tooltip
      active.current = el;
      timer.current = window.setTimeout(() => {
        const r = el.getBoundingClientRect();
        const above = r.top > window.innerHeight - r.bottom;
        setTip({
          text,
          left: Math.min(Math.max(r.left + r.width / 2, 140), window.innerWidth - 140),
          top: above ? r.top - 8 : r.bottom + 8,
          above,
        });
      }, 140);
    };
    const onOver = (e: MouseEvent) => {
      const el = (e.target as HTMLElement | null)?.closest?.("[title]") as HTMLElement | null;
      if (el && el !== active.current) {
        hide();
        show(el);
      }
    };
    const onOut = (e: MouseEvent) => {
      if (!active.current) return;
      const to = e.relatedTarget as Node | null;
      if (!to || !active.current.contains(to)) hide();
    };
    document.addEventListener("mouseover", onOver);
    document.addEventListener("mouseout", onOut);
    window.addEventListener("scroll", hide, true);
    window.addEventListener("wheel", hide, { passive: true });
    return () => {
      document.removeEventListener("mouseover", onOver);
      document.removeEventListener("mouseout", onOut);
      window.removeEventListener("scroll", hide, true);
      window.removeEventListener("wheel", hide);
      hide();
    };
  }, []);

  if (!tip) return null;
  return (
    <div
      role="tooltip"
      className="pointer-events-none fixed z-[70] max-w-[300px] border border-gold-deep/50 bg-night-900/95 px-3 py-2 text-[12px] leading-relaxed text-silver shadow-[0_10px_34px_-8px_rgba(0,0,0,0.9)] backdrop-blur-xl"
      style={{ left: tip.left, top: tip.top, transform: `translate(-50%, ${tip.above ? "-100%" : "0"})` }}
    >
      <span aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gold/50 to-transparent" />
      {tip.text}
    </div>
  );
}
