import { useEffect } from "react";
import { Navigate, Outlet, RouterProvider, createBrowserRouter, useLocation, useNavigate } from "react-router-dom";
import { useAuthSessionBootstrap } from "@/hooks/use-auth-session";
import { authSelectors, useAuthStore } from "@/store/use-auth-store";
import { AuthCallbackPage } from "@/pages/AuthCallbackPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotebooksPage } from "@/pages/NotebooksPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { SourceDetailPage } from "@/pages/SourceDetailPage";
import { WorkspacePage } from "@/pages/WorkspacePage";

const router = createBrowserRouter([
  {
    path: "/",
    element: <RootRedirect />
  },
  {
    path: "/auth",
    element: <PublicOnlyRoute />,
    children: [
      { path: "login", element: <LoginPage /> },
      { path: "register", element: <RegisterPage /> },
      { path: "callback", element: <AuthCallbackPage /> }
    ]
  },
  {
    path: "/",
    element: <ProtectedRoute />,
    children: [
      { path: "notebooks", element: <NotebooksPage /> },
      { path: "notebooks/:notebookId", element: <WorkspacePage /> },
      { path: "notebooks/:notebookId/sources/:sourceId", element: <SourceDetailPage /> }
    ]
  },
  {
    path: "*",
    element: <Navigate replace to="/" />
  }
]);

export function AppRouter(): JSX.Element {
  return <RouterProvider router={router} />;
}

function RootRedirect(): JSX.Element {
  const { ready } = useAuthSessionBootstrap();
  const isAuthenticated = useAuthStore(authSelectors.isAuthenticated);
  if (!ready) {
    return <RouteLoadingScreen />;
  }
  return <Navigate replace to={isAuthenticated ? "/notebooks" : "/auth/login"} />;
}

function PublicOnlyRoute(): JSX.Element {
  const { ready } = useAuthSessionBootstrap();
  const isAuthenticated = useAuthStore(authSelectors.isAuthenticated);
  if (!ready) {
    return <RouteLoadingScreen />;
  }
  if (isAuthenticated) {
    return <Navigate replace to="/notebooks" />;
  }
  return <Outlet />;
}

function ProtectedRoute(): JSX.Element {
  const { ready } = useAuthSessionBootstrap();
  const accessToken = useAuthStore(authSelectors.accessToken);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (ready || accessToken) {
      return;
    }
    void navigate("/auth/login", { replace: true, state: { from: location.pathname } });
  }, [accessToken, location.pathname, navigate, ready]);

  if (!ready) {
    return <RouteLoadingScreen />;
  }
  if (!accessToken) {
    return <Navigate replace state={{ from: location.pathname }} to="/auth/login" />;
  }
  return <Outlet />;
}

function RouteLoadingScreen(): JSX.Element {
  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10 sm:px-6">
      <section className="rounded-[1.8rem] border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] px-6 py-5 text-sm text-[color:var(--text-muted)] shadow-soft-card">
        Initializing notebook session...
      </section>
    </main>
  );
}
