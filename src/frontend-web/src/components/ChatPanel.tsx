import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { createNotebookSession, listNotebookMessages, listNotebookSessions, listNotebookSources } from "../lib/api";
import { HttpError } from "../lib/http";
import { streamNotebookMessage } from "../lib/sse";
import { queryClient } from "../app/queryClient";
import { useAuthStore } from "../state/auth-store";
import { useWorkspaceStore } from "../state/workspace-store";
import type { Citation, StreamEvent } from "../types/api";
import styles from "./Workspace.module.css";

type ChatPanelProps = {
  notebookId: string;
};

export function ChatPanel({ notebookId }: ChatPanelProps): JSX.Element {
  const accessToken = useAuthStore((state) => state.accessToken);
  const selectedSessionId = useWorkspaceStore((state) => state.selectedSessionId);
  const setSelectedSessionId = useWorkspaceStore((state) => state.setSelectedSessionId);
  const selectedSourceIds = useWorkspaceStore((state) => state.selectedSourceIds);
  const setSelectedSourceIds = useWorkspaceStore((state) => state.setSelectedSourceIds);
  const focusSource = useWorkspaceStore((state) => state.focusSource);
  const [sessionTitle, setSessionTitle] = useState("Notebook Session");
  const [message, setMessage] = useState("");
  const [streamingText, setStreamingText] = useState("");
  const [finalCitations, setFinalCitations] = useState<Citation[]>([]);
  const [confidence, setConfidence] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);
  const sessionsQuery = useQuery({
    queryKey: ["chat-sessions", notebookId],
    queryFn: () => listNotebookSessions(notebookId),
  });
  const sourcesQuery = useQuery({
    queryKey: ["chat-sources", notebookId],
    queryFn: () => listNotebookSources(notebookId),
  });
  const messagesQuery = useQuery({
    queryKey: ["chat-messages", notebookId, selectedSessionId],
    queryFn: () => listNotebookMessages(notebookId, selectedSessionId!),
    enabled: Boolean(selectedSessionId),
  });
  const createSessionMutation = useMutation({
    mutationFn: () => createNotebookSession(notebookId, sessionTitle.trim() || "Notebook Session"),
    onSuccess: (session) => {
      setSelectedSessionId(session.id);
      void queryClient.invalidateQueries({ queryKey: ["chat-sessions", notebookId] });
    },
  });

  useEffect(() => {
    const firstSession = sessionsQuery.data?.[0]?.id ?? null;
    if (firstSession && !selectedSessionId) {
      setSelectedSessionId(firstSession);
    }
  }, [selectedSessionId, sessionsQuery.data, setSelectedSessionId]);

  async function handleSend(): Promise<void> {
    if (!selectedSessionId || !message.trim()) {
      return;
    }
    setSendError(null);
    setStreamingText("");
    setFinalCitations([]);
    setConfidence(null);
    try {
      await streamNotebookMessage(notebookId, selectedSessionId, {
        accessToken,
        message: message.trim(),
        sourceIds: selectedSourceIds,
        onEvent: (event) => applyStreamEvent(event, setStreamingText, setFinalCitations, setConfidence),
      });
      setMessage("");
      await queryClient.invalidateQueries({ queryKey: ["chat-messages", notebookId, selectedSessionId] });
    } catch (rawError) {
      setSendError(rawError instanceof HttpError ? rawError.message : "Message failed");
    }
  }

  const sources = sourcesQuery.data ?? [];
  const sourceOptions = useMemo(() => sources.map((source) => ({ id: source.id, label: source.name })), [sources]);

  return (
    <div className={styles.column}>
      <div className={styles.panelHeader}>
        <p className={styles.eyebrow}>Chat</p>
        <h2 className={styles.panelTitle}>Grounded Conversation</h2>
      </div>
      <div className={styles.panelBody}>
        <section className={styles.section}>
          <div className={styles.footerRow}>
            <input className={styles.input} value={sessionTitle} onChange={(event) => setSessionTitle(event.target.value)} />
            <button className={styles.button} disabled={createSessionMutation.isPending} onClick={() => createSessionMutation.mutate()} type="button">
              New Session
            </button>
          </div>
          <div className={styles.pillRow}>
            {sessionsQuery.data?.map((session) => (
              <button
                key={session.id}
                className={session.id === selectedSessionId ? styles.pillActive : styles.pill}
                onClick={() => setSelectedSessionId(session.id)}
                type="button"
              >
                {session.title}
              </button>
            ))}
          </div>
        </section>
        <section className={styles.section}>
          <div className={styles.pillRow}>
            {sourceOptions.map((source) => {
              const isSelected = selectedSourceIds.includes(source.id);
              return (
                <button
                  key={source.id}
                  className={isSelected ? styles.pillActive : styles.pill}
                  onClick={() => setSelectedSourceIds(toggleSelection(selectedSourceIds, source.id))}
                  type="button"
                >
                  {source.label}
                </button>
              );
            })}
          </div>
        </section>
        <section className={styles.messageList}>
          {messagesQuery.data?.map((messageRow) => (
            <div key={messageRow.id} className={messageRow.role === "user" ? styles.messageUser : styles.messageAssistant}>
              {messageRow.content}
              {!!messageRow.citations.length && (
                <CitationRow citations={messageRow.citations} onSelect={(citation) => focusSource(toSourceFocus(citation))} />
              )}
            </div>
          )) ?? <div className={styles.emptyState}>Create a session to start grounded chat.</div>}
          {streamingText ? <div className={styles.messageStreaming}>{streamingText}</div> : null}
          {finalCitations.length ? <CitationRow citations={finalCitations} onSelect={(citation) => focusSource(toSourceFocus(citation))} /> : null}
          {confidence ? <p className={styles.tinyMeta}>Confidence: {confidence}</p> : null}
        </section>
        <section className={styles.section}>
          <textarea className={styles.textarea} value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Ask a question grounded in this notebook." />
          <button className={styles.button} disabled={!selectedSessionId || !message.trim()} onClick={() => void handleSend()} type="button">
            Send Message
          </button>
          {sendError ? <p className={styles.error}>{sendError}</p> : null}
        </section>
      </div>
    </div>
  );
}

