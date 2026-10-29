import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import { AuthPage } from "./pages/AuthPage";
import { BoardPage } from "./pages/BoardPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HomePage } from "./pages/HomePage";
import { OrgPage } from "./pages/OrgPage";

function Private({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="auth-page muted">Loading…</div>;
  if (!user) return <Navigate to="/auth" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/auth" element={<AuthPage />} />
      <Route
        path="/"
        element={
          <Private>
            <HomePage />
          </Private>
        }
      />
      <Route
        path="/orgs/:orgId"
        element={
          <Private>
            <OrgPage />
          </Private>
        }
      />
      <Route
        path="/orgs/:orgId/dashboard"
        element={
          <Private>
            <DashboardPage />
          </Private>
        }
      />
      <Route
        path="/projects/:projectId"
        element={
          <Private>
            <BoardPage />
          </Private>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
