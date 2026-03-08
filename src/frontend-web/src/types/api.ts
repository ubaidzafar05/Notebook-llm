export type ApiEnvelope<T> = {
  data: T | null;
  error: ApiErrorBody | null;
  meta: { request_id: string };
};

export type ApiErrorBody = {
  code: string;
  message: string;
  details?: unknown;
};

export type AuthUser = {
  id: string;
  email: string;
};

export type AuthPayload = {
  user: AuthUser;
  access_token: string;
  token_type: string;
};

export type Notebook = {
  id: string;
  title: string;
  description: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};

export type Source = {
  id: string;
  notebook_id?: string;
  name: string;
  source_type: string;
  status: string;
  path_or_url: string;
  metadata: Record<string, unknown>;
};

export type SourceChunk = {
  chunk_id: string;
  chunk_index: number;
  excerpt: string;
  citation: Record<string, unknown>;
};

export type SourceChunksPayload = {
  source_id: string;
  limit: number;
  offset: number;
  chunks: SourceChunk[];
};

export type ChatSession = {
  id: string;
  notebook_id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type Citation = {
  source_id: string;
  chunk_id: string;
  excerpt: string;
  page_number?: number | null;
  start_timestamp?: number | null;
  end_timestamp?: number | null;
  speaker?: string | null;
  section_path?: string | null;
  section_heading?: string | null;
  paragraph_index?: number | null;
  url?: string | null;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  model_info: Record<string, string>;
  created_at: string;
};

export type StreamEvent =
  | { type: "token"; value: string }
  | {
      type: "final";
      content: string;
      citations: Citation[];
      model_info: Record<string, string>;
      confidence: "low" | "medium" | "high";
    };

export type MemorySummary = {
  session_id: string;
  summary: string;
  provider: string;
};

export type Podcast = {
  id: string;
  notebook_id: string | null;
  source_ids: string[];
  status: string;
  output_path: string | null;
  duration_ms: number | null;
  error_message: string | null;
  failure_code: string | null;
  failure_detail: string | null;
  retried_from_podcast_id: string | null;
  created_at: string;
  updated_at: string;
};

export type DependencyHealth = Record<
  string,
  { status: string; detail: string; latency_ms: number | null }
>;
