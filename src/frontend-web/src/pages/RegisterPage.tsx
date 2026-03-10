import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAppTheme } from "@/hooks/use-app-theme";
import { useAuthMutations } from "@/hooks/use-workspace-queries";
import { ApiError } from "@/lib/api";
import { useAuthStore } from "@/store/use-auth-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function RegisterPage(): JSX.Element {
  useAppTheme();
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const { register: registerMutation } = useAuthMutations();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setFormError(null);
    if (password !== confirmPassword) {
      setFormError("Passwords do not match.");
      return;
    }
    try {
      const session = await registerMutation.mutateAsync({ email, password });
      setSession(session);
      navigate("/notebooks", { replace: true });
    } catch (error) {
      setFormError(resolveErrorMessage(error));
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10 sm:px-6">
      <section className="w-full max-w-[760px] rounded-[2rem] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)]/95 p-8 shadow-panel backdrop-blur-xl">
        <p className="text-xs uppercase tracking-[0.32em] text-[color:var(--text-kicker)]">Create account</p>
        <h1 className="mt-4 font-serif text-[clamp(2.2rem,4vw,3.5rem)] leading-[0.96] tracking-[-0.04em] text-[color:var(--text-hero)]">
          Start a notebook that can actually think across its sources.
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-7 text-[color:var(--text-muted)]">
          Registration provisions a default notebook on the backend, so you can create sources and open a chat session immediately after sign up.
        </p>

        <form className="mt-8 grid gap-4 md:grid-cols-2" onSubmit={(event) => void handleSubmit(event)}>
          <div className="md:col-span-2">
            <label className="mb-2 block text-sm font-medium text-[color:var(--text-primary)]" htmlFor="register-email">
              Email
            </label>
            <Input id="register-email" required type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-[color:var(--text-primary)]" htmlFor="register-password">
              Password
            </label>
            <Input id="register-password" required minLength={8} type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-[color:var(--text-primary)]" htmlFor="register-password-confirm">
              Confirm password
            </label>
            <Input id="register-password-confirm" required minLength={8} type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
          </div>
          {formError ? <p className="md:col-span-2 rounded-xl border border-[color:hsl(var(--destructive)/0.3)] bg-[color:hsl(var(--destructive)/0.1)] px-3 py-2 text-sm text-[color:hsl(var(--destructive))]">{formError}</p> : null}
          <div className="md:col-span-2 flex items-center justify-between gap-3 pt-2">
            <p className="text-sm text-[color:var(--text-muted)]">
              Already registered? {" "}
              <Link className="text-[color:var(--accent-soft)] underline-offset-4 hover:underline" to="/auth/login">
                Sign in
              </Link>
            </p>
            <Button disabled={registerMutation.isPending} type="submit">
              {registerMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Create account
            </Button>
          </div>
        </form>
      </section>
    </main>
  );
}

function resolveErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Unable to create account.";
}
