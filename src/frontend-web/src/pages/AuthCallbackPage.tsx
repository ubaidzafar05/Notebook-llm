import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { HttpError } from "../lib/http";
import { useAuthStore } from "../state/auth-store";

export function AuthCallbackPage(): JSX.Element {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const exchangeGoogle = useAuthStore((state) => state.exchangeGoogle);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const oauthCode = params.get("oauth_code");
    if (!oauthCode) {
      setError("Missing OAuth exchange code.");
      return;
    }
    void exchange(oauthCode);
  }, [exchangeGoogle, params]);

  async function exchange(oauthCode: string): Promise<void> {
    try {
      await exchangeGoogle(oauthCode);
      navigate("/app", { replace: true });
    } catch (rawError) {
      setError(rawError instanceof HttpError ? rawError.message : "Google sign-in failed");
    }
  }

  return <div className="app-loader">{error ?? "Completing Google sign-in..."}</div>;
}
