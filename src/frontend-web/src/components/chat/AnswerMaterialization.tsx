import { BookMarked } from "lucide-react";
import { motion } from "framer-motion";
import type { ChatMessageRecord } from "@/lib/api";
import { formatRelativeTime } from "@/lib/utils";

type AnswerMaterializationProps = {
  messages: ChatMessageRecord[];
};

export function AnswerMaterialization({ messages }: AnswerMaterializationProps): JSX.Element {
  if (!messages.length) {
    return (
      <div className="rounded-2xl border border-dashed border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4 text-sm leading-6 text-[color:var(--text-muted)]">
        Insights you keep will appear here for quick reference.
      </div>
    );
  }

  return (
    <div className="pointer-events-auto flex gap-3 overflow-x-auto pb-1">
      {messages.map((message) => (
        <motion.article
          key={message.id}
          className="min-w-[230px] max-w-[280px] rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-3.5 text-left"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="flex items-center gap-1.5 text-[color:var(--text-primary)]">
            <BookMarked className="h-4 w-4 text-[color:var(--accent-soft)]" />
            <span className="text-[11px] uppercase tracking-[0.22em] text-[color:var(--text-kicker)]">Pinned note</span>
          </div>
          <p className="mt-2.5 line-clamp-3 text-sm leading-6 text-[color:var(--text-primary)]">{message.content}</p>
          <p className="mt-2 text-xs text-[color:var(--text-kicker)]">{formatRelativeTime(message.timestamp)}</p>
        </motion.article>
      ))}
    </div>
  );
}
