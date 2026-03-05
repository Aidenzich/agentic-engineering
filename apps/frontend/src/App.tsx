import { Route, Routes } from "react-router";
import AuthGuard from "@/components/auth-guard";
import AppLayout from "@/components/layout/app-layout";
import LoginPage from "@/pages/login";
import RegisterPage from "@/pages/register";
import DashboardPage from "@/pages/dashboard";

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
      <p className="mt-2 text-sm text-slate-500">This page is coming soon.</p>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<AuthGuard />}>
        <Route path="/:orgSlug" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route
            path="wiki"
            element={<PlaceholderPage title="Wiki" />}
          />
          <Route
            path="projects"
            element={<PlaceholderPage title="Projects" />}
          />
          <Route
            path="services"
            element={<PlaceholderPage title="Services" />}
          />
          <Route
            path="workflows"
            element={<PlaceholderPage title="Workflows" />}
          />
          <Route
            path="settings"
            element={<PlaceholderPage title="Settings" />}
          />
        </Route>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
