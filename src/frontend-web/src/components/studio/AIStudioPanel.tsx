import { BookOpenText, SlidersHorizontal, Sparkles } from "lucide-react";
import type { InsightSnapshot, ModelOption, PodcastGenerationPhase, PodcastResult, SourceDocument, VoiceOption } from "@/lib/api";
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
                <SelectItem value="openrouter/claude-3.7-sonnet">openrouter/claude-3.7-sonnet</SelectItem>
                <SelectItem value="openrouter/gpt-4.1-mini">openrouter/gpt-4.1-mini</SelectItem>
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
          <InsightEnginePanel insight={insight} />
        </TabsContent>
      </Tabs>
    </PanelShell>
  );
}
