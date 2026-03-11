import { BookOpenText, LogOut, MessageSquarePlus, MoonStar, PanelRight, Plus, Search, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import { springs } from "@/animations/motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { ThemeMode } from "@/lib/api";
import { cn } from "@/lib/utils";

type NotebookOption = {
  id: string;
  title: string;
};

type TopChromeProps = {
  searchValue: string;
  onSearchChange: (value: string) => void;
  themeMode: ThemeMode;
  onThemeChange: (themeMode: ThemeMode) => void;
  searchPlaceholder?: string;
  notebookTitle?: string;
  statusLabel?: string;
  notebookOptions?: NotebookOption[];
  activeNotebookId?: string;
  onNotebookSelect?: (notebookId: string) => void;
  onCreateNotebook?: () => void;
  onNewChat?: () => void;
  onLogout?: () => void;
  studioOpen?: boolean;
  onToggleStudio?: () => void;
};

const themeOptions: Array<{ value: ThemeMode; label: string }> = [
  { value: "dusk-indigo", label: "Dusk" },
  { value: "linen-light", label: "Linen" },
  { value: "notebook-dark", label: "Ink" },
];

export function TopChrome({
  searchValue,
  onSearchChange,
  themeMode,
  onThemeChange,
  searchPlaceholder = "Search notes, sources, and ideas",
  notebookTitle = "NotebookLM Studio",
  statusLabel = "Ready",
  notebookOptions = [],
  activeNotebookId,
  onNotebookSelect,
  onCreateNotebook,
  onNewChat,
  onLogout,
  studioOpen = false,
  onToggleStudio,
}: TopChromeProps): JSX.Element {
  return (
    <motion.header
      className="sticky top-0 z-50 border-b border-[color:var(--shell-border)] bg-[color:var(--chrome-bg)] backdrop-blur-xl"
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0, transition: springs.panelMaterialize }}
    >
      <div className="mx-auto flex max-w-[1760px] items-center gap-3 px-4 py-2.5 sm:px-6 sm:py-3">
        {/* Brand */}
        <div className="flex shrink-0 items-center gap-2.5">
          <div className="rounded-xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-2 text-[color:var(--panel-icon)]">
            <BookOpenText className="h-4.5 w-4.5" />
          </div>
          <div className="hidden min-w-0 sm:block">
            <p className="truncate text-[10px] uppercase tracking-[0.3em] text-[color:var(--text-kicker)]">
              Notebook
            </p>
            <h1 className="truncate text-sm font-semibold text-[color:var(--text-hero)] sm:text-base">
              {notebookTitle}
            </h1>
          </div>
        </div>

        {/* Notebook select */}
        {notebookOptions.length > 0 && onNotebookSelect ? (
          <div className="hidden min-w-[180px] max-w-[240px] flex-1 md:block">
            <Select value={activeNotebookId} onValueChange={onNotebookSelect}>
              <SelectTrigger className="h-9 border-[color:var(--panel-border)] bg-[color:var(--surface-2)] text-[color:var(--text-primary)]">
                <SelectValue placeholder="Select notebook" />
              </SelectTrigger>
              <SelectContent>
                {notebookOptions.map((option) => (
                  <SelectItem key={option.id} value={option.id}>
                    {option.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        ) : null}

        {/* Search */}
        <div className="min-w-[200px] flex-1 lg:max-w-[36rem]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[color:var(--text-kicker)]" />
            <Input
              aria-label="Search the notebook workspace"
              id="workspace-global-search"
              className="h-9 pl-8 text-sm"
              placeholder={searchPlaceholder}
              value={searchValue}
              onChange={(event) => onSearchChange(event.target.value)}
            />
          </div>
        </div>

        {/* Status chip */}
        <div className="hidden items-center gap-1.5 rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] px-2.5 py-1 text-[11px] text-[color:var(--text-muted)] lg:flex">
          <Sparkles className="h-3 w-3 text-[color:var(--accent-soft)]" />
          {statusLabel}
        </div>

        {/* Actions */}
        <div className="ml-auto flex items-center gap-1.5">
          {onCreateNotebook ? (
            <Button className="hidden xl:inline-flex" size="sm" variant="outline" onClick={onCreateNotebook}>
              <Plus className="h-3.5 w-3.5" />
              Notebook
            </Button>
          ) : null}
          {onNewChat ? (
            <Button className="hidden xl:inline-flex" size="sm" variant="outline" onClick={onNewChat}>
              <MessageSquarePlus className="h-3.5 w-3.5" />
              Chat
            </Button>
          ) : null}

          {onToggleStudio ? (
            <Button
              aria-pressed={studioOpen}
              className={cn(
                studioOpen &&
                "border-[color:var(--theme-pill-active-border)] bg-[color:var(--theme-pill-active-bg)] text-[color:var(--theme-pill-active-text)]"
              )}
              size="sm"
              variant="outline"
              onClick={onToggleStudio}
            >
              <PanelRight className="h-3.5 w-3.5" />
              Studio
            </Button>
          ) : null}

          {/* Theme pills */}
          <div className="hidden items-center gap-1 xl:flex">
            {themeOptions.map((option) => (
              <button
                key={option.value}
                aria-pressed={themeMode === option.value}
                className={cn(
                  "rounded-full border px-2.5 py-1 text-[11px] font-medium transition",
                  themeMode === option.value
                    ? "border-[color:var(--theme-pill-active-border)] bg-[color:var(--theme-pill-active-bg)] text-[color:var(--theme-pill-active-text)]"
                    : "border-[color:var(--panel-border)] bg-[color:var(--surface-2)] text-[color:var(--text-muted)] hover:text-[color:var(--text-primary)]"
                )}
                onClick={() => onThemeChange(option.value)}
                type="button"
              >
                {option.label}
              </button>
            ))}
          </div>

          {/* Mobile theme toggle */}
          <Button
            className="xl:hidden"
            size="sm"
            variant="outline"
            onClick={() =>
              onThemeChange(
                themeOptions[(themeOptions.findIndex((item) => item.value === themeMode) + 1) % themeOptions.length]!
                  .value
              )
            }
          >
            <MoonStar className="h-3.5 w-3.5" />
            {themeOptions.find((option) => option.value === themeMode)?.label ?? "Theme"}
          </Button>

          {onLogout ? (
            <Button size="sm" variant="outline" onClick={onLogout}>
              <LogOut className="h-3.5 w-3.5" />
              Logout
            </Button>
          ) : null}
        </div>
      </div>
    </motion.header>
  );
}
