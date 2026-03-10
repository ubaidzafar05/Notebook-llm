import { BookText, ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import { useMemo } from "react";
import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessageRecord, Citation } from "@/lib/api";
import { springs } from "@/animations/motion";
import { CitationGlowCard } from "@/components/chat/CitationGlowCard";
import { formatRelativeTime } from "@/lib/utils";
import { cn } from "@/lib/utils";

type AIResponsePanelProps = {
  message: ChatMessageRecord | null;
  onCitationHover: (sourceId: string | null) => void;
  onCitationOpen: (citation: Citation) => void;
  className?: string;
  responseExpanded?: boolean;
  citationsExpanded?: boolean;
  onToggleResponse?: () => void;
  onToggleCitations?: () => void;
};

export function AIResponsePanel({
  message,
  onCitationHover,
  onCitationOpen,
  className,
  responseExpanded = true,
  citationsExpanded = true,
  onToggleResponse,
  onToggleCitations,
}: AIResponsePanelProps): JSX.Element {
  const markdown = useMemo(
    () => message?.content ?? "Ask a question to generate a grounded answer from your selected sources.",
    [message]
  );

  return (
    <motion.section
      className={cn(
        "w-full rounded-3xl border border-[color:var(--panel-border)] bg-[color:var(--response-bg)] p-6 shadow-panel sm:p-7",
        className
      )}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0, transition: springs.answerAppear }}
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="rounded-xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-2.5 text-[color:var(--panel-icon)]">
          <BookText className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[11px] uppercase tracking-[0.24em] text-[color:var(--text-kicker)]">Notebook answer</p>
          <h3 className="mt-1 font-serif text-[clamp(1.25rem,1.6vw,1.75rem)] leading-tight text-[color:var(--text-hero)]">
            Grounded reading
          </h3>
          <p className="mt-1 text-xs text-[color:var(--text-kicker)]">
            {message ? formatRelativeTime(message.timestamp) : "Ready"}
          </p>
        </div>
      </div>

      {/* Answer body */}
      <div className="mt-5 rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-5">
        <button
          className="flex w-full items-center justify-between text-left"
          type="button"
          aria-label={responseExpanded ? "Collapse answer" : "Expand answer"}
          onClick={onToggleResponse}
        >
          <span className="text-sm font-semibold text-[color:var(--text-primary)]">Answer</span>
          {responseExpanded ? (
            <ChevronUp className="h-4 w-4 text-[color:var(--text-muted)]" />
          ) : (
            <ChevronDown className="h-4 w-4 text-[color:var(--text-muted)]" />
          )}
        </button>

        {responseExpanded ? (
          <div className="prose mt-5 max-w-none text-[15px] leading-7">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code(props) {
                  return (
                    <code
                      className="rounded-md bg-[color:var(--surface-3)] px-1.5 py-1 font-mono text-xs text-[color:var(--code-inline)]"
                      {...props}
                    />
                  );
                },
                pre(props) {
                  return (
                    <pre
                      className="overflow-x-auto rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--code-block-bg)] p-4"
                      {...props}
                    />
                  );
                },
              }}
            >
              {markdown}
            </ReactMarkdown>
            {message?.isStreaming ? (
              <div className="mt-4 inline-flex items-center gap-2 rounded-full bg-[color:var(--chip-accent-bg)] px-3 py-1.5 text-xs font-medium text-[color:var(--chip-accent-text)]">
                <Sparkles className="h-3.5 w-3.5" />
                Drafting from selected sources
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      {/* Citations */}
      {message?.citations?.length ? (
        <div className="mt-5 rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-5">
          <button
            className="flex w-full items-center justify-between text-left"
            type="button"
            aria-label={citationsExpanded ? "Collapse citations" : "Expand citations"}
            onClick={onToggleCitations}
          >
            <span className="text-sm font-semibold text-[color:var(--text-primary)]">
              Citations ({message.citations.length})
            </span>
            {citationsExpanded ? (
              <ChevronUp className="h-4 w-4 text-[color:var(--text-muted)]" />
            ) : (
              <ChevronDown className="h-4 w-4 text-[color:var(--text-muted)]" />
            )}
          </button>

          {citationsExpanded ? (
            <div className="mt-4 grid gap-3 lg:grid-cols-2">
              {message.citations.map((citation) => (
                <CitationGlowCard key={citation.id} citation={citation} onHover={onCitationHover} onOpen={onCitationOpen} />
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </motion.section>
  );
}
