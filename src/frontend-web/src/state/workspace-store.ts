import { create } from "zustand";

export type SourceFocus = {
  sourceId: string;
  chunkId?: string;
  pageNumber?: number | null;
  startTimestamp?: number | null;
  endTimestamp?: number | null;
};

type WorkspaceState = {
  notebookId: string | null;
  selectedSessionId: string | null;
  selectedSourceIds: string[];
  inspectedSourceId: string | null;
  sourceFocus: SourceFocus | null;
  setNotebookContext: (notebookId: string) => void;
  setSelectedSessionId: (sessionId: string | null) => void;
  setSelectedSourceIds: (sourceIds: string[]) => void;
  setInspectedSourceId: (sourceId: string | null) => void;
  focusSource: (focus: SourceFocus | null) => void;
};

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  notebookId: null,
  selectedSessionId: null,
  selectedSourceIds: [],
  inspectedSourceId: null,
  sourceFocus: null,
  setNotebookContext: (notebookId) => {
    if (get().notebookId === notebookId) {
      return;
    }
    set({
      notebookId,
      selectedSessionId: null,
      selectedSourceIds: [],
      inspectedSourceId: null,
      sourceFocus: null,
    });
  },
  setSelectedSessionId: (selectedSessionId) => set({ selectedSessionId }),
  setSelectedSourceIds: (selectedSourceIds) => set({ selectedSourceIds }),
  setInspectedSourceId: (inspectedSourceId) => set({ inspectedSourceId }),
  focusSource: (sourceFocus) =>
    set({
      sourceFocus,
      inspectedSourceId: sourceFocus?.sourceId ?? null,
    }),
}));
