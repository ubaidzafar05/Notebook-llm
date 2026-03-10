import { create } from "zustand";

export type AuthUser = {
  id: string;
  email: string;
};

type AuthState = {
  accessToken: string | null;
  user: AuthUser | null;
  initialized: boolean;
  setSession: (session: { accessToken: string; user: AuthUser }) => void;
  updateAccessToken: (accessToken: string | null) => void;
  clearSession: () => void;
  setInitialized: (initialized: boolean) => void;
};

const STORAGE_KEY = "notebooklm-auth-session";

type PersistedAuthState = {
  accessToken: string | null;
  user: AuthUser | null;
};

function loadPersistedState(): PersistedAuthState {
  if (typeof window === "undefined") {
    return { accessToken: null, user: null };
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return { accessToken: null, user: null };
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") {
      return { accessToken: null, user: null };
    }
    const accessToken = typeof (parsed as { accessToken?: unknown }).accessToken === "string" ? (parsed as { accessToken: string }).accessToken : null;
    const userValue = (parsed as { user?: unknown }).user;
    const user = isAuthUser(userValue) ? userValue : null;
    return { accessToken, user };
  } catch {
    return { accessToken: null, user: null };
  }
}

function persistState(state: PersistedAuthState): void {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function isAuthUser(value: unknown): value is AuthUser {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as { id?: unknown; email?: unknown };
  return typeof candidate.id === "string" && typeof candidate.email === "string";
}

const initialState = loadPersistedState();

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: initialState.accessToken,
  user: initialState.user,
  initialized: false,
  setSession: ({ accessToken, user }) =>
    set(() => {
      const next = { accessToken, user };
      persistState(next);
      return { ...next, initialized: true };
    }),
  updateAccessToken: (accessToken) =>
    set((state) => {
      const next = { accessToken, user: state.user };
      persistState(next);
      return { accessToken };
    }),
  clearSession: () =>
    set(() => {
      persistState({ accessToken: null, user: null });
      return { accessToken: null, user: null, initialized: true };
    }),
  setInitialized: (initialized) => set(() => ({ initialized }))
}));

export const authSelectors = {
  accessToken: (state: AuthState) => state.accessToken,
  isAuthenticated: (state: AuthState) => Boolean(state.accessToken && state.user),
  initialized: (state: AuthState) => state.initialized,
  user: (state: AuthState) => state.user
};
