import { beforeEach, describe, expect, it } from "vitest";
import { useWorkspaceStore } from "./workspace-store";

describe("useWorkspaceStore", () => {
  beforeEach(() => {
    useWorkspaceStore.setState({
      notebookId: null,
      selectedSessionId: null,
      selectedSourceIds: [],
      inspectedSourceId: null,
      sourceFocus: null,
    });
  });

  it("resets notebook-scoped selections when notebook changes", () => {
    useWorkspaceStore.setState({
      notebookId: "nb-1",
      selectedSessionId: "session-1",
      selectedSourceIds: ["source-1"],
      inspectedSourceId: "source-1",
      sourceFocus: { sourceId: "source-1", chunkId: "chunk-1" },
    });

    useWorkspaceStore.getState().setNotebookContext("nb-2");

    expect(useWorkspaceStore.getState()).toMatchObject({
      notebookId: "nb-2",
      selectedSessionId: null,
      selectedSourceIds: [],
      inspectedSourceId: null,
      sourceFocus: null,
    });
  });

  it("keeps source focus and inspected source aligned", () => {
    useWorkspaceStore.getState().focusSource({
      sourceId: "source-99",
      chunkId: "chunk-42",
      pageNumber: 3,
    });

    expect(useWorkspaceStore.getState().inspectedSourceId).toBe("source-99");
    expect(useWorkspaceStore.getState().sourceFocus?.chunkId).toBe("chunk-42");
  });
});
