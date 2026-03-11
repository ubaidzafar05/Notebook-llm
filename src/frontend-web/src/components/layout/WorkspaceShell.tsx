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
      <main className="mx-auto w-full max-w-[1760px] px-4 pb-8 pt-5 sm:px-6 lg:pb-10">
        <div
          className="grid items-start gap-6"
          style={{
            gridTemplateColumns: galleryCollapsed ? "0px 1fr" : "var(--gallery-rail-width) 1fr",
          }}
        >
          {/* Gallery rail — collapsible */}
          <div className="hidden xl:block">
            <motion.aside
              aria-label="Source gallery"
              className={cn(
                "h-full w-[var(--gallery-rail-width)]",
                galleryCollapsed && "pointer-events-none"
              )}
              initial={false}
              animate={{
                x: galleryCollapsed ? -320 : 0,
                opacity: galleryCollapsed ? 0 : 1,
              }}
              transition={springs.galleryToggle}
              style={{ willChange: "transform" }}
            >
              <div className="min-w-[280px] space-y-4">{left}</div>
            </motion.aside>
          </div>

          {/* Gallery toggle for desktop */}
          <div className="hidden pt-1 xl:block">
            <Button
              aria-label={galleryCollapsed ? "Expand source gallery" : "Collapse source gallery"}
              size="sm"
              variant="ghost"
              onClick={onToggleGallery}
            >
              {galleryCollapsed ? (
                <PanelLeftOpen className="h-4 w-4" />
              ) : (
                <PanelLeftClose className="h-4 w-4" />
              )}
            </Button>
          </div>

          {/* Center — Answer Board (dominant) */}
          <section className="min-w-0">
            <div className="mx-auto max-w-[var(--answer-board-max-width)]">{children}</div>
          </section>
        </div>

        {/* Mobile source gallery — shown below center on small screens */}
        <div className="mt-6 xl:hidden">{left}</div>
      </main>

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
          <div className="min-h-0 flex-1 overflow-hidden">{right}</div>
        </div>
      </motion.aside>
    </>
  );
}
