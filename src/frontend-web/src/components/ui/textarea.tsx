import * as React from "react";
import { cn } from "@/lib/utils";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "min-h-[120px] w-full rounded-2xl border border-[color:var(--input-border)] bg-[color:var(--input-bg)] px-4 py-3 text-sm leading-7 text-foreground shadow-inset ring-offset-background transition placeholder:text-muted-foreground/80 focus-visible:border-[color:var(--focus-border)] focus-visible:bg-[color:var(--input-focus-bg)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--focus-ring)]",
        className
      )}
      {...props}
    />
  )
);

Textarea.displayName = "Textarea";
