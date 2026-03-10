import { Search } from "lucide-react";
import type { SourceDocument } from "@/lib/api";
import { PanelShell } from "@/components/layout/PanelShell";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { DocumentOrb } from "@/components/sources/DocumentOrb";
import { SourcePreviewCard } from "@/components/sources/SourcePreviewCard";
import { UploadDropzone } from "@/components/sources/UploadDropzone";

type SourceNebulaProps = {
  documents: SourceDocument[];
  isLoading: boolean;
  isUploading: boolean;
  searchValue: string;
  previewDocument: SourceDocument | null;
  selectedDocumentIds: string[];
  activeDocumentId: string | null;
  activityMessage?: string | null;
  canCancelJob?: boolean;
  onSearchChange: (value: string) => void;
  onUploadFile: (file: File) => Promise<void>;
  onIngestUrl: (payload: { url: string; sourceType: "website" | "youtube" }) => Promise<void>;
  onSelectDocument: (sourceId: string) => void;
  onHoverDocument: (sourceId: string | null) => void;
  onDeleteDocument: (sourceId: string) => void;
  onOpenDocument: (sourceId: string) => void;
  onCancelJob?: () => Promise<void>;
};

export function SourceNebula({
  documents,
  isLoading,
  isUploading,
  searchValue,
  previewDocument,
  selectedDocumentIds,
  activeDocumentId,
  activityMessage,
  canCancelJob = false,
  onSearchChange,
  onUploadFile,
  onIngestUrl,
  onSelectDocument,
  onHoverDocument,
  onDeleteDocument,
  onOpenDocument,
  onCancelJob,
}: SourceNebulaProps): JSX.Element {
  return (
    <PanelShell className="flex h-full min-h-[680px] flex-col p-5">
      {/* Header */}
      <header className="mb-4 px-1">
        <p className="text-[10px] uppercase tracking-[0.3em] text-[color:var(--text-kicker)]">Sources</p>
        <div className="mt-1.5 flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-[color:var(--text-hero)]">Source gallery</h2>
          <span className="rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] px-2.5 py-1 text-[11px] text-[color:var(--text-muted)]">
            {documents.length} items
          </span>
        </div>
      </header>

      {/* Upload zone */}
      <UploadDropzone isUploading={isUploading} onIngestUrl={onIngestUrl} onUploadFile={onUploadFile} />

      {/* Activity message */}
      {activityMessage ? (
        <div className="mt-3 rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] px-4 py-3 text-sm text-[color:var(--text-primary)]">
          <div className="flex items-center justify-between gap-2">
            <span>{activityMessage}</span>
            {canCancelJob && onCancelJob ? (
              <Button size="sm" variant="outline" onClick={() => void onCancelJob()}>
                Cancel
              </Button>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* Preview card */}
      <div className="mt-4">
        <SourcePreviewCard document={previewDocument} />
      </div>

      {/* Source filter */}
      <div className="mt-4 flex items-center gap-2 rounded-xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] px-3 py-1.5">
        <Search className="h-3.5 w-3.5 text-[color:var(--text-kicker)]" />
        <Input
          aria-label="Filter notebook sources"
          className="h-8 border-0 bg-transparent px-0 shadow-none focus-visible:ring-0"
          placeholder="Search sources"
          value={searchValue}
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </div>

      {/* Source list */}
      <ScrollArea className="mt-4 flex-1 pr-1">
        <div className="space-y-3 pb-1">
          {isLoading
            ? Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-36 w-full rounded-2xl" />)
            : documents.map((document) => (
              <DocumentOrb
                key={document.id}
                document={document}
                isActive={activeDocumentId === document.id}
                isSelected={selectedDocumentIds.includes(document.id)}
                onDelete={() => onDeleteDocument(document.id)}
                onHover={onHoverDocument}
                onOpen={() => onOpenDocument(document.id)}
                onSelect={() => onSelectDocument(document.id)}
              />
            ))}
        </div>
      </ScrollArea>
    </PanelShell>
  );
}
