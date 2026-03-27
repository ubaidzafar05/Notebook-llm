import * as React from "react";
import { cn } from "@/lib/utils";

type SliderProps = Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "defaultValue" | "onChange"> & {
  value?: number[];
  defaultValue?: number[];
  onValueChange?: (value: number[]) => void;
};

export const Slider = React.forwardRef<HTMLInputElement, SliderProps>(
  ({ className, value, defaultValue, min = 0, max = 100, step = 1, onValueChange, ...props }, ref) => {
    const currentValue = value?.[0] ?? defaultValue?.[0] ?? Number(min);
    return (
      <input
        ref={ref}
        className={cn("h-2 w-full cursor-pointer accent-[color:var(--accent-soft)]", className)}
        max={max}
        min={min}
        step={step}
        type="range"
        value={currentValue}
        onChange={(event) => onValueChange?.([Number(event.target.value)])}
        {...props}
      />
    );
  }
);

Slider.displayName = "Slider";
