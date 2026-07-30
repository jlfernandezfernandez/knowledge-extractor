import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { authApi } from "./api";
import type { AuthStatus, AuthenticatedUser, LoginInput, RegisterInput } from "./types";

type AuthContextValue = {
  user: AuthenticatedUser | null;
  status: AuthStatus;
  login: (input: LoginInput) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const sessionVersion = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    let mounted = true;
    const version = sessionVersion.current;

    void authApi.me(controller.signal)
      .then(({ user: restoredUser }) => {
        if (!mounted || sessionVersion.current !== version) return;
        setUser(restoredUser);
        setStatus("authenticated");
      })
      .catch(() => {
        if (!mounted || controller.signal.aborted || sessionVersion.current !== version) return;
        setUser(null);
        setStatus("anonymous");
      });

    return () => {
      mounted = false;
      controller.abort();
    };
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    status,
    login: async (input) => {
      const response = await authApi.login(input);
      sessionVersion.current += 1;
      setUser(response.user);
      setStatus("authenticated");
    },
    register: async (input) => {
      const response = await authApi.register(input);
      sessionVersion.current += 1;
      setUser(response.user);
      setStatus("authenticated");
    },
    logout: async () => {
      sessionVersion.current += 1;
      try {
        await authApi.logout();
      } finally {
        setUser(null);
        setStatus("anonymous");
      }
    },
  }), [status, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// oxlint-disable-next-line react/only-export-components -- the hook is the provider's public consumer API.
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within an AuthProvider");
  return context;
}
