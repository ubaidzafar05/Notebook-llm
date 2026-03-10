import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Edit3, Loader2, Plus, Trash2 } from "lucide-react";
import { useAppTheme } from "@/hooks/use-app-theme";
import { useAuthMutations, useNotebookMutations, useNotebooksQuery } from "@/hooks/use-workspace-queries";
import { ApiError, type ThemeMode } from "@/lib/api";
import { TopChrome } from "@/components/layout/TopChrome";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/store/use-auth-store";
import { useWorkspaceStore } from "@/store/use-workspace-store";

export function NotebooksPage(): JSX.Element {
  useAppTheme();
  const navigate = useNavigate();
  const themeMode = useWorkspaceStore((state) => state.studioState.themeMode);
  const setThemeMode = useWorkspaceStore((state) => state.setThemeMode);
  const clearSession = useAuthStore((state) => state.clearSession);
  const notebooksQuery = useNotebooksQuery();
  const notebookMutations = useNotebookMutations();
  const { logout: logoutMutation } = useAuthMutations();
  const [searchValue, setSearchValue] = useState("");
  const [createTitle, setCreateTitle] = useState("");
  const [createDescription, setCreateDescription] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  const notebooks = notebooksQuery.data ?? [];
  const filteredNotebooks = useMemo(() => {
    const term = searchValue.trim().toLowerCase();
    if (!term) {
      return notebooks;
    }
    return notebooks.filter((notebook) => notebook.title.toLowerCase().includes(term) || (notebook.description ?? "").toLowerCase().includes(term));
  }, [notebooks, searchValue]);

  async function handleLogout(): Promise<void> {
    try {
      await logoutMutation.mutateAsync();
    } finally {
      clearSession();
      navigate("/auth/login", { replace: true });
    }
  }

  async function handleCreateNotebook(): Promise<void> {
    const title = createTitle.trim();
    if (!title) {
      setError("Notebook title is required.");
      return;
    }
    setError(null);
    try {
      const notebook = await notebookMutations.createNotebook.mutateAsync({ title, description: createDescription.trim() || undefined });
      setCreateTitle("");
      setCreateDescription("");
      navigate(`/notebooks/${notebook.id}`);
    } catch (cause) {
      setError(resolveErrorMessage(cause));
    }
  }

  async function handleSaveEdit(notebookId: string): Promise<void> {
    setError(null);
    try {
      await notebookMutations.updateNotebook.mutateAsync({ notebookId, title: editTitle.trim(), description: editDescription.trim() || undefined });
      setEditingId(null);
      setEditTitle("");
      setEditDescription("");
    } catch (cause) {
      setError(resolveErrorMessage(cause));
    }
  }

  async function handleDeleteNotebook(notebookId: string): Promise<void> {
    setError(null);
    const confirmed = window.confirm("Delete this notebook and all of its sources, chats, and podcast jobs?");
    if (!confirmed) {
      return;
    }
    try {
      await notebookMutations.deleteNotebook.mutateAsync(notebookId);
    } catch (cause) {
      setError(resolveErrorMessage(cause));
    }
  }

  return (
    <div className="min-h-screen">
      <TopChrome
        notebookTitle="All notebooks"
        onCreateNotebook={() => void handleCreateNotebook()}
        onLogout={() => void handleLogout()}
        onSearchChange={setSearchValue}
        onThemeChange={(mode: ThemeMode) => setThemeMode(mode)}
        searchPlaceholder="Search notebooks"
        searchValue={searchValue}
        statusLabel={`${notebooks.length} notebooks`}
        themeMode={themeMode}
      />
      <main className="mx-auto max-w-[1760px] px-4 py-6 sm:px-6">
        <section className="grid gap-6 lg:grid-cols-[380px_minmax(0,1fr)]">
          <aside className="rounded-[2rem] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-5 shadow-panel">
            <p className="text-xs uppercase tracking-[0.28em] text-[color:var(--text-kicker)]">Create notebook</p>
            <h2 className="mt-3 font-serif text-3xl text-[color:var(--text-hero)]">Start a new workspace</h2>
            <div className="mt-5 space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-[color:var(--text-primary)]" htmlFor="create-title">Title</label>
                <Input id="create-title" value={createTitle} onChange={(event) => setCreateTitle(event.target.value)} />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-[color:var(--text-primary)]" htmlFor="create-description">Description</label>
                <Input id="create-description" value={createDescription} onChange={(event) => setCreateDescription(event.target.value)} />
              </div>
              <Button className="w-full" disabled={notebookMutations.createNotebook.isPending} onClick={() => void handleCreateNotebook()}>
                {notebookMutations.createNotebook.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                Create notebook
              </Button>
              {error ? <p className="rounded-xl border border-[color:hsl(var(--destructive)/0.3)] bg-[color:hsl(var(--destructive)/0.1)] px-3 py-2 text-sm text-[color:hsl(var(--destructive))]">{error}</p> : null}
            </div>
          </aside>

          <section className="rounded-[2rem] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-5 shadow-panel">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.28em] text-[color:var(--text-kicker)]">Library</p>
                <h2 className="mt-2 font-serif text-3xl text-[color:var(--text-hero)]">Your notebooks</h2>
              </div>
              {notebooksQuery.isLoading ? <Loader2 className="h-5 w-5 animate-spin text-[color:var(--accent-soft)]" /> : null}
            </div>
            <div className="mt-5 grid gap-4 xl:grid-cols-2">
              {filteredNotebooks.map((notebook) => {
                const isEditing = editingId === notebook.id;
                return (
                  <article key={notebook.id} className="rounded-[1.7rem] border border-[color:var(--panel-border)] bg-[color:var(--response-bg)] p-5 shadow-soft-card">
                    {isEditing ? (
                      <div className="space-y-3">
                        <Input value={editTitle} onChange={(event) => setEditTitle(event.target.value)} />
                        <Input value={editDescription} onChange={(event) => setEditDescription(event.target.value)} />
                        <div className="flex gap-2">
                          <Button onClick={() => void handleSaveEdit(notebook.id)}>Save</Button>
                          <Button variant="outline" onClick={() => setEditingId(null)}>Cancel</Button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="text-xs uppercase tracking-[0.24em] text-[color:var(--text-kicker)]">{notebook.isDefault ? "Default notebook" : "Notebook"}</p>
                            <h3 className="mt-2 text-xl font-semibold text-[color:var(--text-primary)]">{notebook.title}</h3>
                          </div>
                          <div className="flex gap-2">
                            <Button
                              aria-label={`Rename ${notebook.title}`}
                              size="sm"
                              variant="ghost"
                              onClick={() => {
                                setEditingId(notebook.id);
                                setEditTitle(notebook.title);
                                setEditDescription(notebook.description ?? "");
                              }}
                            >
                              <Edit3 className="h-4 w-4" />
                            </Button>
                            <Button
                              aria-label={`Delete ${notebook.title}`}
                              disabled={notebook.isDefault}
                              size="sm"
                              variant="ghost"
                              onClick={() => void handleDeleteNotebook(notebook.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        <p className="mt-3 min-h-[3rem] text-sm leading-6 text-[color:var(--text-muted)]">{notebook.description || "No description yet."}</p>
                        <div className="mt-5 flex items-center justify-between gap-3">
                          <span className="text-xs text-[color:var(--text-kicker)]">Updated {new Date(notebook.updatedAt).toLocaleDateString()}</span>
                          <Button asChild>
                            <Link to={`/notebooks/${notebook.id}`}>Open notebook</Link>
                          </Button>
                        </div>
                      </>
                    )}
                  </article>
                );
              })}
            </div>
            {!notebooksQuery.isLoading && filteredNotebooks.length === 0 ? (
              <div className="mt-6 rounded-[1.6rem] border border-dashed border-[color:var(--panel-border)] bg-[color:var(--surface-3)] p-6 text-sm leading-6 text-[color:var(--text-muted)]">
                No notebooks match your current search.
              </div>
            ) : null}
          </section>
        </section>
      </main>
    </div>
  );
}

function resolveErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Request failed.";
}
