import { useEffect } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, X } from "lucide-react";
import { Button } from "@/components/ui/button";

type ConfirmDialogProps = {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  cancelLabel?: string;
  isPending?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  cancelLabel = "Cancel",
  isPending = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps): JSX.Element | null {
  useEffect(() => {
    if (!open) {
      return;
    }
    function handleKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape" && !isPending) {
        onCancel();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isPending, onCancel, open]);

  if (!open || typeof document === "undefined") {
    return null;
  }

  return createPortal(
    <div className="fixed inset-0 z-[90] flex items-center justify-center bg-[rgba(16,19,17,0.48)] px-4 py-6 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-[28px] border border-[color:var(--panel-border)] bg-[color:var(--surface-1)] p-6 shadow-panel">
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="rounded-2xl border border-[rgba(191,97,106,0.25)] bg-[rgba(191,97,106,0.12)] p-2.5 text-[rgb(163,55,65)]">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.24em] text-[color:var(--text-kicker)]">Confirm action</p>
              <h2 className="mt-2 text-xl font-semibold text-[color:var(--text-hero)]">{title}</h2>
              <p className="mt-3 text-sm leading-6 text-[color:var(--text-muted)]">{description}</p>
            </div>
          </div>
          <button
            aria-label="Close confirmation dialog"
            className="rounded-xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-2 text-[color:var(--text-muted)] transition hover:text-[color:var(--text-primary)]"
            disabled={isPending}
            onClick={onCancel}
            type="button"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <Button disabled={isPending} variant="outline" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button
            className="bg-[rgb(150,88,39)] text-white hover:bg-[rgb(126,72,31)]"
            disabled={isPending}
            onClick={onConfirm}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
