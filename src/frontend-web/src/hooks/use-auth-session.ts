import { useEffect, useState } from "react";
import { refreshSession } from "@/lib/api";
import { useAuthStore } from "@/store/use-auth-store";

export function useAuthSessionBootstrap(): { ready: boolean } {
  const initialized = useAuthStore((state) => state.initialized);
  const accessToken = useAuthStore((state) => state.accessToken);
  const setInitialized = useAuthStore((state) => state.setInitialized);
  const [ready, setReady] = useState(initialized);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap(): Promise<void> {
      if (initialized) {
        setReady(true);
        return;
      }
      if (accessToken) {
        setInitialized(true);
        if (!cancelled) {
          setReady(true);
        }
        return;
      }
      await refreshSession();
      setInitialized(true);
      if (!cancelled) {
        setReady(true);
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, [accessToken, initialized, setInitialized]);

  return { ready };
}
