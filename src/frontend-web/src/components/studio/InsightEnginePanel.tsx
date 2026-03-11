import { BarChart3, BookOpenCheck, BrainCircuit, Network } from "lucide-react";
import type { InsightSnapshot } from "@/lib/api";

const stats = [
  { key: "totalSources", label: "Sources", icon: BookOpenCheck },
  { key: "totalChunks", label: "Chunks", icon: BarChart3 },
  { key: "totalEmbeddings", label: "Embeddings", icon: BrainCircuit },
  { key: "relationCount", label: "Links", icon: Network }
] as const;

export function InsightEnginePanel({ insight }: { insight: InsightSnapshot }): JSX.Element {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2.5">
        {stats.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.key} className="rounded-xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-3">
              <div className="flex items-center gap-1.5 text-[color:var(--text-kicker)]">
                <Icon className="h-4 w-4" />
                <span className="text-[11px] uppercase tracking-[0.2em]">{item.label}</span>
              </div>
              <p className="mt-2 text-xl font-semibold text-[color:var(--text-primary)]">{insight[item.key]}</p>
            </div>
          );
        })}
      </div>

      <div className="space-y-2.5">
        {insight.summaries.map((summary) => (
          <article key={summary.id} className="min-w-0 overflow-hidden rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4">
            <h3 className="break-words text-sm font-semibold text-[color:var(--text-primary)]">{summary.title}</h3>
            <p className="mt-2 break-words text-sm leading-6 text-[color:var(--text-muted)]">{summary.summary}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
