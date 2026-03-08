import { create } from "zustand";
import { decodeUserFromAccessToken } from "../lib/jwt";
import { requestJson, requestVoid, setAuthBridge } from "../lib/http";
import type { AuthPayload, AuthUser, DependencyHealth } from "../types/api";

type AuthState = {
  user: AuthUser | null;
  accessToken: string | null;
  bootstrapped: boolean;
  status: "idle" | "loading" | "authenticated" | "anonymous";
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  exchangeGoogle: (oauthCode: string) => Promise<void>;
  restoreSession: () => Promise<string | null>;
  logout: () => Promise<void>;
  dependencyHealth: () => Promise<DependencyHealth>;
  clearError: () => void;
};

let refreshPromise: Promise<string | null> | null = null;

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  bootstrapped: false,
  status: "idle",
  error: null,
  login: async (email, password) => {
    set({ status: "loading", error: null });
    const payload = await requestJson<AuthPayload>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      headers: { "Content-Type": "application/json" },
      auth: false,
      allowRefresh: false,
    });
    set({ user: payload.user, accessToken: payload.access_token, status: "authenticated", bootstrapped: true });
  },
  register: async (email, password) => {
    set({ status: "loading", error: null });
    const payload = await requestJson<AuthPayload>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      headers: { "Content-Type": "application/json" },
      auth: false,
      allowRefresh: false,
    });
    set({ user: payload.user, accessToken: payload.access_token, status: "authenticated", bootstrapped: true });
  },
  exchangeGoogle: async (oauthCode) => {
    set({ status: "loading", error: null });
    const payload = await requestJson<AuthPayload>("/api/v1/auth/google/exchange", {
      method: "POST",
      body: JSON.stringify({ oauth_code: oauthCode }),
      headers: { "Content-Type": "application/json" },
      auth: false,
      allowRefresh: false,
    });
    set({ user: payload.user, accessToken: payload.access_token, status: "authenticated", bootstrapped: true });
  },
  restoreSession: async () => {
    if (refreshPromise) {
      return refreshPromise;
    }
    refreshPromise = (async () => {
      try {
        const payload = await requestJson<{ access_token: string; token_type: string }>("/api/v1/auth/refresh", {
          method: "POST",
          auth: false,
          allowRefresh: false,
        });
        const user = decodeUserFromAccessToken(payload.access_token);
        set({
          user,
          accessToken: payload.access_token,
          status: user ? "authenticated" : "anonymous",
          bootstrapped: true,
          error: null,
        });
        return payload.access_token;
      } catch {
        set({ user: null, accessToken: null, status: "anonymous", bootstrapped: true });
        return null;
      } finally {
        refreshPromise = null;
      }
    })();
    return refreshPromise;
  },
  logout: async () => {
    try {
      await requestVoid("/api/v1/auth/logout", { method: "POST", allowRefresh: false, auth: false });
    } finally {
      set({ user: null, accessToken: null, status: "anonymous", bootstrapped: true, error: null });
    }
  },
  dependencyHealth: async () =>
    requestJson<DependencyHealth>("/api/v1/health/dependencies", {
      auth: false,
      allowRefresh: false,
    }),
  clearError: () => set({ error: null }),
}));

setAuthBridge({
  getAccessToken: () => useAuthStore.getState().accessToken,
  refreshAccessToken: () => useAuthStore.getState().restoreSession(),
  clearSession: () =>
    useAuthStore.setState({
      user: null,
      accessToken: null,
      status: "anonymous",
      bootstrapped: true,
      error: null,
    }),
});
