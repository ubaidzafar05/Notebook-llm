import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  cancelJob,
  createNotebook,
  createNotebookPodcast,
  createNotebookSession,
  deleteNotebook,
  deleteNotebookSource,
  exchangeGoogleCode,
  exportNotebookSession,
  getJob,
  getNotebook,
  getNotebookSource,
  getNotebookUsage,
  getSourceChunks,
  ingestNotebookUrl,
  listNotebookMessages,
  listNotebookPodcasts,
  listNotebooks,
  listNotebookSessions,
  listNotebookSources,
  listNotebookSourcesFiltered,
  login,
  logout,
  register,
  retryNotebookPodcast,
  searchNotebookMessages,
  searchNotebookSources,
  startGoogleAuth,
  streamNotebookMessage,
  updateNotebook,
  uploadNotebookSource,
  type ChatSession,
  type SourceDocument,
  type VoiceOption,
  type UrlIngestPayload
} from "@/lib/api";

type SourceMapContext = Map<string, SourceDocument>;

export function useNotebooksQuery(enabled = true) {
  return useQuery({
    queryKey: ["notebooks"],
    queryFn: listNotebooks,
    enabled
  });
}

export function useNotebookQuery(notebookId: string, enabled = true) {
  return useQuery({
    queryKey: ["notebooks", notebookId],
    queryFn: () => getNotebook(notebookId),
    enabled: enabled && Boolean(notebookId)
  });
}

export function useNotebookSourcesQuery(notebookId: string, enabled = true) {
  return useQuery({
    queryKey: ["notebooks", notebookId, "sources"],
    queryFn: () => listNotebookSources(notebookId),
    enabled: enabled && Boolean(notebookId),
    refetchInterval: (query) => {
      const documents = query.state.data ?? [];
      return documents.some((document) => document.status === "processing") ? 2500 : false;
    }
  });
}

export function useNotebookSourcesFilteredQuery(
  notebookId: string,
  filters: { type?: string[]; status?: string[]; from?: string; to?: string; q?: string },
  enabled = true
) {
  return useQuery({
    queryKey: ["notebooks", notebookId, "sources", "filtered", filters],
    queryFn: () => listNotebookSourcesFiltered(notebookId, filters),
    enabled: enabled && Boolean(notebookId)
  });
}

export function useNotebookSourcesSearchQuery(notebookId: string, query: string, enabled = true) {
  return useQuery({
    queryKey: ["notebooks", notebookId, "sources", "search", query],
    queryFn: () => searchNotebookSources(notebookId, query),
    enabled: enabled && Boolean(notebookId) && Boolean(query.trim())
  });
}

export function useNotebookSourceQuery(notebookId: string, sourceId: string, enabled = true) {
  return useQuery({
    queryKey: ["notebooks", notebookId, "sources", sourceId],
    queryFn: () => getNotebookSource(notebookId, sourceId),
    enabled: enabled && Boolean(notebookId) && Boolean(sourceId)
  });
}

export function useSourceChunksQuery(notebookId: string, sourceId: string, limit = 50, offset = 0, enabled = true) {
  return useQuery({
    queryKey: ["notebooks", notebookId, "sources", sourceId, "chunks", limit, offset],
    queryFn: () => getSourceChunks(notebookId, sourceId, { limit, offset }),
    enabled: enabled && Boolean(notebookId) && Boolean(sourceId)
  });
}

export function useNotebookSessionsQuery(notebookId: string, enabled = true) {
  return useQuery({
    queryKey: ["notebooks", notebookId, "sessions"],
    queryFn: () => listNotebookSessions(notebookId),
    enabled: enabled && Boolean(notebookId)
  });
}

export function useNotebookMessagesQuery(notebookId: string, sessionId: string, sourceMap: SourceMapContext, enabled = true) {
  return useQuery({
    queryKey: ["notebooks", notebookId, "sessions", sessionId, "messages"],
    queryFn: () => listNotebookMessages(notebookId, sessionId, sourceMap),
    enabled: enabled && Boolean(notebookId) && Boolean(sessionId)
  });
}

export function useChatSearchQuery(notebookId: string, query: string, enabled = true) {
  return useQuery({
    queryKey: ["notebooks", notebookId, "chat", "search", query],
    queryFn: () => searchNotebookMessages(notebookId, query),
    enabled: enabled && Boolean(notebookId) && Boolean(query.trim())
  });
}

export function useNotebookUsageQuery(notebookId: string, enabled = true) {
  return useQuery({
    queryKey: ["notebooks", notebookId, "usage"],
    queryFn: () => getNotebookUsage(notebookId),
    enabled: enabled && Boolean(notebookId)
  });
}

export function useNotebookPodcastsQuery(notebookId: string, enabled = true) {
  return useQuery({
    queryKey: ["notebooks", notebookId, "podcasts"],
    queryFn: () => listNotebookPodcasts(notebookId),
    enabled: enabled && Boolean(notebookId),
    refetchInterval: (query) => {
      const podcasts = query.state.data ?? [];
      return podcasts.some((podcast) => podcast.status === "queued" || podcast.status === "processing") ? 3000 : false;
    }
  });
}

