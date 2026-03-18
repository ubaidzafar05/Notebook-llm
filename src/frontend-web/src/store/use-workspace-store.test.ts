import { beforeEach, describe, expect, it } from "vitest";
import type { KnowledgeNode, SourceDocument } from "@/lib/api";
import { useWorkspaceStore } from "@/store/use-workspace-store";

const documentSeed: SourceDocument = {
  id: "src-test",
  notebookId: "nb-1",
  title: "Seed.txt",
  type: "txt",
  status: "ready",
  progress: 100,
  summary: "Seed",
  chunks: 3,
  embeddingsCount: 3,
  updatedAt: new Date().toISOString(),
  accent: "#45d4ff",
  preview: {
    sourceId: "src-test",
    headline: "Seed",
    metadata: ["TXT"],
    excerpt: "Seed excerpt"
  },
  nodePosition: { x: 20, y: 30, z: 0 },
  backendStatus: "ready",
  pathOrUrl: "Seed.txt",
  metadata: {}
};

const nodeSeed: KnowledgeNode = {
  id: "node-src-test",
  sourceId: "src-test",
  label: "Seed.txt",
  kind: "source",
  position: { x: 20, y: 30, z: 0 },
  size: "md",
  accent: "#45d4ff",
  status: "ready"
};

beforeEach(() => {
  useWorkspaceStore.setState((state) => ({
    ...state,
    documentsState: {
      ...state.documentsState,
      documents: [documentSeed],
      selectedDocumentIds: [],
      activeDocumentId: "src-test"
    },
    sceneState: {
      ...state.sceneState,
      nodes: [nodeSeed],
      edges: []
    },
    chatState: {
      ...state.chatState,
      attachedDocumentIds: []
    }
  }));
});

describe("workspace store", () => {
  it("toggles document selection and composer attachments together", () => {
    useWorkspaceStore.getState().toggleDocumentSelection("src-test");
    expect(useWorkspaceStore.getState().documentsState.selectedDocumentIds).toEqual(["src-test"]);
    expect(useWorkspaceStore.getState().chatState.attachedDocumentIds).toEqual(["src-test"]);
  });

  it("updates node positions after constrained drag", () => {
    useWorkspaceStore.getState().setNodePosition("node-src-test", { x: 48, y: 42, z: 0 });
    expect(useWorkspaceStore.getState().sceneState.nodes[0]?.position).toEqual({ x: 48, y: 42, z: 0 });
  });
});

describe("gallery collapsed state", () => {
  beforeEach(() => {
    useWorkspaceStore.getState().setGalleryCollapsed(false);
  });

  it("defaults to not collapsed", () => {
    expect(useWorkspaceStore.getState().uiShellState.galleryCollapsed).toBe(false);
  });

  it("sets gallery collapsed to true", () => {
    useWorkspaceStore.getState().setGalleryCollapsed(true);
    expect(useWorkspaceStore.getState().uiShellState.galleryCollapsed).toBe(true);
  });

  it("toggles gallery collapsed state", () => {
    expect(useWorkspaceStore.getState().uiShellState.galleryCollapsed).toBe(false);
    useWorkspaceStore.getState().toggleGalleryCollapsed();
    expect(useWorkspaceStore.getState().uiShellState.galleryCollapsed).toBe(true);
    useWorkspaceStore.getState().toggleGalleryCollapsed();
    expect(useWorkspaceStore.getState().uiShellState.galleryCollapsed).toBe(false);
  });
});

describe("theme mode", () => {
  it("defaults to everforest-light", () => {
    expect(useWorkspaceStore.getState().studioState.themeMode).toBe("everforest-light");
  });

  it("cycles between light and dark", () => {
    useWorkspaceStore.getState().cycleThemeMode();
    expect(useWorkspaceStore.getState().studioState.themeMode).toBe("everforest-dark");
    useWorkspaceStore.getState().cycleThemeMode();
    expect(useWorkspaceStore.getState().studioState.themeMode).toBe("everforest-light");
  });

  it("sets theme mode directly", () => {
    useWorkspaceStore.getState().setThemeMode("everforest-dark");
    expect(useWorkspaceStore.getState().studioState.themeMode).toBe("everforest-dark");
  });
});