function CitationRow({ citations, onSelect }: { citations: Citation[]; onSelect: (citation: Citation) => void }): JSX.Element {
  return (
    <div className={styles.pillRow}>
      {citations.map((citation) => (
        <button key={`${citation.source_id}-${citation.chunk_id}`} className={styles.pill} onClick={() => onSelect(citation)} type="button">
          {citation.source_id.slice(0, 8)} · {formatCitationAnchor(citation)}
        </button>
      ))}
    </div>
  );
}

function applyStreamEvent(
  event: StreamEvent,
  setStreamingText: (value: string | ((current: string) => string)) => void,
  setFinalCitations: (value: Citation[]) => void,
  setConfidence: (value: string | null) => void,
): void {
  if (event.type === "token") {
    setStreamingText((current) => current + event.value);
    return;
  }
  setStreamingText(event.content);
  setFinalCitations(event.citations);
  setConfidence(event.confidence);
}

function toggleSelection(selectedSourceIds: string[], sourceId: string): string[] {
  return selectedSourceIds.includes(sourceId)
    ? selectedSourceIds.filter((item) => item !== sourceId)
    : [...selectedSourceIds, sourceId];
}

function formatCitationAnchor(citation: Citation): string {
  if (typeof citation.page_number === "number") {
    return `p.${citation.page_number}`;
  }
  if (typeof citation.start_timestamp === "number") {
    return `${citation.start_timestamp}s`;
  }
  if (typeof citation.section_heading === "string" && citation.section_heading) {
    return citation.section_heading;
  }
  return citation.chunk_id.slice(0, 8);
}

function toSourceFocus(citation: Citation) {
  return {
    sourceId: citation.source_id,
    chunkId: citation.chunk_id,
    pageNumber: citation.page_number ?? null,
    startTimestamp: citation.start_timestamp ?? null,
    endTimestamp: citation.end_timestamp ?? null,
  };
}
