import { useEffect } from "react";
import { useWorkspaceStore, type ThemeMode } from "@/store/use-workspace-store";
import { canUseWebGL } from "@/lib/utils";

const THEME_STORAGE_KEY = "notebooklm-theme-mode";
const themeModes: ThemeMode[] = ["dusk-indigo", "linen-light", "notebook-dark"];

export function useAppTheme(): void {
  const themeMode = useWorkspaceStore((state) => state.studioState.themeMode);
  const setReducedMotion = useWorkspaceStore((state) => state.setReducedMotion);
  const setWebglReady = useWorkspaceStore((state) => state.setWebglReady);
  const setThemeMode = useWorkspaceStore((state) => state.setThemeMode);

  useEffect(() => {
    const savedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (savedTheme && themeModes.includes(savedTheme as ThemeMode)) {
      setThemeMode(savedTheme as ThemeMode);
    }
  }, [setThemeMode]);

  useEffect(() => {
    const isDarkTheme = themeMode !== "linen-light";
    document.documentElement.dataset.theme = themeMode;
    document.body.dataset.theme = themeMode;
    document.documentElement.classList.toggle("dark", isDarkTheme);
    document.body.classList.toggle("dark", isDarkTheme);
    window.localStorage.setItem(THEME_STORAGE_KEY, themeMode);
  }, [themeMode]);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = (): void => setReducedMotion(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, [setReducedMotion]);

  useEffect(() => {
    setWebglReady(canUseWebGL());
  }, [setWebglReady]);
}
