import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { ingestNotebookUrl, listNotebookSources, listSourceChunks, uploadNotebookSource } from "../lib/api";
import { queryClient } from "../app/queryClient";
import { useWorkspaceStore } from "../state/workspace-store";
import type { Source } from "../types/api";
import styles from "./Workspace.module.css";

type SourcePanelProps = {
  notebookId: string;
};

export function SourcePanel({ notebookId }: SourcePanelProps): JSX.Element {
  const sourceFocus = useWorkspaceStore((state) => state.sourceFocus);
  const inspectedSourceId = useWorkspaceStore((state) => state.inspectedSourceId);
  const setInspectedSourceId = useWorkspaceStore((state) => state.setInspectedSourceId);
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [sourceType, setSourceType] = useState<"web" | "youtube">("web");
  const [message, setMessage] = useState<string | null>(null);
  const sourcesQuery = useQuery({
    queryKey: ["sources", notebookId],
    queryFn: () => listNotebookSources(notebookId),
    refetchInterval: 5_000,
  });
  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file) {
        throw new Error("Select a file first");
      }
      return uploadNotebookSource(notebookId, file);
    },
    onSuccess: (result) => {
      setMessage(`Source queued: ${result.source_id}`);
      setFile(null);
      void queryClient.invalidateQueries({ queryKey: ["sources", notebookId] });
    },
  });
  const urlMutation = useMutation({
    mutationFn: () => ingestNotebookUrl(notebookId, url.trim(), sourceType),
    onSuccess: (result) => {
      setMessage(`URL queued: ${result.source_id}`);
      setUrl("");
      void queryClient.invalidateQueries({ queryKey: ["sources", notebookId] });
    },
  });
  const sources = sourcesQuery.data ?? [];
  const focusedSource = useMemo(
    () => sources.find((item) => item.id === (sourceFocus?.sourceId ?? inspectedSourceId)) ?? sources[0],
    [inspectedSourceId, sourceFocus?.sourceId, sources],
  );
  const sourceChunksQuery = useQuery({
    queryKey: ["source-chunks", notebookId, focusedSource?.id],
    queryFn: () => listSourceChunks(notebookId, focusedSource!.id),
    enabled: Boolean(focusedSource?.id),
  });

  useEffect(() => {
    if (focusedSource?.id) {
      setInspectedSourceId(focusedSource.id);
    }
  }, [focusedSource?.id, setInspectedSourceId]);

  return (
    <div className={styles.column}>
      <div className={styles.panelHeader}>
        <p className={styles.eyebrow}>Sources</p>
        <h2 className={styles.panelTitle}>Ingest and Inspect</h2>
      </div>
      <div className={styles.panelBody}>
        <section className={styles.section}>
          <label className={styles.label}>
            Upload file
            <input className={styles.input} onChange={(event) => setFile(event.target.files?.[0] ?? null)} type="file" />
          </label>
          <button className={styles.button} disabled={!file || uploadMutation.isPending} onClick={() => uploadMutation.mutate()} type="button">
            {uploadMutation.isPending ? "Queueing..." : "Upload Source"}
          </button>
        </section>
        <section className={styles.section}>
          <label className={styles.label}>
            Web or YouTube URL
            <input className={styles.input} value={url} onChange={(event) => setUrl(event.target.value)} />
          </label>
          <label className={styles.label}>
            Source type
            <select className={styles.select} value={sourceType} onChange={(event) => setSourceType(event.target.value as "web" | "youtube")}>
              <option value="web">Web</option>
              <option value="youtube">YouTube</option>
            </select>
          </label>
          <button className={styles.secondaryButton} disabled={!url.trim() || urlMutation.isPending} onClick={() => urlMutation.mutate()} type="button">
            {urlMutation.isPending ? "Queueing..." : "Ingest URL"}
          </button>
          {message ? <p className={styles.tinyMeta}>{message}</p> : null}
        </section>
        <SourceList notebookId={notebookId} sources={sources} />
        <SourceInspector focusedSource={focusedSource} notebookId={notebookId} />
        {sourceChunksQuery.error ? <p className={styles.error}>{String(sourceChunksQuery.error)}</p> : null}
      </div>
    </div>
  );
}

function SourceList({ notebookId, sources }: { notebookId: string; sources: Source[] }): JSX.Element {
  const setInspectedSourceId = useWorkspaceStore((state) => state.setInspectedSourceId);
  if (!sources.length) {
    return <div className={styles.emptyState}>No sources yet in this notebook.</div>;
  }
  return (
    <section className={styles.section}>
      <p className={styles.eyebrow}>Notebook Sources</p>
      <div className={styles.cardList}>
        {sources.map((source) => (
          <button key={source.id} className={styles.card} onClick={() => setInspectedSourceId(source.id)} type="button">
            <p className={styles.cardTitle}>{source.name}</p>
            <p className={styles.cardMeta}>
              {source.source_type} · {source.status} · {formatSourceMeta(source)}
            </p>
            <p className={styles.tinyMeta}>{notebookId.slice(0, 8)}</p>
          </button>
        ))}
      </div>
    </section>
  );
}

function formatSourceMeta(source: Source): string {
  const sectionHeading = source.metadata["section_heading"];
  if (typeof sectionHeading === "string" && sectionHeading) {
    return sectionHeading;
  }
  return source.path_or_url;
}

function SourceInspector({ notebookId, focusedSource }: { notebookId: string; focusedSource?: Source }): JSX.Element {
  const focus = useWorkspaceStore((state) => state.sourceFocus);
  const query = useQuery({
    queryKey: ["source-inspector", notebookId, focusedSource?.id],
    queryFn: () => listSourceChunks(notebookId, focusedSource!.id),
    enabled: Boolean(focusedSource?.id),
  });
  if (!focusedSource) {
    return <div className={styles.emptyState}>Select a source to inspect chunk anchors.</div>;
  }
  return (
    <section className={styles.section}>
      <p className={styles.eyebrow}>Chunk Drilldown</p>
      <p className={styles.cardTitle}>{focusedSource.name}</p>
      <div className={styles.scrollSection}>
        <div className={styles.cardList}>
          {query.data?.chunks.map((chunk) => (
            <div key={chunk.chunk_id} className={chunk.chunk_id === focus?.chunkId ? styles.cardActive : styles.card}>
              <p className={styles.cardTitle}>Chunk {chunk.chunk_index}</p>
              <p className={styles.cardMeta}>{chunk.excerpt}</p>
              <p className={styles.tinyMeta}>{JSON.stringify(chunk.citation)}</p>
            </div>
          )) ?? <div className={styles.emptyState}>No chunks available yet.</div>}
        </div>
      </div>
    </section>
  );
}
