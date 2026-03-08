import { createBrowserRouter, Navigate, Outlet, useLocation } from "react-router-dom";
import { useEffect, type ReactNode } from "react";
import { AppHomePage } from "../pages/AppHomePage";
import { AuthCallbackPage } from "../pages/AuthCallbackPage";
import { LoginPage } from "../pages/LoginPage";
import { NotebookPage } from "../pages/NotebookPage";
import { useAuthStore } from "../state/auth-store";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/auth/callback", element: <AuthCallbackPage /> },
  {
    path: "/app",
    element: (
      <RequireAuth>
        <AppHomePage />
      </RequireAuth>
    ),
  },
  {
    path: "/notebooks/:notebookId",
    element: (
      <RequireAuth>
        <NotebookPage />
      </RequireAuth>
    ),
  },
  { path: "*", element: <Navigate to="/app" replace /> },
]);

function RequireAuth({ children }: { children: ReactNode }): JSX.Element {
  const location = useLocation();
  const bootstrapped = useAuthStore((state) => state.bootstrapped);
  const status = useAuthStore((state) => state.status);
  const restoreSession = useAuthStore((state) => state.restoreSession);

  useEffect(() => {
    if (!bootstrapped) {
      void restoreSession();
    }
  }, [bootstrapped, restoreSession]);

  if (!bootstrapped || status === "loading") {
    return <div className="app-loader">Loading workspace...</div>;
  }
  if (status !== "authenticated") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <OutletWrapper>{children}</OutletWrapper>;
}

function OutletWrapper({ children }: { children: ReactNode }): JSX.Element {
  return <>{children ?? <Outlet />}</>;
}
