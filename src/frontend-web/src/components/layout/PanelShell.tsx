import type { PropsWithChildren } from "react";
import { cn } from "@/lib/utils";

type PanelShellProps = PropsWithChildren<{
  className?: string;
}>;

export function PanelShell({ children, className }: PanelShellProps): JSX.Element {
  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-2xl border border-[color:var(--border-soft)] bg-[color:var(--surface-1)] shadow-soft-card",
        className
      )}
    >
      <div className="relative flex h-full min-h-0 flex-col">{children}</div>
    </section>
  );
}
