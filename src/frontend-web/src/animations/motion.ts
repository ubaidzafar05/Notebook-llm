import type { Transition, Variants } from "framer-motion";

// ── Spring presets ──────────────────────────────────────────
// Event-driven springs only. No infinite pulsing.

export const springs = {
  /** Panels, cards, and overlays entering the viewport */
  panelMaterialize: { type: "spring", stiffness: 120, damping: 16, mass: 0.9 } satisfies Transition,
  /** Hover lift on source cards and buttons */
  cardHover: { type: "spring", stiffness: 180, damping: 14, mass: 0.6 } satisfies Transition,
  /** Studio slide-over open/close */
  studioSlide: { type: "spring", stiffness: 210, damping: 24, mass: 0.72 } satisfies Transition,
  /** Gallery rail expand/collapse */
  galleryToggle: { type: "spring", stiffness: 200, damping: 22, mass: 0.7 } satisfies Transition,
  /** Answer appearing after streaming completes */
  answerAppear: { type: "spring", stiffness: 100, damping: 18, mass: 1.0 } satisfies Transition,
  /** Prompt send pulse */
  sendPulse: { type: "spring", stiffness: 300, damping: 20, mass: 0.5 } satisfies Transition,
  /** Upload dropzone hover feedback */
  uploadFeedback: { type: "spring", stiffness: 160, damping: 16, mass: 0.65 } satisfies Transition,
};

// ── Variant sets ────────────────────────────────────────────

export const fadeUp: Variants = {
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0, transition: springs.panelMaterialize },
};

export const scaleIn: Variants = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1, transition: springs.answerAppear },
};

export const slideInRight: Variants = {
  initial: { x: 40, opacity: 0 },
  animate: { x: 0, opacity: 1, transition: springs.studioSlide },
  exit: { x: 40, opacity: 0, transition: { duration: 0.18 } },
};
