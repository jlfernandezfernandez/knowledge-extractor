import { AppRouter } from "@/app/router";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/features/auth/auth-provider";

export default function App() {
  return (
    <TooltipProvider>
      <AuthProvider>
        <AppRouter />
      </AuthProvider>
    </TooltipProvider>
  );
}
