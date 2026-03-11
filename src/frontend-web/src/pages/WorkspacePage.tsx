import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import type { ChatMessageRecord, Citation, JobRecord, PodcastGenerationPhase, SourceDocument, ThemeMode } from "@/lib/api";
import { ApiError, buildInsightSnapshot, buildKnowledgeResult, getJob } from "@/lib/api";
import { useAppTheme } from "@/hooks/use-app-theme";
import {
  useAuthMutations,
  useChatMutations,
  useChatSearchQuery,
  useExportMutation,
  useNotebookSourcesFilteredQuery,
  useNotebookSourcesSearchQuery,
  useNotebookUsageQuery,
  useNotebookPodcastsQuery,
  useNotebookQuery,
  useNotebookSessionsQuery,
  useNotebookSourcesQuery,
  useNotebooksQuery,
  usePodcastMutations,
  useSourceMutations,
  useNotebookMessagesQuery
} from "@/hooks/use-workspace-queries";
import { TopChrome } from "@/components/layout/TopChrome";
import { WorkspaceShell } from "@/components/layout/WorkspaceShell";
import { SourceNebula } from "@/components/sources/SourceNebula";
import { AnswerBoard } from "@/components/answer/AnswerBoard";
import { AIStudioPanel } from "@/components/studio/AIStudioPanel";
import {
  getAnswerTimeline,
  getLatestAssistantMessage,
  useWorkspaceStore,
  workspaceSelectors
} from "@/store/use-workspace-store";
import { useAuthStore } from "@/store/use-auth-store";

