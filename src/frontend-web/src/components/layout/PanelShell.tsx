import type { PropsWithChildren } from "react";
import { cn } from "@/lib/utils";

type PanelShellProps = PropsWithChildren<{
  className?: string;
}>;

export function PanelShell({ children, className }: PanelShellProps): JSX.Element {
  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-3xl border border-[color:var(--panel-border)] bg-[color:var(--panel-bg)] shadow-panel backdrop-blur-xl",
        className
      )}
    >
      <div className="pointer-events-none absolute inset-0 bg-[var(--panel-glow)] opacity-40" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(180deg,var(--panel-sheen),transparent_18%)]" />
      <div className="relative h-full">{children}</div>
    </section>
  );
}
