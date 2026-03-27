import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Edit3, Loader2, Pin, PinOff, Plus, Sparkles, Trash2, Wand2 } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { useAppTheme } from "@/hooks/use-app-theme";
import { useAuthMutations, useNotebookMutations, useNotebooksQuery } from "@/hooks/use-workspace-queries";
import { ApiError, type ThemeMode } from "@/lib/api";
import { TopChrome } from "@/components/layout/TopChrome";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/store/use-auth-store";
import { useWorkspaceStore } from "@/store/use-workspace-store";
import { springs } from "@/animations/motion";
import { cn } from "@/lib/utils";

export function NotebooksPage(): JSX.Element {
  useAppTheme();
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion() ?? false;
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

  const unpinnedNotebooks = useMemo(() => filteredNotebooks.filter((notebook) => !notebook.isPinned), [filteredNotebooks]);

  const featuredNotebookIds = useMemo(() => {
    return [...unpinnedNotebooks]
      .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
      .slice(0, 2)
      .map((notebook) => notebook.id);
  }, [unpinnedNotebooks]);

  const pinnedNotebooks = useMemo(() => {
    return filteredNotebooks
      .filter((notebook) => notebook.isPinned)
      .sort((a, b) => {
        const aTime = a.pinnedAt ? new Date(a.pinnedAt).getTime() : 0;
        const bTime = b.pinnedAt ? new Date(b.pinnedAt).getTime() : 0;
        return bTime - aTime;
      });
  }, [filteredNotebooks]);
  const lastOpenedNotebooks = useMemo(() => {
    return [...unpinnedNotebooks]
      .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
      .slice(0, 4);
  }, [unpinnedNotebooks]);

  const emptyState = !notebooksQuery.isLoading && filteredNotebooks.length === 0;

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

  async function handleTogglePin(notebookId: string, nextPinned: boolean): Promise<void> {
    setError(null);
    try {
      await notebookMutations.updateNotebook.mutateAsync({ notebookId, title: undefined, description: undefined, isPinned: nextPinned });
    } catch (cause) {
      setError(resolveErrorMessage(cause));
    }
  }

  return (
    <div className="min-h-screen bg-[color:var(--shell-bg)]">
      <TopChrome
        notebookTitle="All notebooks"
        onLogout={() => void handleLogout()}
        onSearchChange={setSearchValue}
        onThemeChange={(mode: ThemeMode) => setThemeMode(mode)}
        searchPlaceholder="Search notebooks"
        searchValue={searchValue}
        statusLabel={`${notebooks.length} notebooks`}
        themeMode={themeMode}
      />
      <main className="relative mx-auto max-w-[1760px] px-4 pb-16 pt-6 sm:px-6">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-[420px] rounded-[40px] bg-[radial-gradient(circle_at_top,rgba(210,196,255,0.55),rgba(255,255,255,0))]" />
        <motion.section
          className="relative overflow-hidden rounded-[32px] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] px-6 py-6 shadow-panel sm:px-8"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0, transition: springs.panelMaterialize }}
        >
          <div className="absolute -right-24 top-6 h-40 w-40 rounded-full bg-[radial-gradient(circle,rgba(140,126,230,0.35),rgba(140,126,230,0))] blur-2xl" />
          <div className="absolute left-8 top-8 h-24 w-24 rounded-full bg-[radial-gradient(circle,rgba(255,203,193,0.35),rgba(255,203,193,0))] blur-2xl" />
          <div className="relative flex flex-wrap items-center justify-between gap-6">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-[color:var(--text-kicker)]">Living library</p>
              <h2 className="mt-2 font-serif text-4xl text-[color:var(--text-hero)]">Your notebooks, beautifully in motion.</h2>
              <p className="mt-2 max-w-[520px] text-sm leading-6 text-[color:var(--text-muted)]">
                Build living research spaces, track breakthroughs, and keep the entire thought trail visible.
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-3 text-xs text-[color:var(--text-kicker)]">
                <span className="rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] px-3 py-1">{notebooks.length} notebooks</span>
                <span className="rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] px-3 py-1">
                  {filteredNotebooks.length} visible
                </span>
                <span className="rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] px-3 py-1">
                  Updated {filteredNotebooks[0] ? new Date(filteredNotebooks[0].updatedAt).toLocaleDateString() : "today"}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" onClick={() => setSearchValue("")}>Clear search</Button>
            </div>
          </div>
        </motion.section>

        <section className="relative mt-8 grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="space-y-6">
            {pinnedNotebooks.length > 0 ? (
              <motion.div
                className="rounded-[28px] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-5 shadow-panel"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0, transition: springs.panelMaterialize }}
              >
                <div className="flex items-center gap-2 text-xs uppercase tracking-[0.3em] text-[color:var(--text-kicker)]">
                  <Sparkles className="h-3.5 w-3.5 text-[color:var(--accent-soft)]" />
                  Pinned
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  {pinnedNotebooks.map((notebook) => (
                    <NotebookCard
                      key={notebook.id}
                      notebook={notebook}
                      featured
                      isEditing={editingId === notebook.id}
                      editTitle={editTitle}
                      editDescription={editDescription}
                      onEditStart={() => {
                        setEditingId(notebook.id);
                        setEditTitle(notebook.title);
                        setEditDescription(notebook.description ?? "");
                      }}
                      onEditChangeTitle={setEditTitle}
                      onEditChangeDescription={setEditDescription}
                      onEditSave={() => void handleSaveEdit(notebook.id)}
                      onEditCancel={() => setEditingId(null)}
                      onDelete={() => void handleDeleteNotebook(notebook.id)}
                      onTogglePin={() => void handleTogglePin(notebook.id, !notebook.isPinned)}
                      onOpen={() => navigate(`/notebooks/${notebook.id}`)}
                      reduceMotion={reduceMotion}
                    />
                  ))}
                </div>
              </motion.div>
            ) : null}

            <motion.section
              className="rounded-[28px] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-5 shadow-panel"
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0, transition: springs.panelMaterialize }}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.28em] text-[color:var(--text-kicker)]">Library</p>
                  <h2 className="mt-2 font-serif text-3xl text-[color:var(--text-hero)]">Your notebooks</h2>
                </div>
                <div className="flex items-center gap-2 text-xs text-[color:var(--text-kicker)]">
                  {notebooksQuery.isLoading ? <Loader2 className="h-4 w-4 animate-spin text-[color:var(--accent-soft)]" /> : null}
                  <span className="rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] px-3 py-1">
                    {filteredNotebooks.length} results
                  </span>
                </div>
              </div>

              {emptyState ? (
                <EmptyLibrary
                  reduceMotion={reduceMotion}
                />
              ) : (
                <motion.div
                  className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3"
                  initial="initial"
                  animate="animate"
                  variants={{
                    initial: { opacity: 0 },
                    animate: { opacity: 1, transition: { staggerChildren: 0.08 } },
                  }}
                >
                  {unpinnedNotebooks.map((notebook) => (
                    <NotebookCard
                      key={notebook.id}
                      notebook={notebook}
                      featured={featuredNotebookIds.includes(notebook.id)}
                      isEditing={editingId === notebook.id}
                      editTitle={editTitle}
                      editDescription={editDescription}
                      onEditStart={() => {
                        setEditingId(notebook.id);
                        setEditTitle(notebook.title);
                        setEditDescription(notebook.description ?? "");
                      }}
                      onEditChangeTitle={setEditTitle}
                      onEditChangeDescription={setEditDescription}
                      onEditSave={() => void handleSaveEdit(notebook.id)}
                      onEditCancel={() => setEditingId(null)}
                      onDelete={() => void handleDeleteNotebook(notebook.id)}
                      onTogglePin={() => void handleTogglePin(notebook.id, !notebook.isPinned)}
                      onOpen={() => navigate(`/notebooks/${notebook.id}`)}
                      reduceMotion={reduceMotion}
                      className={cn(featuredNotebookIds.includes(notebook.id) && "md:col-span-2")}
                    />
                  ))}
                </motion.div>
              )}
            </motion.section>
          </div>

          <aside className="relative space-y-6">
            <motion.div
              className="rounded-[28px] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-5 shadow-panel"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0, transition: springs.panelMaterialize }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.28em] text-[color:var(--text-kicker)]">Create</p>
                  <h3 className="mt-2 font-serif text-2xl text-[color:var(--text-hero)]">Start something magical</h3>
                </div>
                <div className="rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] p-2 text-[color:var(--accent-soft)]">
                  <Wand2 className="h-4 w-4" />
                </div>
              </div>
              <div className="mt-5 space-y-4">
                <div>
                  <label className="mb-2 block text-sm font-medium text-[color:var(--text-primary)]" htmlFor="create-title">Title</label>
                  <Input id="create-title" value={createTitle} onChange={(event) => setCreateTitle(event.target.value)} />
                </div>
                <div>
                  <label className="mb-2 block text-sm font-medium text-[color:var(--text-primary)]" htmlFor="create-description">Description</label>
                  <Input id="create-description" value={createDescription} onChange={(event) => setCreateDescription(event.target.value)} />
                </div>
                <div className={reduceMotion ? "" : "animate-[pulse_2.2s_ease-in-out_infinite]"}>
                  <Button className="w-full" disabled={notebookMutations.createNotebook.isPending} onClick={() => void handleCreateNotebook()}>
                    {notebookMutations.createNotebook.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                    Create notebook
                  </Button>
                </div>
                {error ? (
                  <p className="rounded-xl border border-[color:hsl(var(--destructive)/0.3)] bg-[color:hsl(var(--destructive)/0.1)] px-3 py-2 text-sm text-[color:hsl(var(--destructive))]">{error}</p>
                ) : null}
              </div>
            </motion.div>

            {lastOpenedNotebooks.length > 0 ? (
              <motion.div
                className="rounded-[28px] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-5 shadow-panel"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0, transition: springs.panelMaterialize }}
              >
                <p className="text-xs uppercase tracking-[0.28em] text-[color:var(--text-kicker)]">Recently visited</p>
                <div className="mt-4 space-y-3">
                  {lastOpenedNotebooks.map((notebook) => (
                    <button
                      key={notebook.id}
                      type="button"
                      onClick={() => navigate(`/notebooks/${notebook.id}`)}
                      className="flex w-full items-center justify-between rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] px-3 py-2 text-left text-sm text-[color:var(--text-primary)] transition hover:-translate-y-0.5 hover:shadow-soft-card"
                    >
                      <span className="truncate">{notebook.title}</span>
                      <span className="text-xs text-[color:var(--text-kicker)]">{new Date(notebook.updatedAt).toLocaleDateString()}</span>
                    </button>
                  ))}
                </div>
              </motion.div>
            ) : null}

            <motion.div
              className="rounded-[28px] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-5 shadow-panel"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0, transition: springs.panelMaterialize }}
            >
              <p className="text-xs uppercase tracking-[0.28em] text-[color:var(--text-kicker)]">Tips</p>
              <ul className="mt-4 space-y-2 text-sm text-[color:var(--text-muted)]">
                <li className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] px-3 py-2">Pin notebooks to keep them at the top.</li>
                <li className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] px-3 py-2">Use search to jump between research threads quickly.</li>
                <li className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] px-3 py-2">Rename notebooks to keep your library tidy.</li>
              </ul>
            </motion.div>
          </aside>
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

