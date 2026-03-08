import { useMutation, useQuery } from "@tanstack/react-query";
import { createNotebookPodcast, getDependencyHealth, getMemorySummary, listNotebookPodcasts, listNotebookSources, podcastAudioUrl, retryNotebookPodcast } from "../lib/api";
import { queryClient } from "../app/queryClient";
import { useWorkspaceStore } from "../state/workspace-store";
import styles from "./Workspace.module.css";

type StudioPanelProps = {
  notebookId: string;
};

export function StudioPanel({ notebookId }: StudioPanelProps): JSX.Element {
  const selectedSessionId = useWorkspaceStore((state) => state.selectedSessionId);
  const sourcesQuery = useQuery({
    queryKey: ["studio-sources", notebookId],
    queryFn: () => listNotebookSources(notebookId),
  });
  const memoryQuery = useQuery({
    queryKey: ["memory-summary", selectedSessionId],
    queryFn: () => getMemorySummary(selectedSessionId!),
    enabled: Boolean(selectedSessionId),
  });
  const dependencyQuery = useQuery({
    queryKey: ["dependency-health"],
    queryFn: getDependencyHealth,
    refetchInterval: 30_000,
  });
  const podcastsQuery = useQuery({
    queryKey: ["podcasts", notebookId],
    queryFn: () => listNotebookPodcasts(notebookId),
    refetchInterval: 5_000,
  });
  const createMutation = useMutation({
    mutationFn: (sourceIds: string[]) => createNotebookPodcast(notebookId, sourceIds, "Notebook Briefing"),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["podcasts", notebookId] });
    },
  });
  const retryMutation = useMutation({
    mutationFn: (podcastId: string) => retryNotebookPodcast(notebookId, podcastId, "Notebook Briefing Retry"),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["podcasts", notebookId] });
    },
  });
  const sourceIds = sourcesQuery.data?.map((source) => source.id) ?? [];

  return (
    <div className={styles.column}>
      <div className={styles.panelHeader}>
        <p className={styles.eyebrow}>Studio</p>
        <h2 className={styles.panelTitle}>Memory, Health, Podcasts</h2>
      </div>
      <div className={styles.panelBody}>
        <section className={styles.section}>
          <p className={styles.eyebrow}>Memory Summary</p>
          {memoryQuery.data ? (
            <>
              <p className={styles.cardTitle}>{memoryQuery.data.summary}</p>
              <p className={styles.tinyMeta}>Provider: {memoryQuery.data.provider}</p>
            </>
          ) : (
            <div className={styles.emptyState}>Select a session to inspect the current Zep summary.</div>
          )}
        </section>
        <section className={styles.section}>
          <p className={styles.eyebrow}>Dependencies</p>
          <div className={styles.cardList}>
            {Object.entries(dependencyQuery.data ?? {}).map(([name, item]) => (
              <div key={name} className={styles.card}>
                <p className={styles.cardTitle}>{name}</p>
                <p className={item.status === "up" ? styles.statusUp : item.status === "degraded" ? styles.statusDegraded : styles.statusDown}>
                  {item.status}
                </p>
                <p className={styles.cardMeta}>{item.detail}</p>
              </div>
            ))}
          </div>
        </section>
        <section className={styles.section}>
          <p className={styles.eyebrow}>Podcast Studio</p>
          <button className={styles.button} disabled={!sourceIds.length || createMutation.isPending} onClick={() => createMutation.mutate(sourceIds)} type="button">
            {createMutation.isPending ? "Queueing..." : "Generate Podcast"}
          </button>
          <div className={styles.cardList}>
            {podcastsQuery.data?.map((podcast) => (
              <div key={podcast.id} className={styles.card}>
                <p className={styles.cardTitle}>{podcast.id.slice(0, 8)}</p>
                <p className={styles.cardMeta}>
                  {podcast.status} · {podcast.updated_at}
                </p>
                {podcast.failure_code ? <p className={styles.error}>{podcast.failure_code}: {podcast.failure_detail}</p> : null}
                <div className={styles.footerRow}>
                  <button className={styles.secondaryButton} onClick={() => retryMutation.mutate(podcast.id)} type="button">
                    Retry
                  </button>
                  {podcast.output_path ? (
                    <a className={styles.button} href={podcastAudioUrl(notebookId, podcast.id)}>
                      Download
                    </a>
                  ) : null}
                </div>
              </div>
            )) ?? <div className={styles.emptyState}>No podcast jobs yet.</div>}
          </div>
        </section>
      </div>
    </div>
  );
}
