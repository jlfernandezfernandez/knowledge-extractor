import { api } from "@/lib/api";
import type { AuthResponse, LoginInput, RegisterInput } from "./types";

export const authApi = {
  login: (input: LoginInput) =>
    api<AuthResponse>("/api/auth/login", { method: "POST", body: JSON.stringify(input) }),
  register: (input: RegisterInput) =>
    api<AuthResponse>("/api/auth/register", { method: "POST", body: JSON.stringify(input) }),
  me: (signal?: AbortSignal) => api<AuthResponse>("/api/auth/me", { signal }),
  logout: () => api<void>("/api/auth/logout", { method: "POST" }),
};
