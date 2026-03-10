import { Orbit, Waves } from "lucide-react";
import { Button } from "@/components/ui/button";

type FloatingToolbarProps = {
  reducedMotion: boolean;
  onToggleMotion: () => void;
};

export function FloatingToolbar({ reducedMotion, onToggleMotion }: FloatingToolbarProps): JSX.Element {
  return (
    <div className="pointer-events-auto inline-flex items-center gap-2 rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-2)]/88 px-3 py-2 text-xs text-[color:var(--text-muted)] shadow-soft-card backdrop-blur-xl">
      <span className="inline-flex items-center gap-2 rounded-full bg-[color:var(--chip-accent-bg)] px-3 py-1 text-[color:var(--chip-accent-text)]">
        <Orbit className="h-3.5 w-3.5" />
        Linked sources
      </span>
      <Button className="h-8 rounded-full px-3 text-xs text-[color:var(--text-primary)]" size="sm" variant="ghost" onClick={onToggleMotion}>
        <Waves className="h-3.5 w-3.5" />
        {reducedMotion ? "Calm" : "Motion"}
      </Button>
    </div>
  );
}
