import { useTranslation } from "react-i18next";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ApiError } from "@/lib/api";

/** A failure, said where it happened. Never a toast: the thing that failed is
 *  on screen, and the message belongs next to it. */
export function ErrorNote({ error }: { error: unknown }) {
  const { t } = useTranslation();
  if (!error) return null;
  const message = String(error instanceof ApiError
    ? t(`errors.${error.code}`, { defaultValue: t("errors.requestFailed") })
    : t("errors.requestFailed"));
  return (
    <Alert className="mt-4" variant="destructive">
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}
