import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAppTheme } from "@/hooks/use-app-theme";
import { useAuthMutations } from "@/hooks/use-workspace-queries";
import { ApiError } from "@/lib/api";
import { useAuthStore } from "@/store/use-auth-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function LoginPage(): JSX.Element {
  useAppTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const setSession = useAuthStore((state) => state.setSession);
  const { login: loginMutation, startGoogleAuth: googleMutation } = useAuthMutations();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const redirectTo = typeof location.state === "object" && location.state && "from" in location.state ? String((location.state as { from?: string }).from ?? "/notebooks") : "/notebooks";

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setFormError(null);
    try {
      const session = await loginMutation.mutateAsync({ email, password });
      setSession(session);
      navigate(redirectTo, { replace: true });
    } catch (error) {
      setFormError(resolveErrorMessage(error));
    }
  }

  async function handleGoogleLogin(): Promise<void> {
    setFormError(null);
    try {
      const result = await googleMutation.mutateAsync();
      window.location.assign(result.authUrl);
    } catch (error) {
      setFormError(resolveErrorMessage(error));
    }
  }

  return (
    <main className="auth-shell flex min-h-screen items-center justify-center px-4 py-10 sm:px-6">
      <section className="w-full max-w-[980px] rounded-[2rem] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)]/95 p-6 shadow-panel backdrop-blur-xl md:grid md:grid-cols-[1.1fr_0.9fr] md:gap-8 md:p-8">
        <div className="flex flex-col justify-between rounded-[1.8rem] border border-[color:var(--panel-border)] bg-[color:var(--response-bg)] p-6">
          <div>
            <p className="text-xs uppercase tracking-[0.32em] text-[color:var(--text-kicker)]">NotebookLM</p>
            <h1 className="mt-4 max-w-md font-serif text-[clamp(2.2rem,4vw,4rem)] leading-[0.95] tracking-[-0.04em] text-[color:var(--text-hero)]">
              A calmer way to read, cite, and draft.
            </h1>
            <p className="mt-5 max-w-lg text-base leading-7 text-[color:var(--text-muted)]">
              Sign in to manage notebooks, upload sources, chat against real indexed material, and generate podcast drafts from the same workspace.
            </p>
          </div>
          <div className="mt-8 rounded-[1.5rem] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4 text-sm leading-6 text-[color:var(--text-primary)]">
            Production path: authenticated notebooks, notebook-scoped sources, streaming chat, chunk inspection, and podcast jobs.
          </div>
        </div>

        <div className="mt-8 md:mt-0">
          <div className="rounded-[1.8rem] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-6">
            <h2 className="font-serif text-3xl text-[color:var(--text-hero)]">Sign in</h2>
            <p className="mt-2 text-sm text-[color:var(--text-muted)]">Use email and password or continue with Google.</p>
            <form className="mt-6 space-y-4" onSubmit={(event) => void handleSubmit(event)}>
              <div>
                <label className="mb-2 block text-sm font-medium text-[color:var(--text-primary)]" htmlFor="login-email">
                  Email
                </label>
                <Input id="login-email" required type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-[color:var(--text-primary)]" htmlFor="login-password">
                  Password
                </label>
                <Input id="login-password" required minLength={8} type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
              </div>
              {formError ? <p className="rounded-xl border border-[color:hsl(var(--destructive)/0.3)] bg-[color:hsl(var(--destructive)/0.1)] px-3 py-2 text-sm text-[color:hsl(var(--destructive))]">{formError}</p> : null}
              <Button className="w-full" disabled={loginMutation.isPending} type="submit">
                {loginMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Continue
              </Button>
            </form>
            <Button className="mt-3 w-full" disabled={googleMutation.isPending} type="button" variant="outline" onClick={() => void handleGoogleLogin()}>
              {googleMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Continue with Google
            </Button>
            <p className="mt-4 text-sm text-[color:var(--text-muted)]">
              No account yet? {" "}
              <Link className="text-[color:var(--accent-soft)] underline-offset-4 hover:underline" to="/auth/register">
                Create one
              </Link>
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

function resolveErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Unable to complete sign in.";
}
