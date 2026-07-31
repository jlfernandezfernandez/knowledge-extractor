import { post, request } from "@/lib/api";
import type { AuthResponse, LoginInput, RegisterInput } from "./types";

export const authApi = {
  login: (input: LoginInput) => post<AuthResponse>("/api/auth/login", input),
  register: (input: RegisterInput) => post<AuthResponse>("/api/auth/register", input),
  me: (signal?: AbortSignal) => request<AuthResponse>("/api/auth/me", { signal }),
  logout: () => post<void>("/api/auth/logout"),
};
