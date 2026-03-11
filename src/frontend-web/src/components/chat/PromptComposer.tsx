import { AtSign, CornerDownLeft, Mic, PenLine } from "lucide-react";
import type { KeyboardEvent } from "react";
import { motion } from "framer-motion";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { springs } from "@/animations/motion";
import { useSpeechInput } from "@/hooks/use-speech-input";

type PromptComposerProps = {
  draftPrompt: string;
  attachedCount: number;
  isSending: boolean;
  onChange: (value: string) => void;
  onSubmit: () => Promise<void>;
};

export function PromptComposer({ draftPrompt, attachedCount, isSending, onChange, onSubmit }: PromptComposerProps): JSX.Element {
  const speech = useSpeechInput((text) => {
    const next = draftPrompt ? `${draftPrompt} ${text}` : text;
    onChange(next);
  });

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>): void {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      void onSubmit();
    }
  }

  return (
    <div className="rounded-3xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-5">
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-[color:var(--text-muted)]">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] px-2.5 py-1 text-[color:var(--text-primary)]">
          <AtSign className="h-3.5 w-3.5 text-[color:var(--accent-soft)]" />
          {attachedCount} attached
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--panel-border)] bg-[color:var(--surface-3)] px-2.5 py-1">
          <CornerDownLeft className="h-3.5 w-3.5" />
          Cmd/Ctrl+Enter
        </span>
      </div>

      <Textarea
        aria-label="Prompt composer"
        id="prompt-composer-input"
        className="min-h-[120px] resize-none rounded-xl"
        placeholder="Ask for a summary, compare contradictions, extract action items, or request a podcast script."
        value={draftPrompt}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
      />

      {speech.error ? (
        <p className="mt-3 text-xs text-[color:hsl(var(--destructive))]">{speech.error}</p>
      ) : null}

      <div className="mt-3 flex items-center justify-between">
        <Button
          size="sm"
          type="button"
          variant="outline"
          disabled={!speech.supported}
          onClick={() => (speech.listening ? speech.stop() : speech.start())}
        >
          <Mic className="h-4 w-4" />
          {speech.listening ? "Listening..." : "Voice"}
        </Button>
        <motion.div whileTap={{ scale: 0.96 }} transition={springs.sendPulse}>
          <Button disabled={!draftPrompt.trim() || isSending} onClick={() => void onSubmit()}>
            <PenLine className="h-4 w-4" />
            {isSending ? "Sending..." : "Ask"}
          </Button>
        </motion.div>
      </div>
    </div>
  );
}
