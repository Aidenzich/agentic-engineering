import { Navigate, Outlet } from "react-router";
import { useAuthStore } from "@/lib/store/auth";
import { useMe } from "@/lib/api/auth";

export default function AuthGuard() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { isLoading, isError } = useMe();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-200 border-t-blue-600" />
          <p className="text-sm text-slate-500">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || isError) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
