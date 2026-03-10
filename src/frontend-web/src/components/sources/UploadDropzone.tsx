import { Link2, Upload, Youtube } from "lucide-react";
import { useRef, useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type UploadDropzoneProps = {
  isUploading: boolean;
  onUploadFile: (file: File) => Promise<void>;
  onIngestUrl: (payload: { url: string; sourceType: "website" | "youtube" }) => Promise<void>;
};

export function UploadDropzone({ isUploading, onUploadFile, onIngestUrl }: UploadDropzoneProps): JSX.Element {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [urlValue, setUrlValue] = useState("");

  async function handleFiles(files: FileList | null): Promise<void> {
    const file = files?.[0];
    if (!file) {
      return;
    }
    await onUploadFile(file);
  }

  async function submitUrl(sourceType: "website" | "youtube"): Promise<void> {
    const url = urlValue.trim();
    if (!url) {
      return;
    }
    await onIngestUrl({ url, sourceType });
    setUrlValue("");
  }

  return (
    <div className="space-y-3 rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4">
      <motion.button
        type="button"
        className="group relative flex w-full flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-[color:var(--panel-border-strong)] bg-[color:var(--surface-3)] px-4 py-8 text-center transition"
        onClick={() => fileInputRef.current?.click()}
        onDrop={(event) => {
          event.preventDefault();
          void handleFiles(event.dataTransfer.files);
        }}
        onDragOver={(event) => event.preventDefault()}
        whileHover={{ y: -1 }}
      >
        <div className="grid h-12 w-12 place-items-center rounded-xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)]">
          <Upload className="h-5 w-5 text-[color:var(--text-primary)]" />
        </div>
        <div>
          <p className="text-sm font-semibold text-[color:var(--text-primary)]">Add a source</p>
          <p className="mt-1 text-sm text-[color:var(--text-muted)]">Drop PDF, TXT, or audio files, or click to browse.</p>
        </div>
        {isUploading ? <span className="text-xs font-medium text-[color:var(--accent-soft)]">Uploading...</span> : null}
        <input
          ref={fileInputRef}
          accept=".pdf,.txt,.md,.mp3,.wav,.m4a"
          className="hidden"
          type="file"
          onChange={(event) => void handleFiles(event.target.files)}
        />
      </motion.button>

      <div className="relative">
        <Link2 className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--text-kicker)]" />
        <Input
          aria-label="Source URL"
          className="pl-9"
          placeholder="Paste a website or YouTube link"
          value={urlValue}
          onChange={(event) => setUrlValue(event.target.value)}
        />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Button disabled={isUploading} variant="secondary" onClick={() => void submitUrl("website")}>
          <Link2 className="h-4 w-4" />
          Website
        </Button>
        <Button disabled={isUploading} variant="secondary" onClick={() => void submitUrl("youtube")}>
          <Youtube className="h-4 w-4" />
          YouTube
        </Button>
      </div>
    </div>
  );
}
