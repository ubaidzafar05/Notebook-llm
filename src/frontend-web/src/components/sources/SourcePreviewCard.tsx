import type { SourceDocument } from "@/lib/api";

type SourcePreviewCardProps = {
  document: SourceDocument | null;
};

export function SourcePreviewCard({ document }: SourcePreviewCardProps): JSX.Element {
  if (!document) {
    return (
      <div className="rounded-2xl border border-dashed border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4 text-sm leading-6 text-[color:var(--text-muted)]">
        Hover a source to preview the excerpt used for grounding answers.
      </div>
    );
  }

  return (
    <div className="min-w-0 overflow-hidden rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4">
      <div className="mb-3 flex items-center gap-2.5">
        <div className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: document.accent }} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-[11px] uppercase tracking-[0.24em] text-[color:var(--text-kicker)]">{document.preview.headline}</p>
          <h3 className="break-words text-sm font-semibold text-[color:var(--text-primary)]">{document.title}</h3>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 text-xs text-[color:var(--text-muted)]">
        {document.preview.metadata.map((item) => (
          <span key={item} className="rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] px-2.5 py-1">
            {item}
          </span>
        ))}
      </div>

      <p className="mt-3 break-words text-sm leading-6 text-[color:var(--text-primary)]">{document.preview.excerpt}</p>
    </div>
  );
}
