import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type WaveformVisualizerProps = {
  bars: number[];
  isActive: boolean;
};

export function WaveformVisualizer({ bars, isActive }: WaveformVisualizerProps): JSX.Element {
  const waveform = bars.length ? bars : [16, 24, 38, 14, 28, 34, 20, 17, 29, 41, 18, 32, 24, 36];
  return (
    <div className="flex h-24 items-end gap-1 rounded-[1.4rem] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] px-4 py-4">
      {waveform.map((height, index) => (
        <motion.span
          key={`${index}-${height}`}
          animate={isActive ? { height: [`${Math.max(12, height - 8)}%`, `${height}%`, `${Math.max(16, height + 8)}%`] } : { height: `${height}%` }}
          className={cn("w-full rounded-full bg-gradient-to-t from-[color:var(--waveform-a)] via-[color:var(--waveform-b)] to-[color:var(--waveform-c)]")}
          style={{ maxWidth: 10 }}
          transition={{ duration: 1.8, repeat: isActive ? Infinity : 0, delay: index * 0.05, repeatType: "mirror" }}
        />
      ))}
    </div>
  );
}
