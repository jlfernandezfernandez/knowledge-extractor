import { AppRouter } from "@/app/router";
import { AuthProvider } from "@/features/auth/auth-provider";

export default function App() {
  return (
    <AuthProvider>
      <AppRouter />
    </AuthProvider>
  );
}