export function WorkspacePage(): JSX.Element {
  useAppTheme();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { notebookId = "" } = useParams();
  const themeMode = useWorkspaceStore((state) => state.studioState.themeMode);
  const setThemeMode = useWorkspaceStore((state) => state.setThemeMode);
  const selectedDocumentIds = useWorkspaceStore(workspaceSelectors.selectedDocumentIds);
  const activeDocumentId = useWorkspaceStore(workspaceSelectors.activeDocumentId);
  const hoveredDocumentId = useWorkspaceStore(workspaceSelectors.hoveredDocumentId);
  const nodes = useWorkspaceStore(workspaceSelectors.nodes);
  const edges = useWorkspaceStore(workspaceSelectors.edges);
  const messages = useWorkspaceStore(workspaceSelectors.messages);
  const draftPrompt = useWorkspaceStore(workspaceSelectors.draftPrompt);
  const attachedDocumentIds = useWorkspaceStore(workspaceSelectors.attachedDocumentIds);
  const chatSettings = useWorkspaceStore(workspaceSelectors.chatSettings);
  const studioState = useWorkspaceStore(workspaceSelectors.studioState);
  const sceneState = useWorkspaceStore(workspaceSelectors.sceneState);
  const uiShellState = useWorkspaceStore(workspaceSelectors.uiShellState);
  const answerBoardState = useWorkspaceStore(workspaceSelectors.answerBoardState);
  const sourceFilters = useWorkspaceStore(workspaceSelectors.sourceFilters);
  const setKnowledgeGraph = useWorkspaceStore((state) => state.setKnowledgeGraph);
  const setMessages = useWorkspaceStore((state) => state.setMessages);
  const addMessage = useWorkspaceStore((state) => state.addMessage);
  const updateMessage = useWorkspaceStore((state) => state.updateMessage);
  const setDraftPrompt = useWorkspaceStore((state) => state.setDraftPrompt);
  const toggleDocumentSelection = useWorkspaceStore((state) => state.toggleDocumentSelection);
  const clearSelectedDocuments = useWorkspaceStore((state) => state.clearSelectedDocuments);
  const setHoveredDocument = useWorkspaceStore((state) => state.setHoveredDocument);
  const setActiveDocument = useWorkspaceStore((state) => state.setActiveDocument);
  const setFocusedCitation = useWorkspaceStore((state) => state.setFocusedCitation);
  const setStreamingAnswerId = useWorkspaceStore((state) => state.setStreamingAnswerId);
  const setHoveredNode = useWorkspaceStore((state) => state.setHoveredNode);
  const setStudioOpen = useWorkspaceStore((state) => state.setStudioOpen);
  const toggleStudioOpen = useWorkspaceStore((state) => state.toggleStudioOpen);
  const toggleGalleryCollapsed = useWorkspaceStore((state) => state.toggleGalleryCollapsed);
  const setActiveStudioTab = useWorkspaceStore((state) => state.setActiveStudioTab);
  const setAnswerSectionExpanded = useWorkspaceStore((state) => state.setAnswerSectionExpanded);
  const setAnswerBoardHighlightedSource = useWorkspaceStore((state) => state.setAnswerBoardHighlightedSource);
  const setAnswerViewMode = useWorkspaceStore((state) => state.setAnswerViewMode);
  const setSourceFilters = useWorkspaceStore((state) => state.setSourceFilters);
  const updateChatSettings = useWorkspaceStore((state) => state.updateChatSettings);
  const setSelectedVoice = useWorkspaceStore((state) => state.setSelectedVoice);
  const clearSession = useAuthStore((state) => state.clearSession);
  const { logout: logoutMutation } = useAuthMutations();

  const [searchValue, setSearchValue] = useState("");
  const [sourceSearchValue, setSourceSearchValue] = useState("");
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [trackedJobs, setTrackedJobs] = useState<Record<string, string>>({});
  const [jobStates, setJobStates] = useState<Record<string, JobRecord>>({});
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const autoCreatedSessionRef = useRef(false);

  const notebooksQuery = useNotebooksQuery(Boolean(notebookId));
  const notebookQuery = useNotebookQuery(notebookId, Boolean(notebookId));
  const rawSourcesQuery = useNotebookSourcesQuery(notebookId, Boolean(notebookId));
  const filteredSourcesQuery = useNotebookSourcesFilteredQuery(
    notebookId,
    {
      type: sourceFilters.types,
      status: sourceFilters.statuses,
      from: sourceFilters.from ?? undefined,
      to: sourceFilters.to ?? undefined,
      q: sourceSearchValue.trim() || undefined
    },
    Boolean(notebookId)
  );
  const sourceSearchQuery = useNotebookSourcesSearchQuery(notebookId, sourceSearchValue.trim(), Boolean(notebookId));
  const sourceMutations = useSourceMutations(notebookId);
  const sessionListQuery = useNotebookSessionsQuery(notebookId, Boolean(notebookId));
  const activeSession = useMemo(
    () => (sessionListQuery.data ?? []).find((session) => session.id === activeSessionId) ?? null,
    [activeSessionId, sessionListQuery.data]
  );

  const hasFilters = sourceFilters.types.length > 0 || sourceFilters.statuses.length > 0 || Boolean(sourceFilters.from || sourceFilters.to);
  const activeSourceData = sourceSearchValue.trim()
    ? sourceSearchQuery.data ?? []
    : hasFilters
      ? filteredSourcesQuery.data ?? []
      : rawSourcesQuery.data ?? [];
  const sourcesLoading = sourceSearchValue.trim()
    ? sourceSearchQuery.isLoading
    : hasFilters
      ? filteredSourcesQuery.isLoading
      : rawSourcesQuery.isLoading;
  const baseSourceData = (rawSourcesQuery.data ?? []).length ? rawSourcesQuery.data ?? [] : activeSourceData;
  const mergedDocuments = useMemo(() => mergeSourceProgress(baseSourceData, trackedJobs, jobStates), [baseSourceData, jobStates, trackedJobs]);
  const visibleDocuments = useMemo(() => mergeSourceProgress(activeSourceData, trackedJobs, jobStates), [activeSourceData, trackedJobs, jobStates]);
  const sourceMap = useMemo(() => new Map(mergedDocuments.map((document) => [document.id, document])), [mergedDocuments]);
  const chatMutations = useChatMutations(notebookId, sourceMap);
  const messagesQuery = useNotebookMessagesQuery(notebookId, activeSessionId ?? "", sourceMap, Boolean(notebookId && activeSessionId));
  const chatSearchQuery = useChatSearchQuery(notebookId, searchValue, Boolean(notebookId && searchValue.trim()));
  const podcastsQuery = useNotebookPodcastsQuery(notebookId, Boolean(notebookId));
  const podcastMutations = usePodcastMutations(notebookId);
  const usageQuery = useNotebookUsageQuery(notebookId, Boolean(notebookId));
  const exportMutation = useExportMutation(notebookId);
  const notebookOptions = useMemo(() => (notebooksQuery.data ?? []).map((notebook) => ({ id: notebook.id, title: notebook.title })), [notebooksQuery.data]);

  useEffect(() => {
    autoCreatedSessionRef.current = false;
    setActiveSessionId(null);
    clearSelectedDocuments();
    setActiveDocument(null);
    setHoveredDocument(null);
    setAnswerBoardHighlightedSource(null);
    setFocusedCitation(null);
    setDraftPrompt("");
    setMessages([]);
  }, [
    clearSelectedDocuments,
    notebookId,
    setActiveDocument,
    setAnswerBoardHighlightedSource,
    setFocusedCitation,
    setDraftPrompt,
    setHoveredDocument,
    setMessages
  ]);

  useEffect(() => {
    const knowledge = buildKnowledgeResult(mergedDocuments);
    setKnowledgeGraph(knowledge.documents, knowledge.nodes, knowledge.edges);
  }, [mergedDocuments, setKnowledgeGraph]);

  useEffect(() => {
    if (!activeDocumentId && mergedDocuments[0]) {
      setActiveDocument(mergedDocuments[0].id);
    }
  }, [activeDocumentId, mergedDocuments, setActiveDocument]);

  useEffect(() => {
    const sessions = sessionListQuery.data ?? [];
    if (!notebookId || sessionListQuery.isLoading) {
      return;
    }
    const storageKey = sessionStorageKey(notebookId);
    const storedSessionId = window.localStorage.getItem(storageKey);
    const currentStillExists = activeSessionId && sessions.some((session) => session.id === activeSessionId);
    if (currentStillExists) {
      return;
    }
    if (storedSessionId && sessions.some((session) => session.id === storedSessionId)) {
      setActiveSessionId(storedSessionId);
      return;
    }
    if (sessions[0]) {
      setActiveSessionId(sessions[0].id);
      return;
    }
    if (!autoCreatedSessionRef.current) {
      autoCreatedSessionRef.current = true;
      void createSession("Notebook chat");
    }
  }, [activeSessionId, notebookId, sessionListQuery.data, sessionListQuery.isLoading]);

  useEffect(() => {
    if (!activeSessionId || !notebookId) {
      setMessages([]);
      return;
    }
    window.localStorage.setItem(sessionStorageKey(notebookId), activeSessionId);
  }, [activeSessionId, notebookId, setMessages]);

  useEffect(() => {
    if (messagesQuery.data) {
      setMessages(messagesQuery.data);
    }
  }, [messagesQuery.data, setMessages]);

  useEffect(() => {
    if (!rawSourcesQuery.data?.length) {
      return;
    }
    setTrackedJobs((current) => {
      const next = { ...current };
      for (const source of rawSourcesQuery.data) {
        if (!source.jobId) {
          continue;
        }
        if (source.ingestionJob && ["completed", "failed", "cancelled"].includes(source.ingestionJob.status)) {
          delete next[source.id];
          continue;
        }
        next[source.id] = source.jobId;
      }
      return next;
    });
  }, [rawSourcesQuery.data]);

  useEffect(() => {
    function isTypingTarget(target: EventTarget | null): boolean {
      if (!(target instanceof HTMLElement)) {
        return false;
      }
      const tag = target.tagName.toLowerCase();
      return tag === "input" || tag === "textarea" || target.isContentEditable;
    }

    function handleKeyDown(event: KeyboardEvent): void {
      if (isTypingTarget(event.target)) {
        return;
      }
      if (event.key === "/") {
        event.preventDefault();
        const input = document.getElementById("workspace-global-search") as HTMLInputElement | null;
        input?.focus();
        return;
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        const input = document.getElementById("source-gallery-search") as HTMLInputElement | null;
        input?.focus();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    const entries = Object.entries(trackedJobs);
    if (!entries.length) {
      return;
    }
    let cancelled = false;

    async function pollJobs(): Promise<void> {
      const results = await Promise.all(entries.map(async ([sourceId, jobId]) => ({ sourceId, jobId, job: await getJob(jobId) })));
      if (cancelled) {
        return;
      }
      setJobStates((current) => {
        const next = { ...current };
        for (const result of results) {
          next[result.jobId] = result.job;
        }
        return next;
      });
      const hasSettledJob = results.some((result) => ["completed", "failed", "cancelled"].includes(result.job.status));
      if (hasSettledJob) {
        await queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "sources"] });
        setTrackedJobs((current) => {
          const next = { ...current };
          for (const result of results) {
            if (["completed", "failed", "cancelled"].includes(result.job.status)) {
              delete next[result.sourceId];
            }
          }
          return next;
        });
      }
    }

    void pollJobs();
    const intervalId = window.setInterval(() => void pollJobs(), 2000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [notebookId, queryClient, trackedJobs]);

  const previewDocument = useMemo(() => {
    const focusedId = hoveredDocumentId ?? sceneState.focusedCitationId ?? activeDocumentId;
    return mergedDocuments.find((document) => document.id === focusedId) ?? null;
  }, [activeDocumentId, hoveredDocumentId, mergedDocuments, sceneState.focusedCitationId]);

  const activityMessage = useMemo(() => resolveActivityMessage(trackedJobs, jobStates, mergedDocuments), [jobStates, mergedDocuments, trackedJobs]);
  const activeIngestionJob = useMemo(() => resolveActiveIngestionJob(trackedJobs, jobStates), [jobStates, trackedJobs]);
  const activeMessage = useMemo(() => getLatestAssistantMessage(messages), [messages]);
  const timeline = useMemo(() => getAnswerTimeline(messages), [messages]);
  const insight = useMemo(() => buildInsightSnapshot(mergedDocuments), [mergedDocuments]);
  const historyResults = useMemo(() => chatSearchQuery.data ?? [], [chatSearchQuery.data]);
  const usageSnapshot = useMemo(() => usageQuery.data ?? null, [usageQuery.data]);
  const sessionSummary = activeSession?.summary ?? null;
  const latestPodcast = useMemo(() => {
    const podcasts = podcastsQuery.data ?? [];
    return [...podcasts].sort((left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime())[0] ?? null;
  }, [podcastsQuery.data]);
  const podcastPhase = useMemo(() => mapPodcastPhase(latestPodcast?.status, podcastMutations.createPodcast.isPending), [latestPodcast?.status, podcastMutations.createPodcast.isPending]);
  const podcastScript = latestPodcast?.script ?? "";
  const podcastAudioUrl = latestPodcast?.audioUrl ?? null;
  const waveform = latestPodcast?.waveform ?? [];

  async function createSession(title: string): Promise<string | null> {
    setWorkspaceError(null);
    try {
      const session = await chatMutations.createSession.mutateAsync(title);
      setActiveSessionId(session.id);
      setMessages([]);
      return session.id;
    } catch (error) {
      setWorkspaceError(resolveErrorMessage(error));
      return null;
    }
  }

  async function handleLogout(): Promise<void> {
    try {
      await logoutMutation.mutateAsync();
    } finally {
      clearSession();
      navigate("/auth/login", { replace: true });
    }
  }

  async function handleUploadFile(file: File): Promise<void> {
    setWorkspaceError(null);
    try {
      const result = await sourceMutations.uploadSource.mutateAsync(file);
      setTrackedJobs((current) => ({ ...current, [result.sourceId]: result.jobId }));
    } catch (error) {
      setWorkspaceError(resolveErrorMessage(error));
    }
  }

  async function handleIngestUrl(payload: { url: string; sourceType: "website" | "youtube" }): Promise<void> {
    setWorkspaceError(null);
    try {
      const result = await sourceMutations.ingestUrl.mutateAsync(payload);
      setTrackedJobs((current) => ({ ...current, [result.sourceId]: result.jobId }));
    } catch (error) {
      setWorkspaceError(resolveErrorMessage(error));
    }
  }

  async function handleDeleteSource(sourceId: string): Promise<void> {
    const source = mergedDocuments.find((item) => item.id === sourceId);
    if (!source) {
      return;
    }
    const confirmed = window.confirm(`Delete ${source.title}? This removes the source from the notebook.`);
    if (!confirmed) {
      return;
    }
    setWorkspaceError(null);
    try {
      await sourceMutations.deleteSource.mutateAsync(sourceId);
      setTrackedJobs((current) => {
        const next = { ...current };
        delete next[sourceId];
        return next;
      });
    } catch (error) {
      setWorkspaceError(resolveErrorMessage(error));
    }
  }

  async function handleSubmitPrompt(): Promise<void> {
    const prompt = draftPrompt.trim();
    if (!prompt) {
      return;
    }
    let sessionId = activeSessionId;
    if (!sessionId) {
      sessionId = await createSession("Notebook chat");
    }
    if (!sessionId) {
      setWorkspaceError("Unable to start a chat session.");
      return;
    }

    const selectedSourceIds = attachedDocumentIds.length ? attachedDocumentIds : selectedDocumentIds;
    const userMessage: ChatMessageRecord = {
      id: `user-${Date.now()}`,
      role: "user",
      content: prompt,
      timestamp: new Date().toISOString()
    };
    const placeholderId = `assistant-${Date.now()}`;
    addMessage(userMessage);
    addMessage({
      id: placeholderId,
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
      isStreaming: true,
      visualization: activeMessage?.visualization
    });
    setDraftPrompt("");
    setStreamingAnswerId(placeholderId);
    setWorkspaceError(null);

    try {
      const answer = await chatMutations.sendMessage.mutateAsync({
        sessionId,
        message: prompt,
        sourceIds: selectedSourceIds,
        onToken: (token) => {
          updateMessage(placeholderId, (message) => ({ ...message, content: `${message.content}${token}`, isStreaming: true }));
        }
      });
      updateMessage(placeholderId, () => ({ ...answer, id: placeholderId, isStreaming: false }));
    } catch (error) {
      updateMessage(placeholderId, (message) => ({
        ...message,
        content: resolveErrorMessage(error),
        isStreaming: false,
        citations: []
      }));
      setWorkspaceError(resolveErrorMessage(error));
    } finally {
      setStreamingAnswerId(null);
    }
  }

  async function handleExport(format: "md" | "pdf"): Promise<void> {
    if (!activeSessionId) {
      setWorkspaceError("No active chat session to export.");
      return;
    }
    setWorkspaceError(null);
    const context = {
      topK: chatSettings.topK,
      similarityThreshold: chatSettings.similarityThreshold,
      model: chatSettings.model,
      memoryEnabled: chatSettings.memoryEnabled,
      attachedSourceIds: attachedDocumentIds
    };
    try {
      const blob = await exportMutation.mutateAsync({ sessionId: activeSessionId, format, context });
      downloadBlob(blob, `session-${activeSessionId}.${format}`);
    } catch (error) {
      if (format === "pdf") {
        try {
          const blob = await exportMutation.mutateAsync({ sessionId: activeSessionId, format: "md", context });
          downloadBlob(blob, `session-${activeSessionId}.md`);
          setWorkspaceError("PDF export failed. Downloaded a Markdown report instead.");
          return;
        } catch (fallbackError) {
          setWorkspaceError(fallbackError instanceof ApiError ? fallbackError.message : "Export failed.");
          return;
        }
      }
      setWorkspaceError(error instanceof ApiError ? error.message : "Export failed.");
    }
  }

  function downloadBlob(blob: Blob, filename: string): void {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    window.URL.revokeObjectURL(url);
  }

  async function handleGeneratePodcast(): Promise<void> {
    setWorkspaceError(null);
    try {
      await podcastMutations.createPodcast.mutateAsync({
        sourceIds: selectedDocumentIds,
        title: `Notebook Podcast ${new Date().toLocaleString()}`,
        voice: studioState.selectedVoice
      });
    } catch (error) {
      setWorkspaceError(resolveErrorMessage(error));
    }
  }

  async function handleRetryPodcast(podcastId: string): Promise<void> {
    setWorkspaceError(null);
    try {
      await podcastMutations.retryPodcast.mutateAsync({
        podcastId,
        title: `Notebook Podcast Retry ${new Date().toLocaleString()}`,
        voice: studioState.selectedVoice
      });
    } catch (error) {
      setWorkspaceError(resolveErrorMessage(error));
    }
  }

  async function handleCancelActiveJob(): Promise<void> {
    const activeJobId = activeIngestionJob?.job.id;
    if (!activeJobId) {
      return;
    }
    setWorkspaceError(null);
    try {
      await sourceMutations.cancelJob.mutateAsync(activeJobId);
      setTrackedJobs((current) => {
        const next = { ...current };
        delete next[activeIngestionJob.sourceId];
        return next;
      });
      await queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "sources"] });
    } catch (error) {
      setWorkspaceError(resolveErrorMessage(error));
    }
  }

  function handleNodeSelect(nodeId: string): void {
    const sourceId = nodes.find((node) => node.id === nodeId)?.sourceId;
    if (!sourceId) {
      return;
    }
    setActiveDocument(sourceId);
    toggleDocumentSelection(sourceId);
  }

  function handleNodeHover(nodeId: string | null): void {
    setHoveredNode(nodeId);
    const sourceId = nodes.find((node) => node.id === nodeId)?.sourceId ?? null;
    setHoveredDocument(sourceId);
  }

  function handleCitationHover(sourceId: string | null): void {
    setFocusedCitation(sourceId);
    setAnswerBoardHighlightedSource(sourceId);
  }

  function handleCitationOpen(citation: Citation): void {
    navigate(`/notebooks/${notebookId}/sources/${citation.sourceId}?chunk=${encodeURIComponent(citation.chunkId)}`);
  }

  if (!notebookId) {
    return <div />;
  }

  return (
    <div className="min-h-screen">
      <TopChrome
        activeNotebookId={notebookId}
        notebookOptions={notebookOptions}
        notebookTitle={notebookQuery.data?.title ?? "Notebook workspace"}
        onCreateNotebook={() => navigate("/notebooks")}
        onLogout={() => void handleLogout()}
        onNewChat={() => void createSession(`Chat ${new Date().toLocaleTimeString()}`)}
        onNotebookSelect={(nextNotebookId) => navigate(`/notebooks/${nextNotebookId}`)}
        onSearchChange={setSearchValue}
        onToggleStudio={() => toggleStudioOpen()}
        onThemeChange={(mode: ThemeMode) => setThemeMode(mode)}
        searchPlaceholder="Search chat history"
        searchValue={searchValue}
        statusLabel={activeSessionId ? "Notebook ready" : "Preparing chat"}
        studioOpen={uiShellState.studioOpen}
        themeMode={themeMode}
      />
      <WorkspaceShell
        studioOpen={uiShellState.studioOpen}
        galleryCollapsed={uiShellState.galleryCollapsed}
        onCloseStudio={() => setStudioOpen(false)}
        onToggleGallery={toggleGalleryCollapsed}
        left={
          <SourceNebula
            activeDocumentId={activeDocumentId}
            activityMessage={workspaceError ?? activityMessage}
            canCancelJob={Boolean(activeIngestionJob)}
            documents={visibleDocuments}
            isLoading={sourcesLoading}
            isUploading={sourceMutations.uploadSource.isPending || sourceMutations.ingestUrl.isPending}
            onCancelJob={handleCancelActiveJob}
            onDeleteDocument={(sourceId) => void handleDeleteSource(sourceId)}
            onHoverDocument={setHoveredDocument}
            onIngestUrl={handleIngestUrl}
            onOpenDocument={(sourceId) => navigate(`/notebooks/${notebookId}/sources/${sourceId}`)}
            onSearchChange={setSourceSearchValue}
            onUpdateFilters={setSourceFilters}
            onSelectDocument={(sourceId) => {
              setActiveDocument(sourceId);
              toggleDocumentSelection(sourceId);
            }}
            onUploadFile={handleUploadFile}
            previewDocument={previewDocument}
            searchValue={sourceSearchValue}
            selectedDocumentIds={selectedDocumentIds}
            filters={sourceFilters}
          />
        }
        right={
          <AIStudioPanel
            activeTab={uiShellState.activeStudioTab}
            chatSettings={chatSettings}
            documents={mergedDocuments}
            insight={insight}
            isGeneratingPodcast={podcastMutations.createPodcast.isPending || podcastPhase !== "idle" && podcastPhase !== "complete"}
            historyQuery={searchValue}
            historyResults={historyResults}
            historyLoading={chatSearchQuery.isLoading}
            onOpenHistoryResult={(sessionId) => {
              setActiveSessionId(sessionId);
              setActiveStudioTab("chat");
            }}
            sessionSummary={sessionSummary}
            usage={usageSnapshot}
            onGeneratePodcast={handleGeneratePodcast}
            onTabChange={setActiveStudioTab}
            onRetryPodcast={handleRetryPodcast}
            onSelectVoice={setSelectedVoice}
            onUpdateChatSettings={updateChatSettings}
            podcastAudioUrl={podcastAudioUrl}
            podcastPhase={podcastPhase}
            podcastScript={podcastScript}
            podcasts={podcastsQuery.data ?? []}
            selectedDocumentIds={selectedDocumentIds}
            selectedVoice={studioState.selectedVoice}
            waveform={waveform}
          />
        }
      >
        <AnswerBoard
          activeDocumentId={activeDocumentId}
          activeMessage={activeMessage}
          answerSections={answerBoardState.expandedSections}
          attachedCount={attachedDocumentIds.length}
          documents={mergedDocuments}
          draftPrompt={draftPrompt}
          edges={edges}
          highlightedSourceId={answerBoardState.highlightedSourceId}
          isSending={chatMutations.sendMessage.isPending}
          nodes={nodes}
          onCitationHover={handleCitationHover}
          onCitationOpen={handleCitationOpen}
          onDraftChange={setDraftPrompt}
          onExport={(format) => void handleExport(format)}
          onNodeHover={handleNodeHover}
          onNodeSelect={(node) => handleNodeSelect(node.id)}
          onSubmit={handleSubmitPrompt}
          onToggleSection={(section, expanded) => setAnswerSectionExpanded(section, expanded)}
          onViewChange={setAnswerViewMode}
          selectedDocumentIds={selectedDocumentIds}
          timeline={timeline}
          viewMode={answerBoardState.viewMode}
        />
      </WorkspaceShell>
    </div>
  );
}

