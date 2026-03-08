import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { startGoogleAuth } from "../lib/api";
import { HttpError } from "../lib/http";
import { useAuthStore } from "../state/auth-store";
import styles from "./LoginPage.module.css";

export function LoginPage(): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const login = useAuthStore((state) => state.login);
  const register = useAuthStore((state) => state.register);
  const dependencyHealth = useAuthStore((state) => state.dependencyHealth);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [googlePending, setGooglePending] = useState(false);
  const [dependencyMessage, setDependencyMessage] = useState<string | null>(null);
  const redirectTo = useMemo(() => {
    const state = location.state as { from?: string } | null;
    return state?.from ?? "/app";
  }, [location.state]);

  async function handleSubmit(): Promise<void> {
    const validationError = validateCredentials(email, password);
    if (validationError) {
      setError(validationError);
      return;
    }
    setPending(true);
    setError(null);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password);
      }
      navigate(redirectTo, { replace: true });
    } catch (rawError) {
      setError(rawError instanceof HttpError ? rawError.message : "Authentication failed");
    } finally {
      setPending(false);
    }
  }

  async function handleHealthCheck(): Promise<void> {
    try {
      const health = await dependencyHealth();
      const summary = Object.entries(health)
        .map(([name, item]) => `${name}: ${item.status}`)
        .join(" | ");
      setDependencyMessage(summary);
    } catch (rawError) {
      setDependencyMessage(rawError instanceof Error ? rawError.message : "Dependency check failed");
    }
  }

  async function handleGoogleStart(): Promise<void> {
    setGooglePending(true);
    setError(null);
    try {
      const payload = await startGoogleAuth();
      window.location.href = payload.auth_url;
    } catch (rawError) {
      setError(rawError instanceof HttpError ? rawError.message : "Google sign-in failed to start");
      setGooglePending(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.backdrop} />
      <section className={styles.panel}>
        <p className={styles.kicker}>Notebook-centered research assistant</p>
        <h1 className={styles.title}>NotebookLLM</h1>
        <p className={styles.subtitle}>
          Ground answers in your sources, preserve session memory in Zep, and build podcasts from the same notebook context.
        </p>
        <div className={styles.switcher}>
          <button className={mode === "login" ? styles.activeTab : styles.tab} onClick={() => setMode("login")} type="button">
            Login
          </button>
          <button className={mode === "register" ? styles.activeTab : styles.tab} onClick={() => setMode("register")} type="button">
            Register
          </button>
        </div>
        <label className={styles.label}>
          Email
          <input className={styles.input} value={email} onChange={(event) => setEmail(event.target.value)} type="email" />
        </label>
        <label className={styles.label}>
          Password
          <input className={styles.input} value={password} onChange={(event) => setPassword(event.target.value)} type="password" />
        </label>
        {error ? <p className={styles.error}>{error}</p> : null}
        <div className={styles.actions}>
          <button className={styles.primaryButton} onClick={() => void handleSubmit()} disabled={pending} type="button">
            {pending ? "Working..." : mode === "login" ? "Enter Workspace" : "Create Account"}
          </button>
          <button className={styles.secondaryButton} disabled={googlePending} onClick={() => void handleGoogleStart()} type="button">
            {googlePending ? "Redirecting..." : "Continue with Google"}
          </button>
        </div>
        <button className={styles.healthButton} onClick={() => void handleHealthCheck()} type="button">
          Check Dependencies
        </button>
        {dependencyMessage ? <p className={styles.healthMessage}>{dependencyMessage}</p> : null}
      </section>
    </div>
  );
}

function validateCredentials(email: string, password: string): string | null {
  if (!email.trim()) {
    return "Email is required.";
  }
  if (!email.includes("@")) {
    return "Enter a valid email address.";
  }
  if (password.length < 8) {
    return "Password must be at least 8 characters.";
  }
  return null;
}