export function useJobQuery(jobId: string | null, enabled = true) {
  return useQuery({
    queryKey: ["jobs", jobId],
    queryFn: () => getJob(jobId ?? ""),
    enabled: enabled && Boolean(jobId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "running" ? 2000 : false;
    }
  });
}

export function useAuthMutations() {
  return {
    login: useMutation({ mutationFn: login }),
    register: useMutation({ mutationFn: register }),
    exchangeGoogleCode: useMutation({ mutationFn: exchangeGoogleCode }),
    startGoogleAuth: useMutation({ mutationFn: startGoogleAuth }),
    logout: useMutation({ mutationFn: logout })
  };
}

export function useNotebookMutations() {
  const queryClient = useQueryClient();
  return {
    createNotebook: useMutation({
      mutationFn: createNotebook,
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["notebooks"] });
      }
    }),
    updateNotebook: useMutation({
      mutationFn: ({ notebookId, title, description }: { notebookId: string; title: string; description?: string }) =>
        updateNotebook(notebookId, { title, description }),
      onSuccess: async (_, variables) => {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ["notebooks"] }),
          queryClient.invalidateQueries({ queryKey: ["notebooks", variables.notebookId] })
        ]);
      }
    }),
    deleteNotebook: useMutation({
      mutationFn: deleteNotebook,
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["notebooks"] });
      }
    })
  };
}

export function useSourceMutations(notebookId: string) {
  const queryClient = useQueryClient();
  async function invalidateSourceQueries(sourceId?: string): Promise<void> {
    const tasks = [
      queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "sources"] }),
      queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "podcasts"] })
    ];
    if (sourceId) {
      tasks.push(queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "sources", sourceId] }));
      tasks.push(queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "sources", sourceId, "chunks"] }));
    }
    await Promise.all(tasks);
  }

  return {
    uploadSource: useMutation({
      mutationFn: (file: File) => uploadNotebookSource(notebookId, file),
      onSuccess: async () => {
        await invalidateSourceQueries();
      }
    }),
    ingestUrl: useMutation({
      mutationFn: (payload: UrlIngestPayload) => ingestNotebookUrl(notebookId, payload),
      onSuccess: async () => {
        await invalidateSourceQueries();
      }
    }),
    deleteSource: useMutation({
      mutationFn: (sourceId: string) => deleteNotebookSource(notebookId, sourceId),
      onSuccess: async (_, sourceId) => {
        await invalidateSourceQueries(sourceId);
      }
    }),
    cancelJob: useMutation({ mutationFn: cancelJob })
  };
}

export function useChatMutations(notebookId: string, sourceMap: SourceMapContext) {
  const queryClient = useQueryClient();
  return {
    createSession: useMutation({
      mutationFn: (title: string) => createNotebookSession(notebookId, title),
      onSuccess: async (session: ChatSession) => {
        await queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "sessions"] });
        queryClient.setQueryData(["notebooks", notebookId, "sessions", session.id, "messages"], []);
      }
    }),
    sendMessage: useMutation({
      mutationFn: ({ sessionId, message, sourceIds, onToken }: { sessionId: string; message: string; sourceIds: string[]; onToken?: (token: string) => void }) =>
        streamNotebookMessage(notebookId, sessionId, { message, sourceIds }, sourceMap, { onToken }),
      onSuccess: async (_, variables) => {
        await queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "sessions", variables.sessionId, "messages"] });
        await queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "sessions"] });
      }
    })
  };
}

export function useExportMutation(notebookId: string) {
  return useMutation({
    mutationFn: ({
      sessionId,
      format,
      context
    }: {
      sessionId: string;
      format: "md" | "pdf";
      context?: {
        topK?: number;
        similarityThreshold?: number;
        model?: string;
        memoryEnabled?: boolean;
        attachedSourceIds?: string[];
      };
    }) => exportNotebookSession(notebookId, sessionId, format, context)
  });
}

export function usePodcastMutations(notebookId: string) {
  const queryClient = useQueryClient();
  return {
    createPodcast: useMutation({
      mutationFn: ({ sourceIds, title, voice }: { sourceIds: string[]; title: string; voice?: VoiceOption }) =>
        createNotebookPodcast(notebookId, { sourceIds, title, voice }),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "podcasts"] });
      }
    }),
    retryPodcast: useMutation({
      mutationFn: ({ podcastId, title, voice }: { podcastId: string; title: string; voice?: VoiceOption }) =>
        retryNotebookPodcast(notebookId, podcastId, title, voice),
      onSuccess: async () => {
        await queryClient.invalidateQueries({ queryKey: ["notebooks", notebookId, "podcasts"] });
      }
    })
  };
}

export type AuthMutationBundle = ReturnType<typeof useAuthMutations>;
