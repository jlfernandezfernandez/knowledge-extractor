export type AuthenticatedUser = {
  id: string;
  email: string;
  display_name: string;
};

export type AuthResponse = {
  user: AuthenticatedUser;
};

export type LoginInput = {
  email: string;
  password: string;
};

export type RegisterInput = LoginInput & {
  display_name: string;
};

export type AuthStatus = "loading" | "authenticated" | "anonymous";
