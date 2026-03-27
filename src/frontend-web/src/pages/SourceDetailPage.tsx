import { useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ArrowLeft, Loader2, Trash2 } from "lucide-react";
import { useAppTheme } from "@/hooks/use-app-theme";
import { useNotebookQuery, useNotebookSourceQuery, useSourceChunksQuery, useSourceMutations } from "@/hooks/use-workspace-queries";
import { ApiError, type ThemeMode } from "@/lib/api";
import { TopChrome } from "@/components/layout/TopChrome";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useWorkspaceStore } from "@/store/use-workspace-store";

export function SourceDetailPage(): JSX.Element {
  useAppTheme();
  const navigate = useNavigate();
  const { notebookId = "", sourceId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const themeMode = useWorkspaceStore((state) => state.studioState.themeMode);
  const setThemeMode = useWorkspaceStore((state) => state.setThemeMode);
  const [searchValue, setSearchValue] = useState("");
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const notebookQuery = useNotebookQuery(notebookId, Boolean(notebookId));
  const sourceQuery = useNotebookSourceQuery(notebookId, sourceId, Boolean(notebookId && sourceId));
  const chunksQuery = useSourceChunksQuery(notebookId, sourceId, 50, offset, Boolean(notebookId && sourceId));
  const sourceMutations = useSourceMutations(notebookId);
  const highlightedChunkId = searchParams.get("chunk");

  const filteredChunks = useMemo(() => {
    const chunks = chunksQuery.data?.chunks ?? [];
    const term = searchValue.trim().toLowerCase();
    if (!term) {
      return chunks;
    }
    return chunks.filter((chunk) => chunk.excerpt.toLowerCase().includes(term));
  }, [chunksQuery.data?.chunks, searchValue]);

  async function handleDelete(): Promise<void> {
    const source = sourceQuery.data;
    if (!source) {
      return;
    }
    try {
      await sourceMutations.deleteSource.mutateAsync(source.id);
      setConfirmOpen(false);
      navigate(`/notebooks/${notebookId}`);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Delete failed.");
    }
  }

  const source = sourceQuery.data;

  return (
    <div className="min-h-screen">
      <ConfirmDialog
        confirmLabel="Delete source"
        description={
          source
            ? `Delete ${source.title} and remove its indexed chunks from this notebook. This cannot be undone.`
            : ""
        }
        isPending={sourceMutations.deleteSource.isPending}
        open={confirmOpen}
        title="Delete source?"
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() => void handleDelete()}
      />
      <TopChrome
        notebookTitle={notebookQuery.data?.title ?? "Source detail"}
        onHome={() => navigate("/notebooks")}
        onSearchChange={setSearchValue}
        onThemeChange={(mode: ThemeMode) => setThemeMode(mode)}
        searchPlaceholder="Search chunks in this source"
        searchValue={searchValue}
        statusLabel={source ? `${source.chunks} chunks` : "Loading source"}
        themeMode={themeMode}
      />
      <main className="mx-auto max-w-[1760px] px-4 py-6 sm:px-6">
        <div className="mb-5 flex items-center justify-between gap-3">
          <Button asChild variant="outline">
            <Link to={`/notebooks/${notebookId}`}>
              <ArrowLeft className="h-4 w-4" />
              Back to notebook
            </Link>
          </Button>
          <Button disabled={sourceMutations.deleteSource.isPending} variant="outline" onClick={() => setConfirmOpen(true)}>
            {sourceMutations.deleteSource.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            Delete source
          </Button>
        </div>

        <section className="grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
          <aside className="rounded-[2rem] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-5 shadow-panel">
            {source ? (
              <>
                <p className="text-xs uppercase tracking-[0.28em] text-[color:var(--text-kicker)]">Source overview</p>
                <h1 className="mt-3 font-serif text-3xl text-[color:var(--text-hero)]">{source.title}</h1>
                <p className="mt-4 text-sm leading-7 text-[color:var(--text-muted)]">{source.summary}</p>
                <dl className="mt-6 space-y-3 text-sm text-[color:var(--text-primary)]">
                  <div className="flex items-center justify-between gap-3"><dt>Status</dt><dd>{source.backendStatus}</dd></div>
                  <div className="flex items-center justify-between gap-3"><dt>Type</dt><dd>{source.type}</dd></div>
                  <div className="flex items-center justify-between gap-3"><dt>Chunks</dt><dd>{source.chunks}</dd></div>
                  <div className="flex items-center justify-between gap-3"><dt>Location</dt><dd className="max-w-[180px] truncate">{source.pathOrUrl}</dd></div>
                </dl>
                {error ? <p className="mt-4 rounded-xl border border-[color:hsl(var(--destructive)/0.3)] bg-[color:hsl(var(--destructive)/0.1)] px-3 py-2 text-sm text-[color:hsl(var(--destructive))]">{error}</p> : null}
              </>
            ) : (
              <Loader2 className="h-5 w-5 animate-spin text-[color:var(--accent-soft)]" />
            )}
          </aside>

          <section className="rounded-[2rem] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-5 shadow-panel">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-[color:var(--text-kicker)]">Chunk inspector</p>
                <h2 className="mt-2 font-serif text-3xl text-[color:var(--text-hero)]">Indexed excerpts</h2>
              </div>
              {chunksQuery.isLoading ? <Loader2 className="h-5 w-5 animate-spin text-[color:var(--accent-soft)]" /> : null}
            </div>
            <div className="mt-5 space-y-4">
              {filteredChunks.map((chunk) => (
                <article
                  key={chunk.chunkId}
                  className={[
                    "rounded-[1.5rem] border bg-[color:var(--response-bg)] p-4 shadow-soft-card",
                    highlightedChunkId === chunk.chunkId
                      ? "border-[color:var(--panel-border-strong)] ring-2 ring-[color:var(--focus-ring-strong)]"
                      : "border-[color:var(--panel-border)]"
                  ].join(" ")}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-[color:var(--text-primary)]">Chunk {chunk.chunkIndex + 1}</p>
                    <span className="text-xs text-[color:var(--text-kicker)]">{typeof chunk.citation.page_number === "number" ? `Page ${chunk.citation.page_number}` : "Notebook excerpt"}</span>
                  </div>
                  <p className="mt-3 text-sm leading-7 text-[color:var(--text-primary)]">{chunk.excerpt}</p>
                </article>
              ))}
              {!chunksQuery.isLoading && filteredChunks.length === 0 ? (
                <div className="rounded-[1.5rem] border border-dashed border-[color:var(--panel-border)] bg-[color:var(--surface-3)] p-5 text-sm leading-6 text-[color:var(--text-muted)]">
                  No chunks match the current filter.
                </div>
              ) : null}
            </div>
            <div className="mt-5 flex items-center justify-between gap-3">
              <Button disabled={offset === 0} variant="outline" onClick={() => setOffset((current) => Math.max(0, current - 50))}>
                Previous
              </Button>
              <Button disabled={(chunksQuery.data?.chunks.length ?? 0) < 50} variant="outline" onClick={() => setOffset((current) => current + 50)}>
                Next
              </Button>
            </div>
          </section>
        </section>
      </main>
    </div>
  );
}
