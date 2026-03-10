import { ExternalLink, FileAudio2, FileText, Globe2, NotebookPen, Trash2, Youtube } from "lucide-react";
import { motion } from "framer-motion";
import type { SourceDocument } from "@/lib/api";
import { springs } from "@/animations/motion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, fileTypeLabel, formatRelativeTime } from "@/lib/utils";

type DocumentOrbProps = {
  document: SourceDocument;
  isSelected: boolean;
  isActive: boolean;
  onSelect: () => void;
  onHover: (sourceId: string | null) => void;
  onDelete: () => void;
  onOpen: () => void;
};

const icons = {
  pdf: FileText,
  txt: NotebookPen,
  audio: FileAudio2,
  youtube: Youtube,
  website: Globe2
};

export function DocumentOrb({ document, isSelected, isActive, onSelect, onHover, onDelete, onOpen }: DocumentOrbProps): JSX.Element {
  const Icon = icons[document.type];

  return (
    <motion.article
      className={cn(
        "rounded-2xl border bg-[color:var(--surface-2)] p-4 transition",
        isActive ? "border-[color:var(--panel-border-strong)]" : "border-[color:var(--panel-border)] hover:border-[color:var(--panel-border-strong)]"
      )}
      onMouseEnter={() => onHover(document.id)}
      onMouseLeave={() => onHover(null)}
      transition={springs.cardHover}
      whileHover={{ y: -2 }}
    >
      <div className="flex gap-3">
        <button
          className="flex min-w-0 flex-1 gap-3 text-left"
          type="button"
          onClick={onSelect}
        >
          <div
            className="mt-0.5 grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-[color:var(--panel-border)] bg-[color:var(--surface-3)]"
            style={{ boxShadow: `inset 0 1px 0 rgba(255,255,255,0.45), 0 10px 24px ${document.accent}2d` }}
          >
            <Icon className="h-4.5 w-4.5 text-[color:var(--text-primary)]" />
          </div>

          <div className="min-w-0 flex-1">
            <p className="line-clamp-2 text-[15px] font-semibold leading-6 text-[color:var(--text-primary)]">{document.title}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              <Badge variant="secondary">{fileTypeLabel(document.type)}</Badge>
              <Badge variant={document.status === "ready" ? "success" : document.status === "processing" ? "warning" : "destructive"}>{document.backendStatus}</Badge>
              {isSelected ? <Badge className="bg-[color:var(--chip-accent-bg)] text-[color:var(--chip-accent-text)]">attached</Badge> : null}
            </div>
            <p className="mt-3 line-clamp-2 text-sm leading-6 text-[color:var(--text-muted)]">{document.summary}</p>
            <div className="mt-3 flex items-center justify-between text-xs text-[color:var(--text-kicker)]">
              <span>{document.chunks} chunks</span>
              <span>{formatRelativeTime(document.updatedAt)}</span>
            </div>
            {document.status !== "ready" ? (
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-[color:var(--surface-3)]">
                <div className="h-full rounded-full transition-all" style={{ width: `${document.progress}%`, background: document.accent }} />
              </div>
            ) : null}
          </div>
        </button>

        <div className="flex flex-col gap-1">
          <Button aria-label={`Open ${document.title}`} size="sm" variant="ghost" onClick={onOpen}>
            <ExternalLink className="h-4 w-4" />
          </Button>
          <Button aria-label={`Delete ${document.title}`} size="sm" variant="ghost" onClick={onDelete}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </motion.article>
  );
}
