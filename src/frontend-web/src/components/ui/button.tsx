import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-xl text-sm font-semibold transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-[color:var(--button-primary-bg)] text-[color:var(--button-primary-text)] shadow-soft-card hover:bg-[color:var(--button-primary-hover)]",
        secondary: "bg-[color:var(--button-secondary-bg)] text-[color:var(--button-secondary-text)] shadow-inset hover:bg-[color:var(--button-secondary-hover)]",
        ghost: "bg-transparent text-foreground hover:bg-[color:var(--button-ghost-hover)]",
        outline: "border border-[color:var(--input-border)] bg-[color:var(--surface-2)] text-card-foreground shadow-inset hover:border-[color:var(--panel-border-strong)] hover:bg-[color:var(--surface-3)]"
      },
      size: {
        default: "h-11 px-4 py-2",
        sm: "h-9 rounded-lg px-3 text-xs",
        lg: "h-12 rounded-2xl px-6"
      }
    },
    defaultVariants: {
      variant: "default",
      size: "default"
    }
  }
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />;
  }
);

Button.displayName = "Button";