type NotebookCardProps = {
  notebook: { id: string; title: string; description: string | null; updatedAt: string; isDefault: boolean; isPinned: boolean };
  featured?: boolean;
  isEditing: boolean;
  editTitle: string;
  editDescription: string;
  onEditStart: () => void;
  onEditChangeTitle: (value: string) => void;
  onEditChangeDescription: (value: string) => void;
  onEditSave: () => void;
  onEditCancel: () => void;
  onDelete: () => void;
  onTogglePin: () => void;
  onOpen: () => void;
  reduceMotion: boolean;
  className?: string;
};

function NotebookCard({
  notebook,
  featured,
  isEditing,
  editTitle,
  editDescription,
  onEditStart,
  onEditChangeTitle,
  onEditChangeDescription,
  onEditSave,
  onEditCancel,
  onDelete,
  onTogglePin,
  onOpen,
  reduceMotion,
  className,
}: NotebookCardProps): JSX.Element {
  return (
    <motion.article
      className={cn(
        "group relative rounded-[1.7rem] border border-[color:var(--panel-border)] bg-[color:var(--response-bg)] p-5 shadow-soft-card transition",
        featured && "bg-[color:var(--surface-3)]",
        className
      )}
      variants={{
        initial: { opacity: 0, y: 12 },
        animate: { opacity: 1, y: 0, transition: springs.panelMaterialize },
      }}
      whileHover={reduceMotion ? undefined : { y: -4, boxShadow: "0 18px 36px rgba(82,66,155,0.18)" }}
    >
      {isEditing ? (
        <div className="space-y-3">
          <Input value={editTitle} onChange={(event) => onEditChangeTitle(event.target.value)} />
          <Input value={editDescription} onChange={(event) => onEditChangeDescription(event.target.value)} />
          <div className="flex gap-2">
            <Button onClick={onEditSave}>Save</Button>
            <Button variant="outline" onClick={onEditCancel}>Cancel</Button>
          </div>
        </div>
      ) : (
        <>
            <div className="flex items-start justify-between gap-3">
              <div>
              <p className="text-xs uppercase tracking-[0.24em] text-[color:var(--text-kicker)]">
                {notebook.isDefault ? "Default notebook" : notebook.isPinned ? "Pinned" : "Notebook"}
              </p>
              <h3 className="mt-2 text-xl font-semibold text-[color:var(--text-primary)]">{notebook.title}</h3>
            </div>
            <div className="flex gap-2 opacity-100 transition sm:opacity-0 sm:group-hover:opacity-100">
              <Button aria-label={`Pin ${notebook.title}`} size="sm" variant="ghost" onClick={onTogglePin}>
                {notebook.isPinned ? <PinOff className="h-4 w-4" /> : <Pin className="h-4 w-4" />}
              </Button>
              <Button aria-label={`Rename ${notebook.title}`} size="sm" variant="ghost" onClick={onEditStart}>
                <Edit3 className="h-4 w-4" />
              </Button>
              <Button aria-label={`Delete ${notebook.title}`} disabled={notebook.isDefault} size="sm" variant="ghost" onClick={onDelete}>
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <p className="mt-3 min-h-[3rem] text-sm leading-6 text-[color:var(--text-muted)]">
            {notebook.description || "No description yet."}
          </p>
          <div className="mt-5 flex items-center justify-between gap-3">
            <span className="text-xs text-[color:var(--text-kicker)]">Updated {new Date(notebook.updatedAt).toLocaleDateString()}</span>
            <Button onClick={onOpen}>Open notebook</Button>
          </div>
        </>
      )}
    </motion.article>
  );
}

