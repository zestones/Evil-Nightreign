import * as T from "@radix-ui/react-tooltip";

export function TooltipRoot({ children }: { children: React.ReactNode }) {
  return (
    <T.Provider delayDuration={120} skipDelayDuration={300}>
      {children}
    </T.Provider>
  );
}

export function Tip({
  content,
  children,
}: {
  content: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <T.Root>
      <T.Trigger asChild>{children}</T.Trigger>
      <T.Portal>
        <T.Content
          sideOffset={6}
          className="z-50 max-w-[280px] border border-line/70 bg-night-900/95 px-3 py-2 text-[12.5px] text-silver shadow-xl backdrop-blur-xl"
        >
          {content}
          <T.Arrow className="fill-night-900" />
        </T.Content>
      </T.Portal>
    </T.Root>
  );
}
