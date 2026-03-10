import { Mic2, RadioTower, RotateCcw } from "lucide-react";
import type { PodcastGenerationPhase, PodcastResult, SourceDocument, VoiceOption } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { WaveformVisualizer } from "@/components/studio/WaveformVisualizer";
import { cn } from "@/lib/utils";

type PodcastStudioProps = {
  documents: SourceDocument[];
  selectedDocumentIds: string[];
  selectedVoice: VoiceOption;
  podcastScript: string;
  podcastAudioUrl: string | null;
  waveform: number[];
  phase: PodcastGenerationPhase;
  podcasts: PodcastResult[];
  isGenerating: boolean;
  onSelectVoice: (voice: VoiceOption) => void;
  onGenerate: () => Promise<void>;
  onRetry: (podcastId: string) => Promise<void>;
};

const voices: Array<{ value: VoiceOption; label: string; description: string }> = [
  { value: "Alloy Host", label: "Alloy Host", description: "Warm presenter for everyday notebook recaps." },
  { value: "Verse Analyst", label: "Verse Analyst", description: "Sharper analytical tone for dense material." },
  { value: "Nova Narrator", label: "Nova Narrator", description: "Long-form storyteller voice for polished scripts." }
];

export function PodcastStudio({
  documents,
  selectedDocumentIds,
  selectedVoice,
  podcastScript,
  podcastAudioUrl,
  waveform,
  phase,
  podcasts,
  isGenerating,
  onSelectVoice,
  onGenerate,
  onRetry
}: PodcastStudioProps): JSX.Element {
  const activeTitles = documents.filter((document) => selectedDocumentIds.includes(document.id)).map((document) => document.title);

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        {voices.map((voice) => (
          <button
            key={voice.value}
            className={cn(
              "w-full rounded-2xl border p-3 text-left transition",
              selectedVoice === voice.value
                ? "border-[color:var(--panel-border-strong)] bg-[color:var(--surface-3)]"
                : "border-[color:var(--panel-border)] bg-[color:var(--surface-2)] hover:border-[color:var(--panel-border-strong)]"
            )}
            onClick={() => onSelectVoice(voice.value)}
            type="button"
          >
            <div className="flex items-start gap-2.5">
              <div className="grid h-9 w-9 place-items-center rounded-lg bg-[color:var(--surface-3)] text-[color:var(--text-primary)]">
                <Mic2 className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-[color:var(--text-primary)]">{voice.label}</p>
                <p className="mt-1 text-sm leading-6 text-[color:var(--text-muted)]">{voice.description}</p>
              </div>
            </div>
          </button>
        ))}
      </div>

      <div className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4 text-sm text-[color:var(--text-primary)]">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[color:var(--text-kicker)]">Source mix</p>
        <p className="mt-2 leading-6">{activeTitles.join(", ") || "Attach sources from the gallery to generate a podcast script."}</p>
      </div>

      <WaveformVisualizer bars={waveform} isActive={isGenerating} />

      <Button className="w-full" disabled={!selectedDocumentIds.length || isGenerating} onClick={() => void onGenerate()}>
        <RadioTower className="h-4 w-4" />
        {isGenerating ? `Generating (${phase})` : "Generate podcast"}
      </Button>

      <div className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4">
        <p className="text-[11px] uppercase tracking-[0.22em] text-[color:var(--text-kicker)]">Latest output</p>
        <p className="mt-2 text-sm leading-7 text-[color:var(--text-primary)]">
          {podcastScript || "The latest script and rendered audio will appear here."}
        </p>
        {podcastAudioUrl ? <audio aria-label="Generated podcast audio" className="mt-3 w-full" controls src={podcastAudioUrl} /> : null}
      </div>

      <div className="space-y-2">
        {podcasts.map((podcast) => (
          <div key={podcast.id} className="rounded-xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-3">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-[color:var(--text-primary)]">{podcast.status}</p>
                <p className="text-xs text-[color:var(--text-kicker)]">{podcast.durationLabel}</p>
              </div>
              {podcast.status === "failed" ? (
                <Button size="sm" variant="outline" onClick={() => void onRetry(podcast.id)}>
                  <RotateCcw className="h-4 w-4" />
                  Retry
                </Button>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
