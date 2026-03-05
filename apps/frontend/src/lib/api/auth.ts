import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/lib/store/auth";
import apiClient from "@/lib/api/client";
import type {
  ApiResponse,
  AuthResponse,
  Org,
  User,
} from "@/types/api";

export function useLogin() {
  const setUser = useAuthStore((s) => s.setUser);

  return useMutation({
    mutationFn: async (payload: { email: string; password: string }) => {
      const { data } = await apiClient.post<ApiResponse<AuthResponse>>(
        "/auth/login",
        payload,
      );
      return data.data;
    },
    onSuccess: (data) => {
      localStorage.setItem("access_token", data.access_token);
      setUser(data.user);
    },
  });
}

export function useRegister() {
  const setUser = useAuthStore((s) => s.setUser);

  return useMutation({
    mutationFn: async (payload: {
      email: string;
      password: string;
      name: string;
    }) => {
      const { data } = await apiClient.post<ApiResponse<AuthResponse>>(
        "/auth/register",
        payload,
      );
      return data.data;
    },
    onSuccess: (data) => {
      localStorage.setItem("access_token", data.access_token);
      setUser(data.user);
    },
  });
}

export function useLogout() {
  const logout = useAuthStore((s) => s.logout);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      await apiClient.post("/auth/logout");
    },
    onSettled: () => {
      logout();
      queryClient.clear();
    },
  });
}

export function useMe() {
  const setUser = useAuthStore((s) => s.setUser);

  return useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const { data } = await apiClient.get<ApiResponse<User>>("/users/me");
      setUser(data.data);
      return data.data;
    },
    retry: false,
    enabled: !!localStorage.getItem("access_token"),
  });
}

export function useMyOrgs() {
  return useQuery({
    queryKey: ["my-orgs"],
    queryFn: async () => {
      const { data } =
        await apiClient.get<ApiResponse<Org[]>>("/orgs");
      return data.data;
    },
    enabled: !!localStorage.getItem("access_token"),
  });
}
