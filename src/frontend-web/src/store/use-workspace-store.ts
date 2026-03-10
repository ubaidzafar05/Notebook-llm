import { create } from "zustand";
import type {
  AnswerVisualization,
  ChatMessageRecord,
  KnowledgeEdge,
  KnowledgeNode,
  ModelOption,
  PodcastGenerationPhase,
  SourceDocument,
  VoiceOption
} from "@/lib/api";

type ChatSettings = {
  topK: number;
  similarityThreshold: number;
  model: ModelOption;
  memoryEnabled: boolean;
};

export type ThemeMode = "notebook-dark" | "linen-light" | "dusk-indigo";

type DocumentState = {
  documents: SourceDocument[];
  selectedDocumentIds: string[];
  hoveredDocumentId: string | null;
  activeDocumentId: string | null;
  ingestionStateById: Record<string, SourceDocument["status"]>;
};

type SceneState = {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  viewport: { panX: number; panY: number; zoom: number };
  focusedCitationId: string | null;
  activeAnswerId: string | null;
  hoveredNodeId: string | null;
  reducedMotion: boolean;
  webglReady: boolean;
};

type ChatState = {
  messages: ChatMessageRecord[];
  draftPrompt: string;
  streamingAnswerId: string | null;
  attachedDocumentIds: string[];
};

type StudioState = {
  chatSettings: ChatSettings;
  podcastGenerationState: PodcastGenerationPhase;
  selectedVoice: VoiceOption;
  podcastScript: string;
  podcastAudioUrl: string | null;
  waveform: number[];
  themeMode: ThemeMode;
};

export type StudioTab = "chat" | "podcast" | "insight";

type UiShellState = {
  studioOpen: boolean;
  activeStudioTab: StudioTab;
  galleryCollapsed: boolean;
};

type AnswerBoardState = {
  expandedSections: {
    response: boolean;
    citations: boolean;
    notes: boolean;
  };
  highlightedSourceId: string | null;
};

