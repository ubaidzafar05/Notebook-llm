import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAppTheme } from "@/hooks/use-app-theme";
import { useAuthMutations } from "@/hooks/use-workspace-queries";
import { ApiError } from "@/lib/api";
import { useAuthStore } from "@/store/use-auth-store";

export function AuthCallbackPage(): JSX.Element {
  useAppTheme();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const oauthCode = searchParams.get("oauth_code");
  const setSession = useAuthStore((state) => state.setSession);
  const { exchangeGoogleCode: exchangeMutation } = useAuthMutations();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function exchange(): Promise<void> {
      if (!oauthCode) {
        setError("Missing OAuth exchange code.");
        return;
      }
      try {
        const session = await exchangeMutation.mutateAsync(oauthCode);
        if (cancelled) {
          return;
        }
        setSession(session);
        navigate("/notebooks", { replace: true });
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof ApiError ? cause.message : "Google sign in failed.");
        }
      }
    }

    void exchange();
    return () => {
      cancelled = true;
    };
  }, [exchangeMutation, navigate, oauthCode, setSession]);

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10 sm:px-6">
      <section className="w-full max-w-[560px] rounded-[2rem] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)]/95 p-8 text-center shadow-panel backdrop-blur-xl">
        {error ? (
          <>
            <h1 className="font-serif text-3xl text-[color:var(--text-hero)]">Sign in failed</h1>
            <p className="mt-4 text-sm leading-6 text-[color:var(--text-muted)]">{error}</p>
          </>
        ) : (
          <>
            <Loader2 className="mx-auto h-8 w-8 animate-spin text-[color:var(--accent-soft)]" />
            <h1 className="mt-4 font-serif text-3xl text-[color:var(--text-hero)]">Completing Google sign in</h1>
            <p className="mt-4 text-sm leading-6 text-[color:var(--text-muted)]">Exchanging the OAuth code for an authenticated notebook session.</p>
          </>
        )}
      </section>
    </main>
  );
}