function EmptyLibrary({ reduceMotion }: { reduceMotion: boolean }): JSX.Element {
  return (
    <div className="mt-6 rounded-[1.6rem] border border-dashed border-[color:var(--panel-border)] bg-[color:var(--surface-3)] p-6 text-sm leading-6 text-[color:var(--text-muted)]">
      <div className="relative overflow-hidden rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--response-bg)] p-6">
        <div className="absolute -right-10 top-8 h-32 w-32 rounded-full bg-[radial-gradient(circle,rgba(135,120,220,0.35),rgba(135,120,220,0))] blur-2xl" />
        <div className="absolute left-8 top-10 h-24 w-24 rounded-full bg-[radial-gradient(circle,rgba(255,190,180,0.35),rgba(255,190,180,0))] blur-2xl" />
        <div className="relative">
          <p className="text-xs uppercase tracking-[0.24em] text-[color:var(--text-kicker)]">Fresh canvas</p>
          <h3 className="mt-2 font-serif text-2xl text-[color:var(--text-hero)]">Your library is waiting for its first spark.</h3>
          <p className="mt-2 text-sm text-[color:var(--text-muted)]">
            Start with a notebook template or spin something new. We’ll keep it all connected and easy to revisit.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {[
              { title: "Research sprint", description: "Collect sources and map insights." },
              { title: "Product launch", description: "Track ideas, evidence, and next steps." },
              { title: "Creative dossier", description: "Draft, cite, and refine outputs." },
            ].map((template) => (
              <div key={template.title} className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4">
                <p className="text-sm font-semibold text-[color:var(--text-primary)]">{template.title}</p>
                <p className="mt-1 text-xs text-[color:var(--text-kicker)]">{template.description}</p>
              </div>
            ))}
          </div>
          <p className={cn("mt-5 text-xs uppercase tracking-[0.24em] text-[color:var(--text-kicker)]", reduceMotion ? "" : "animate-[pulse_2.2s_ease-in-out_infinite]")}>
            Use the create panel on the right to start your first notebook.
          </p>
        </div>
      </div>
    </div>
  );
}