type WorkspaceState = {
  documentsState: DocumentState;
  sceneState: SceneState;
  chatState: ChatState;
  studioState: StudioState;
  uiShellState: UiShellState;
  answerBoardState: AnswerBoardState;
  setKnowledgeGraph: (documents: SourceDocument[], nodes: KnowledgeNode[], edges: KnowledgeEdge[]) => void;
  setMessages: (messages: ChatMessageRecord[]) => void;
  addMessage: (message: ChatMessageRecord) => void;
  updateMessage: (messageId: string, updater: (message: ChatMessageRecord) => ChatMessageRecord) => void;
  setDraftPrompt: (draftPrompt: string) => void;
  toggleDocumentSelection: (sourceId: string) => void;
  setHoveredDocument: (sourceId: string | null) => void;
  setActiveDocument: (sourceId: string | null) => void;
  setAttachedDocuments: (sourceIds: string[]) => void;
  setFocusedCitation: (sourceId: string | null) => void;
  setStreamingAnswerId: (messageId: string | null) => void;
  setNodePosition: (nodeId: string, position: KnowledgeNode["position"]) => void;
  setHoveredNode: (nodeId: string | null) => void;
  setReducedMotion: (enabled: boolean) => void;
  setWebglReady: (ready: boolean) => void;
  setThemeMode: (themeMode: ThemeMode) => void;
  cycleThemeMode: () => void;
  setStudioOpen: (open: boolean) => void;
  toggleStudioOpen: () => void;
  setActiveStudioTab: (tab: StudioTab) => void;
  updateChatSettings: (patch: Partial<ChatSettings>) => void;
  setSelectedVoice: (voice: VoiceOption) => void;
  setPodcastState: (phase: PodcastGenerationPhase) => void;
  setPodcastOutput: (payload: { script: string; audioUrl: string; waveform: number[] }) => void;
  setAnswerSectionExpanded: (section: keyof AnswerBoardState["expandedSections"], expanded: boolean) => void;
  setAnswerBoardHighlightedSource: (sourceId: string | null) => void;
  setGalleryCollapsed: (collapsed: boolean) => void;
  toggleGalleryCollapsed: () => void;
};

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  documentsState: {
    documents: [],
    selectedDocumentIds: ["src-1", "src-2"],
    hoveredDocumentId: null,
    activeDocumentId: "src-1",
    ingestionStateById: {}
  },
  sceneState: {
    nodes: [],
    edges: [],
    viewport: { panX: 0, panY: 0, zoom: 1 },
    focusedCitationId: null,
    activeAnswerId: null,
    hoveredNodeId: null,
    reducedMotion: false,
    webglReady: true
  },
  chatState: {
    messages: [],
    draftPrompt: "",
    streamingAnswerId: null,
    attachedDocumentIds: ["src-1", "src-2"]
  },
  studioState: {
    chatSettings: {
      topK: 6,
      similarityThreshold: 0.72,
      model: "ollama/qwen3:8b",
      memoryEnabled: true
    },
    podcastGenerationState: "idle",
    selectedVoice: "Alloy Host",
    podcastScript: "",
    podcastAudioUrl: null,
    waveform: [],
    themeMode: "dusk-indigo"
  },
  uiShellState: {
    studioOpen: false,
    activeStudioTab: "chat",
    galleryCollapsed: false,
  },
  answerBoardState: {
    expandedSections: {
      response: true,
      citations: true,
      notes: true
    },
    highlightedSourceId: null
  },
  setKnowledgeGraph: (documents, nodes, edges) =>
    set((state) => ({
      documentsState: {
        ...state.documentsState,
        documents,
        ingestionStateById: Object.fromEntries(documents.map((document) => [document.id, document.status])),
        activeDocumentId: state.documentsState.activeDocumentId && documents.some((document) => document.id === state.documentsState.activeDocumentId)
          ? state.documentsState.activeDocumentId
          : documents[0]?.id ?? null,
        selectedDocumentIds: state.documentsState.selectedDocumentIds.filter((sourceId) => documents.some((document) => document.id === sourceId))
      },
      sceneState: {
        ...state.sceneState,
        nodes,
        edges
      },
      chatState: {
        ...state.chatState,
        attachedDocumentIds: state.chatState.attachedDocumentIds.filter((sourceId) => documents.some((document) => document.id === sourceId))
      }
    })),
  setMessages: (messages) => set((state) => ({ chatState: { ...state.chatState, messages } })),
  addMessage: (message) =>
    set((state) => ({
      chatState: { ...state.chatState, messages: [...state.chatState.messages, message] },
      sceneState: {
        ...state.sceneState,
        activeAnswerId: message.role === "assistant" ? message.id : state.sceneState.activeAnswerId
      }
    })),
  updateMessage: (messageId, updater) =>
    set((state) => ({
      chatState: {
        ...state.chatState,
        messages: state.chatState.messages.map((message) => (message.id === messageId ? updater(message) : message))
      }
    })),
  setDraftPrompt: (draftPrompt) => set((state) => ({ chatState: { ...state.chatState, draftPrompt } })),
  toggleDocumentSelection: (sourceId) =>
    set((state) => {
      const selected = state.documentsState.selectedDocumentIds.includes(sourceId)
        ? state.documentsState.selectedDocumentIds.filter((id) => id !== sourceId)
        : [...state.documentsState.selectedDocumentIds, sourceId];
      return {
        documentsState: { ...state.documentsState, selectedDocumentIds: selected },
        chatState: { ...state.chatState, attachedDocumentIds: selected }
      };
    }),
  setHoveredDocument: (sourceId) => set((state) => ({ documentsState: { ...state.documentsState, hoveredDocumentId: sourceId } })),
  setActiveDocument: (sourceId) => set((state) => ({ documentsState: { ...state.documentsState, activeDocumentId: sourceId } })),
  setAttachedDocuments: (sourceIds) => set((state) => ({ chatState: { ...state.chatState, attachedDocumentIds: sourceIds } })),
  setFocusedCitation: (sourceId) => set((state) => ({ sceneState: { ...state.sceneState, focusedCitationId: sourceId } })),
  setStreamingAnswerId: (messageId) => set((state) => ({ chatState: { ...state.chatState, streamingAnswerId: messageId } })),
  setNodePosition: (nodeId, position) =>
    set((state) => ({
      sceneState: {
        ...state.sceneState,
        nodes: state.sceneState.nodes.map((node) => (node.id === nodeId ? { ...node, position } : node))
      }
    })),
  setHoveredNode: (nodeId) => set((state) => ({ sceneState: { ...state.sceneState, hoveredNodeId: nodeId } })),
  setReducedMotion: (enabled) => set((state) => ({ sceneState: { ...state.sceneState, reducedMotion: enabled } })),
  setWebglReady: (ready) => set((state) => ({ sceneState: { ...state.sceneState, webglReady: ready } })),
  setThemeMode: (themeMode) => set((state) => ({ studioState: { ...state.studioState, themeMode } })),
  cycleThemeMode: () =>
    set((state) => {
      const order: ThemeMode[] = ["dusk-indigo", "linen-light", "notebook-dark"];
      const index = order.indexOf(state.studioState.themeMode);
      const themeMode = order[(index + 1) % order.length] ?? "notebook-dark";
      return {
        studioState: {
          ...state.studioState,
          themeMode
        }
      };
    }),
  setStudioOpen: (open) => set((state) => ({ uiShellState: { ...state.uiShellState, studioOpen: open } })),
  toggleStudioOpen: () => set((state) => ({ uiShellState: { ...state.uiShellState, studioOpen: !state.uiShellState.studioOpen } })),
  setActiveStudioTab: (tab) => set((state) => ({ uiShellState: { ...state.uiShellState, activeStudioTab: tab } })),
  updateChatSettings: (patch) =>
    set((state) => ({
      studioState: {
        ...state.studioState,
        chatSettings: { ...state.studioState.chatSettings, ...patch }
      }
    })),
  setSelectedVoice: (voice) => set((state) => ({ studioState: { ...state.studioState, selectedVoice: voice } })),
  setPodcastState: (phase) => set((state) => ({ studioState: { ...state.studioState, podcastGenerationState: phase } })),
  setPodcastOutput: ({ script, audioUrl, waveform }) =>
    set((state) => ({
      studioState: {
        ...state.studioState,
        podcastScript: script,
        podcastAudioUrl: audioUrl,
        waveform,
        podcastGenerationState: "complete"
      }
    })),
  setAnswerSectionExpanded: (section, expanded) =>
    set((state) => ({
      answerBoardState: {
        ...state.answerBoardState,
        expandedSections: {
          ...state.answerBoardState.expandedSections,
          [section]: expanded
        }
      }
    })),
  setAnswerBoardHighlightedSource: (sourceId) => set((state) => ({ answerBoardState: { ...state.answerBoardState, highlightedSourceId: sourceId } })),
  setGalleryCollapsed: (collapsed) => set((state) => ({ uiShellState: { ...state.uiShellState, galleryCollapsed: collapsed } })),
  toggleGalleryCollapsed: () => set((state) => ({ uiShellState: { ...state.uiShellState, galleryCollapsed: !state.uiShellState.galleryCollapsed } })),
}));

