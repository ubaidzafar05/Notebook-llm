import { ExternalLink, FileText } from "lucide-react";
import { motion } from "framer-motion";
import type { Citation } from "@/lib/api";
import { Button } from "@/components/ui/button";

type CitationGlowCardProps = {
  citation: Citation;
  onHover: (sourceId: string | null) => void;
  onOpen: (citation: Citation) => void;
};

export function CitationGlowCard({ citation, onHover, onOpen }: CitationGlowCardProps): JSX.Element {
  return (
    <motion.div
      className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] p-4"
      whileHover={{ y: -1 }}
      onMouseEnter={() => onHover(citation.sourceId)}
      onMouseLeave={() => onHover(null)}
    >
      <div className="flex items-start gap-2.5">
        <div className="rounded-xl bg-[color:var(--chip-accent-bg)] p-2 text-[color:var(--chip-accent-text)]">
          <FileText className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-[color:var(--text-primary)]">{citation.documentTitle}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-[color:var(--text-kicker)]">
            <span>{citation.pageNumber ? `Page ${citation.pageNumber}` : "Referenced excerpt"}</span>
            {citation.qualityLabel ? (
              <span className="rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] px-2 py-0.5 text-[10px] uppercase tracking-[0.2em]">
                {citation.qualityLabel}
              </span>
            ) : null}
          </div>
        </div>
      </div>
      <p className="mt-3 line-clamp-3 text-sm leading-6 text-[color:var(--text-muted)]">{citation.excerpt}</p>
      <Button className="mt-3 w-full" size="sm" variant="outline" onClick={() => onOpen(citation)}>
        <ExternalLink className="h-4 w-4" />
        Open source
      </Button>
    </motion.div>
  );
}
