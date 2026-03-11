import React from "react";
import { Download, Link2, Network } from "lucide-react";
import { motion } from "framer-motion";
import type { ChatMessageRecord, Citation, KnowledgeEdge, KnowledgeNode, SourceDocument } from "@/lib/api";
import { springs } from "@/animations/motion";
import { AIResponsePanel } from "@/components/chat/AIResponsePanel";
import { AnswerMaterialization } from "@/components/chat/AnswerMaterialization";
import { PromptComposer } from "@/components/chat/PromptComposer";
import { KnowledgeGraphView } from "@/components/graph/KnowledgeGraphView";
import { cn, formatRelativeTime } from "@/lib/utils";

type AnswerBoardProps = {
    documents: SourceDocument[];
    nodes: KnowledgeNode[];
    edges: KnowledgeEdge[];
    activeMessage: ChatMessageRecord | null;
    timeline: ChatMessageRecord[];
    draftPrompt: string;
    attachedCount: number;
    selectedDocumentIds: string[];
    activeDocumentId: string | null;
    isSending: boolean;
    answerSections: {
        response: boolean;
        citations: boolean;
        notes: boolean;
    };
    highlightedSourceId: string | null;
    viewMode: "board" | "graph";
    onDraftChange: (value: string) => void;
    onSubmit: () => Promise<void>;
    onNodeSelect: (node: KnowledgeNode) => void;
    onNodeHover: (nodeId: string | null) => void;
    onCitationHover: (sourceId: string | null) => void;
    onCitationOpen: (citation: Citation) => void;
    onToggleSection: (section: "response" | "citations" | "notes", expanded: boolean) => void;
    onViewChange: (mode: "board" | "graph") => void;
    onExport: (format: "md" | "pdf") => void;
};

export function AnswerBoard({
    documents,
    nodes,
    edges,
    activeMessage,
    timeline,
    draftPrompt,
    attachedCount,
    selectedDocumentIds,
    activeDocumentId,
    isSending,
    answerSections,
    highlightedSourceId,
    viewMode,
    onDraftChange,
    onSubmit,
    onNodeSelect,
    onNodeHover,
    onCitationHover,
    onCitationOpen,
    onToggleSection,
    onViewChange,
    onExport,
}: AnswerBoardProps): JSX.Element {
    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-2">
                    <button
                        className={cn(
                            "rounded-full border px-3 py-1 text-xs",
                            viewMode === "board"
                                ? "border-[color:var(--panel-border-strong)] bg-[color:var(--surface-3)] text-[color:var(--text-primary)]"
                                : "border-[color:var(--panel-border)] bg-[color:var(--surface-2)] text-[color:var(--text-muted)]"
                        )}
                        type="button"
                        onClick={() => onViewChange("board")}
                    >
                        Answer
                    </button>
                    <button
                        className={cn(
                            "inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs",
                            viewMode === "graph"
                                ? "border-[color:var(--panel-border-strong)] bg-[color:var(--surface-3)] text-[color:var(--text-primary)]"
                                : "border-[color:var(--panel-border)] bg-[color:var(--surface-2)] text-[color:var(--text-muted)]"
                        )}
                        type="button"
                        onClick={() => onViewChange("graph")}
                    >
                        <Network className="h-3.5 w-3.5" />
                        Graph
                    </button>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        className="inline-flex items-center gap-1 rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] px-3 py-1 text-xs text-[color:var(--text-muted)]"
                        type="button"
                        onClick={() => onExport("md")}
                    >
                        <Download className="h-3.5 w-3.5" />
                        Download report (MD)
                    </button>
                    <button
                        className="inline-flex items-center gap-1 rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] px-3 py-1 text-xs text-[color:var(--text-muted)]"
                        type="button"
                        onClick={() => onExport("pdf")}
                    >
                        <Download className="h-3.5 w-3.5" />
                        Download report (PDF)
                    </button>
                </div>
            </div>

            {viewMode === "graph" ? (
                <KnowledgeGraphView
                    edges={edges}
                    highlightedSourceId={highlightedSourceId}
                    nodes={nodes}
                    onNodeHover={onNodeHover}
                    onNodeSelect={onNodeSelect}
                />
            ) : null}
            {/* Dominant answer card */}
            {viewMode === "board" ? (
                <AIResponsePanel
                citationsExpanded={answerSections.citations}
                message={activeMessage}
                onCitationHover={onCitationHover}
                onCitationOpen={onCitationOpen}
                onToggleCitations={() => onToggleSection("citations", !answerSections.citations)}
                onToggleResponse={() => onToggleSection("response", !answerSections.response)}
                responseExpanded={answerSections.response}
                />
            ) : null}

            {/* Linked sources ribbon */}
            <LinkedSourcesRibbon
                activeDocumentId={activeDocumentId}
                documents={documents}
                nodes={nodes}
                selectedDocumentIds={selectedDocumentIds}
                onNodeHover={onNodeHover}
                onNodeSelect={onNodeSelect}
                highlightedSourceId={highlightedSourceId}
            />

            {/* Prompt composer — docked */}
            <PromptComposer
                attachedCount={attachedCount}
                draftPrompt={draftPrompt}
                isSending={isSending}
                onChange={onDraftChange}
                onSubmit={onSubmit}
            />

            {/* Pinned insights rail */}
            {answerSections.notes ? (
                <section className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-5">
                    <div className="mb-3 flex items-center justify-between gap-2">
                        <div>
                            <p className="text-[11px] uppercase tracking-[0.24em] text-[color:var(--text-kicker)]">
                                Pinned insights
                            </p>
                            <p className="mt-1 text-sm text-[color:var(--text-muted)]">
                                Recent answers worth keeping visible.
                            </p>
                        </div>
                        <button
                            className="inline-flex items-center gap-1 rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] px-2.5 py-1 text-xs text-[color:var(--text-muted)] transition-opacity hover:opacity-80"
                            type="button"
                            onClick={() => onToggleSection("notes", false)}
                        >
                            <Link2 className="h-3.5 w-3.5" />
                            Hide
                        </button>
                    </div>
                    <AnswerMaterialization messages={timeline} />
                </section>
            ) : (
                <button
                    className="inline-flex w-fit items-center gap-1 rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] px-3 py-1.5 text-xs text-[color:var(--text-muted)] transition-all hover:bg-[color:var(--surface-3)]"
                    type="button"
                    onClick={() => onToggleSection("notes", true)}
                >
                    <Link2 className="h-3.5 w-3.5" />
                    Show pinned insights
                </button>
            )}
        </div>
    );
}