function sessionStorageKey(notebookId: string): string {
  return `notebooklm-active-session:${notebookId}`;
}

function resolveActivityMessage(trackedJobs: Record<string, string>, jobStates: Record<string, JobRecord>, documents: SourceDocument[]): string | null {
  const activeSourceIds = Object.keys(trackedJobs);
  if (!activeSourceIds.length) {
    const failedDocument = documents.find((document) => document.backendStatus === "failed");
    return failedDocument ? `${failedDocument.title} failed to index. Review the source detail for chunking or parsing errors.` : null;
  }
  const activeJob = activeSourceIds
    .map((sourceId) => jobStates[trackedJobs[sourceId] ?? ""])
    .find((job) => job && (job.status === "queued" || job.status === "running"));
  if (!activeJob) {
    return "Refreshing notebook sources...";
  }
  return activeJob.status === "queued" ? "Source queued for ingestion." : `Indexing source... ${activeJob.progress}%`;
}

function resolveActiveIngestionJob(
  trackedJobs: Record<string, string>,
  jobStates: Record<string, JobRecord>
): { sourceId: string; job: JobRecord } | null {
  for (const [sourceId, jobId] of Object.entries(trackedJobs)) {
    const job = jobStates[jobId];
    if (job && (job.status === "queued" || job.status === "running")) {
      return { sourceId, job };
    }
  }
  return null;
}

function mergeSourceProgress(
  documents: SourceDocument[],
  trackedJobs: Record<string, string>,
  jobStates: Record<string, JobRecord>
): SourceDocument[] {
  return documents.map((document) => {
    const jobId = trackedJobs[document.id];
    if (!jobId) {
      return document;
    }
    const job = jobStates[jobId];
    if (!job) {
      return { ...document, jobId };
    }
    return {
      ...document,
      jobId,
      progress: job.progress,
      status: job.status === "failed" ? "error" : job.status === "completed" ? "ready" : "processing",
      backendStatus: job.status === "completed" ? document.backendStatus : job.status
    };
  });
}

function mapPodcastPhase(status: string | undefined, isCreating: boolean): PodcastGenerationPhase {
  if (isCreating) {
    return "warming";
  }
  if (status === "queued") {
    return "scripting";
  }
  if (status === "processing") {
    return "voicing";
  }
  if (status === "completed") {
    return "complete";
  }
  return "idle";
}

function resolveErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Request failed.";
}
