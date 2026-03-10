import { Link2 } from "lucide-react";
import { motion } from "framer-motion";
import type { ChatMessageRecord, Citation, KnowledgeNode, SourceDocument } from "@/lib/api";
import { springs } from "@/animations/motion";
import { AIResponsePanel } from "@/components/chat/AIResponsePanel";
import { AnswerMaterialization } from "@/components/chat/AnswerMaterialization";
import { PromptComposer } from "@/components/chat/PromptComposer";
import { cn, formatRelativeTime } from "@/lib/utils";

type AnswerBoardProps = {
    documents: SourceDocument[];
    nodes: KnowledgeNode[];
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
    onDraftChange: (value: string) => void;
    onSubmit: () => Promise<void>;
    onNodeSelect: (node: KnowledgeNode) => void;
    onNodeHover: (nodeId: string | null) => void;
    onCitationHover: (sourceId: string | null) => void;
    onCitationOpen: (citation: Citation) => void;
    onToggleSection: (section: "response" | "citations" | "notes", expanded: boolean) => void;
};

export function AnswerBoard({
    documents,
    nodes,
    activeMessage,
    timeline,
    draftPrompt,
    attachedCount,
    selectedDocumentIds,
    activeDocumentId,
    isSending,
    answerSections,
    highlightedSourceId,
    onDraftChange,
    onSubmit,
    onNodeSelect,
    onNodeHover,
    onCitationHover,
    onCitationOpen,
    onToggleSection,
}: AnswerBoardProps): JSX.Element {
    const linkedSources = resolveLinkedSources(documents, selectedDocumentIds, activeDocumentId);
    const highlightedIds = new Set<string>([highlightedSourceId ?? ""]);

    return (
        <div className="space-y-5">
            {/* Dominant answer card */}
            <AIResponsePanel
                citationsExpanded={answerSections.citations}
                message={activeMessage}
                onCitationHover={onCitationHover}
                onCitationOpen={onCitationOpen}
                onToggleCitations={() => onToggleSection("citations", !answerSections.citations)}
                onToggleResponse={() => onToggleSection("response", !answerSections.response)}
                responseExpanded={answerSections.response}
            />

            {/* Linked sources ribbon */}
            {linkedSources.length > 0 ? (
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
            ) : null}

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
                            className="inline-flex items-center gap-1 rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] px-2.5 py-1 text-xs text-[color:var(--text-muted)]"
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
                    className="inline-flex w-fit items-center gap-1 rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] px-3 py-1.5 text-xs text-[color:var(--text-muted)]"
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