export const workspaceSelectors = {
  documents: (state: WorkspaceState) => state.documentsState.documents,
  selectedDocumentIds: (state: WorkspaceState) => state.documentsState.selectedDocumentIds,
  activeDocumentId: (state: WorkspaceState) => state.documentsState.activeDocumentId,
  hoveredDocumentId: (state: WorkspaceState) => state.documentsState.hoveredDocumentId,
  nodes: (state: WorkspaceState) => state.sceneState.nodes,
  edges: (state: WorkspaceState) => state.sceneState.edges,
  messages: (state: WorkspaceState) => state.chatState.messages,
  draftPrompt: (state: WorkspaceState) => state.chatState.draftPrompt,
  attachedDocumentIds: (state: WorkspaceState) => state.chatState.attachedDocumentIds,
  chatSettings: (state: WorkspaceState) => state.studioState.chatSettings,
  studioState: (state: WorkspaceState) => state.studioState,
  sceneState: (state: WorkspaceState) => state.sceneState,
  uiShellState: (state: WorkspaceState) => state.uiShellState,
  answerBoardState: (state: WorkspaceState) => state.answerBoardState
};

export function getLatestAssistantMessage(messages: ChatMessageRecord[]): ChatMessageRecord | null {
  return [...messages].reverse().find((message) => message.role === "assistant") ?? null;
}

export function getAnswerTimeline(messages: ChatMessageRecord[]): ChatMessageRecord[] {
  return messages.filter((message) => message.role === "assistant").slice(-4).reverse();
}

export function getActiveVisualization(messages: ChatMessageRecord[]): AnswerVisualization | null {
  return getLatestAssistantMessage(messages)?.visualization ?? null;
}
