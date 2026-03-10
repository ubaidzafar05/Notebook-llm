import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, ...props }, ref) => (
  <input
    ref={ref}
    className={cn(
      "flex h-11 w-full rounded-2xl border border-[color:var(--input-border)] bg-[color:var(--input-bg)] px-4 py-2 text-sm text-foreground shadow-inset ring-offset-background transition placeholder:text-muted-foreground/80 focus-visible:border-[color:var(--focus-border)] focus-visible:bg-[color:var(--input-focus-bg)] focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[color:var(--focus-ring)]",
      className
    )}
    {...props}
  />
));

Input.displayName = "Input";
