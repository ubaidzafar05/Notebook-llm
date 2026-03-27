import type { PropsWithChildren, ReactNode } from "react";
import { PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { springs } from "@/animations/motion";
import { cn } from "@/lib/utils";

type WorkspaceShellProps = PropsWithChildren<{
  left: ReactNode;
  right: ReactNode;
  studioOpen: boolean;
  galleryCollapsed: boolean;
  onCloseStudio: () => void;
  onToggleGallery: () => void;
}>;

export function WorkspaceShell({
  left,
  right,
  children,
  studioOpen,
  galleryCollapsed,
  onCloseStudio,
  onToggleGallery,
}: WorkspaceShellProps): JSX.Element {
  return (
    <>
      <div className="fixed left-4 top-[92px] z-40 hidden xl:block">
        <Button
          aria-label={galleryCollapsed ? "Expand source gallery" : "Collapse source gallery"}
          className="shadow-soft-card"
          size="sm"
          variant="outline"
          onClick={onToggleGallery}
        >
          {galleryCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </Button>
      </div>

      <main className="mx-auto w-full max-w-[1760px] px-4 pb-8 pt-5 sm:px-6 lg:pb-10">
        <div className="flex items-start gap-4">
          <section className="min-w-0 flex-1">
            <div className="mx-auto max-w-[var(--answer-board-max-width)] xl:pl-10">{children}</div>
          </section>
        </div>

        <div className="mt-6 xl:hidden">{left}</div>
      </main>

      <aside
        aria-label="Source gallery"
        className={cn(
          "fixed inset-y-0 left-0 z-30 hidden w-[calc(var(--gallery-rail-width)+2rem)] px-4 pb-6 pt-[80px] transition-[transform,opacity] duration-300 ease-out xl:block",
          galleryCollapsed
            ? "pointer-events-none translate-x-[calc(-1*(var(--gallery-rail-width)+2rem))] opacity-0"
            : "translate-x-0 opacity-100"
        )}
        style={{ willChange: "transform" }}
      >
        <div className="h-[calc(100vh-92px)] min-w-[280px] overflow-hidden">{left}</div>
      </aside>

      {/* Studio overlay */}
      <AnimatePresence>
        {studioOpen ? (
          <motion.button
            aria-label="Close studio panel"
            className="fixed inset-0 z-30 bg-[color:var(--studio-overlay)]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            type="button"
            onClick={onCloseStudio}
          />
        ) : null}
      </AnimatePresence>

      {/* Studio slide-over */}
      <motion.aside
        aria-label="Studio panel"
        className={cn(
          "fixed right-0 top-0 z-40 h-screen w-full max-w-[var(--studio-panel-width)] px-3 pb-3 pt-[72px] sm:px-4 sm:pb-4 lg:pt-[86px]",
          !studioOpen && "pointer-events-none"
        )}
        initial={false}
        animate={{ x: studioOpen ? 0 : 500 }}
        transition={springs.studioSlide}
      >
        <div className="flex h-full flex-col gap-2">
          <div className="flex justify-end">
            <Button aria-label="Close studio" size="sm" variant="outline" onClick={onCloseStudio}>
              <X className="h-4 w-4" />
              Close
            </Button>
          </div>
          <div className="min-h-0 flex-1 overflow-hidden">{studioOpen ? right : null}</div>
        </div>
      </motion.aside>
    </>
  );
}
