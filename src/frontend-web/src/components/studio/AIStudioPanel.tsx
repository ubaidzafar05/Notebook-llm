import { BookOpenText, SlidersHorizontal, Sparkles } from "lucide-react";
import type { ChatSearchResult, InsightSnapshot, ModelOption, NotebookUsage, PodcastGenerationPhase, PodcastResult, SourceDocument, VoiceOption } from "@/lib/api";
import type { StudioTab } from "@/store/use-workspace-store";
import { PanelShell } from "@/components/layout/PanelShell";
import { PodcastStudio } from "@/components/studio/PodcastStudio";
import { InsightEnginePanel } from "@/components/studio/InsightEnginePanel";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

type AIStudioPanelProps = {
  documents: SourceDocument[];
  selectedDocumentIds: string[];
  insight: InsightSnapshot;
  usage: NotebookUsage | null;
  historyQuery: string;
  historyResults: ChatSearchResult[];
  historyLoading: boolean;
  sessionSummary: string | null;
  onOpenHistoryResult: (sessionId: string) => void;
  podcasts: PodcastResult[];
  chatSettings: {
    topK: number;
    similarityThreshold: number;
    model: ModelOption;
    memoryEnabled: boolean;
  };
  selectedVoice: VoiceOption;
  podcastScript: string;
  podcastAudioUrl: string | null;
  waveform: number[];
  podcastPhase: PodcastGenerationPhase;
  isGeneratingPodcast: boolean;
  activeTab: StudioTab;
  onTabChange: (tab: StudioTab) => void;
  onUpdateChatSettings: (patch: { topK?: number; similarityThreshold?: number; model?: ModelOption; memoryEnabled?: boolean }) => void;
  onSelectVoice: (voice: VoiceOption) => void;
  onGeneratePodcast: () => Promise<void>;
  onRetryPodcast: (podcastId: string) => Promise<void>;
};