const LinkedSourcesRibbon = React.memo(function LinkedSourcesRibbon({
    documents,
    selectedDocumentIds,
    activeDocumentId,
    nodes,
    onNodeHover,
    onNodeSelect,
    highlightedSourceId
}: {
    documents: SourceDocument[];
    selectedDocumentIds: string[];
    activeDocumentId: string | null;
    nodes: KnowledgeNode[];
    onNodeHover: (nodeId: string | null) => void;
    onNodeSelect: (node: KnowledgeNode) => void;
    highlightedSourceId: string | null;
}) {
    const linkedSources = React.useMemo(() => resolveLinkedSources(documents, selectedDocumentIds, activeDocumentId), [documents, selectedDocumentIds, activeDocumentId]);
    const highlightedIds = new Set<string>([highlightedSourceId ?? ""]);

    if (linkedSources.length === 0) return null;

    return (
        <section className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4">
            <p className="mb-3 text-[11px] uppercase tracking-[0.24em] text-[color:var(--text-kicker)]">
                Linked sources
            </p>
            <div className="flex flex-wrap gap-2">
                {linkedSources.map((source) => (
                    <motion.button
                        key={source.id}
                        className={cn(
                            "flex items-center gap-2 rounded-xl border px-3.5 py-2.5 text-left transition",
                            highlightedIds.has(source.id)
                                ? "border-[color:var(--panel-border-strong)] bg-[color:var(--surface-3)]"
                                : "border-[color:var(--panel-border)] bg-[color:var(--surface-2)] hover:border-[color:var(--panel-border-strong)]"
                        )}
                        transition={springs.cardHover}
                        type="button"
                        onMouseEnter={() => onNodeHover(`node-${source.id}`)}
                        onMouseLeave={() => onNodeHover(null)}
                        onClick={() => selectSourceNode(source.id, nodes, onNodeSelect)}
                        whileHover={{ y: -1 }}
                    >
                        <div className="min-w-0">
                            <p className="line-clamp-1 text-sm font-semibold text-[color:var(--text-primary)]">
                                {source.title}
                            </p>
                            <p className="mt-0.5 text-xs text-[color:var(--text-muted)]">
                                {source.chunks} chunks · {formatRelativeTime(source.updatedAt)}
                            </p>
                        </div>
                    </motion.button>
                ))}
            </div>
        </section>
    );
});

function resolveLinkedSources(
    documents: SourceDocument[],
    selectedDocumentIds: string[],
    activeDocumentId: string | null
): SourceDocument[] {
    const preferredIds = activeDocumentId
        ? [activeDocumentId, ...selectedDocumentIds.filter((id) => id !== activeDocumentId)]
        : selectedDocumentIds;
    const selected = preferredIds
        .map((sourceId) => documents.find((document) => document.id === sourceId))
        .filter((doc): doc is SourceDocument => Boolean(doc));
    if (selected.length) {
        return selected.slice(0, 6);
    }
    return documents.slice(0, 3);
}

function selectSourceNode(
    sourceId: string,
    nodes: KnowledgeNode[],
    onNodeSelect: (node: KnowledgeNode) => void
): void {
    const node = nodes.find((candidate) => candidate.sourceId === sourceId);
    if (node) {
        onNodeSelect(node);
    }
}