export function AIStudioPanel({
  documents,
  selectedDocumentIds,
  insight,
  usage,
  historyQuery,
  historyResults,
  historyLoading,
  sessionSummary,
  onOpenHistoryResult,
  podcasts,
  chatSettings,
  selectedVoice,
  podcastScript,
  podcastAudioUrl,
  waveform,
  podcastPhase,
  isGeneratingPodcast,
  activeTab,
  onTabChange,
  onUpdateChatSettings,
  onSelectVoice,
  onGeneratePodcast,
  onRetryPodcast,
}: AIStudioPanelProps): JSX.Element {
  return (
    <PanelShell className="flex h-full min-h-0 flex-col p-5">
      {/* Header */}
      <div className="mb-4 flex items-start gap-2.5">
        <div className="rounded-xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-2.5 text-[color:var(--panel-icon)]">
          <Sparkles className="h-4.5 w-4.5" />
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-[0.26em] text-[color:var(--text-kicker)]">Studio</p>
          <h2 className="mt-1 text-lg font-semibold text-[color:var(--text-hero)]">Creative console</h2>
          <p className="mt-1 text-sm text-[color:var(--text-muted)]">
            Tune retrieval, draft audio, and inspect notebook outputs.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <Tabs className="min-h-0 flex-1" value={activeTab} onValueChange={(value) => onTabChange(value as StudioTab)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="chat">Chat</TabsTrigger>
          <TabsTrigger value="podcast">Podcast</TabsTrigger>
          <TabsTrigger value="insight">Insights</TabsTrigger>
        </TabsList>

        {/* Chat settings */}
        <TabsContent className="space-y-4 pt-1" value="chat">
          <div className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4">
            <p className="text-[10px] uppercase tracking-[0.24em] text-[color:var(--text-kicker)]">Session summary</p>
            <p className="mt-2 text-sm text-[color:var(--text-muted)]">
              {sessionSummary ?? "A summary appears after a few exchanges."}
            </p>
          </div>

          <div className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-[color:var(--text-primary)]">
                <SlidersHorizontal className="h-4 w-4 text-[color:var(--accent-soft)]" />
                <span className="text-sm font-medium">Retrieval depth</span>
              </div>
              <Badge>{chatSettings.topK}</Badge>
            </div>
            <Slider
              max={12}
              min={2}
              step={1}
              value={[chatSettings.topK]}
              onValueChange={(value) => onUpdateChatSettings({ topK: value[0] ?? chatSettings.topK })}
            />
          </div>

          <div className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-[color:var(--text-primary)]">
                <BookOpenText className="h-4 w-4 text-[color:var(--accent-soft)]" />
                <span className="text-sm font-medium">Similarity threshold</span>
              </div>
              <Badge>{chatSettings.similarityThreshold.toFixed(2)}</Badge>
            </div>
            <Slider
              max={0.95}
              min={0.45}
              step={0.01}
              value={[chatSettings.similarityThreshold]}
              onValueChange={(value) =>
                onUpdateChatSettings({ similarityThreshold: value[0] ?? chatSettings.similarityThreshold })
              }
            />
          </div>

          <div className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4">
            <p className="text-[10px] uppercase tracking-[0.24em] text-[color:var(--text-kicker)]">Model</p>
            <Select
              value={chatSettings.model}
              onValueChange={(value) => onUpdateChatSettings({ model: value as ModelOption })}
            >
              <SelectTrigger className="mt-2.5">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ollama/qwen3:8b">ollama/qwen3:8b</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4">
            <div>
              <p className="text-sm font-semibold text-[color:var(--text-primary)]">Notebook memory</p>
              <p className="mt-1 text-sm text-[color:var(--text-muted)]">
                Keep recent context while staying source-grounded.
              </p>
            </div>
            <Switch
              checked={chatSettings.memoryEnabled}
              onCheckedChange={(checked) => onUpdateChatSettings({ memoryEnabled: checked })}
            />
          </div>
        </TabsContent>

        {/* Podcast */}
        <TabsContent value="podcast">
          <PodcastStudio
            documents={documents}
            isGenerating={isGeneratingPodcast}
            onGenerate={onGeneratePodcast}
            onRetry={onRetryPodcast}
            onSelectVoice={onSelectVoice}
            phase={podcastPhase}
            podcastAudioUrl={podcastAudioUrl}
            podcastScript={podcastScript}
            podcasts={podcasts}
            selectedDocumentIds={selectedDocumentIds}
            selectedVoice={selectedVoice}
            waveform={waveform}
          />
        </TabsContent>

        {/* Insights */}
        <TabsContent value="insight">
          <div className="space-y-4">
            <InsightEnginePanel insight={insight} />
            {usage ? (
              <div className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4">
                <p className="text-[10px] uppercase tracking-[0.24em] text-[color:var(--text-kicker)]">Usage</p>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] p-3 text-sm">
                    <p className="text-xs text-[color:var(--text-muted)]">Messages</p>
                    <p className="mt-1 text-lg font-semibold text-[color:var(--text-primary)]">{usage.totalMessages}</p>
                  </div>
                  <div className="rounded-xl border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] p-3 text-sm">
                    <p className="text-xs text-[color:var(--text-muted)]">Sources</p>
                    <p className="mt-1 text-lg font-semibold text-[color:var(--text-primary)]">{usage.totalSources}</p>
                  </div>
                  <div className="rounded-xl border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] p-3 text-sm">
                    <p className="text-xs text-[color:var(--text-muted)]">Prompt tokens (est)</p>
                    <p className="mt-1 text-lg font-semibold text-[color:var(--text-primary)]">{usage.totalPromptTokensEst}</p>
                  </div>
                  <div className="rounded-xl border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] p-3 text-sm">
                    <p className="text-xs text-[color:var(--text-muted)]">Response tokens (est)</p>
                    <p className="mt-1 text-lg font-semibold text-[color:var(--text-primary)]">{usage.totalResponseTokensEst}</p>
                  </div>
                </div>
                <div className="mt-3 text-xs text-[color:var(--text-muted)]">
                  Estimated cost: ${usage.estimatedCostUsd.toFixed(2)}
                </div>
              </div>
            ) : null}

            <div className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4">
              <p className="text-[10px] uppercase tracking-[0.24em] text-[color:var(--text-kicker)]">Chat history search</p>
              <p className="mt-2 text-sm text-[color:var(--text-muted)]">
                {historyQuery ? `Results for "${historyQuery}"` : "Use the top search bar to query chat history."}
              </p>
              <div className="mt-3 space-y-2">
                {historyLoading ? (
                  <p className="text-sm text-[color:var(--text-muted)]">Searching…</p>
                ) : historyResults.length ? (
                  historyResults.slice(0, 6).map((result) => (
                    <button
                      key={result.id}
                      className="w-full rounded-xl border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] p-3 text-left text-sm text-[color:var(--text-primary)]"
                      type="button"
                      onClick={() => onOpenHistoryResult(result.sessionId)}
                    >
                      <p className="line-clamp-2">{result.content}</p>
                      <p className="mt-1 text-xs text-[color:var(--text-muted)]">{new Date(result.createdAt).toLocaleString()}</p>
                    </button>
                  ))
                ) : historyQuery ? (
                  <p className="text-sm text-[color:var(--text-muted)]">No matches found.</p>
                ) : null}
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </PanelShell>
  );
}
