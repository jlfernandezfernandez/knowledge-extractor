import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import { useAuth } from "./auth-provider";

type AuthScreenProps = { mode: "login" | "register" };

export function AuthScreen({ mode }: AuthScreenProps) {
  const { t } = useTranslation();
  const { login, register } = useAuth();
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const isRegister = mode === "register";
  const copy = isRegister ? "auth.register" : "auth.login";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setFields({});
    setError("");
    const values = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>;

    try {
      if (isRegister) {
        await register({ display_name: values.display_name, email: values.email, password: values.password });
      } else {
        await login({ email: values.email, password: values.password });
      }
    } catch (caught) {
      if (caught instanceof ApiError && caught.fields) setFields(caught.fields);
      const message = caught instanceof Error ? caught.message : t("auth.failed");
      setError(message);
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  }

  const fieldError = (name: string) => fields[name] && <p id={`${name}-error`} className="text-sm text-destructive">{fields[name]}</p>;

  return (
    <main className="mx-auto flex min-h-dvh max-w-sm items-center px-5">
      <Card className="w-full">
        <CardHeader>
          <Brand label={t("app.name")} className="mb-2" />
          <CardTitle><h1 className="text-inherit font-inherit">{t(`${copy}.title`)}</h1></CardTitle>
          <CardDescription>{t(`${copy}.description`)}</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={submit}>
            {isRegister && (
              <div className="flex flex-col gap-2">
                <Label htmlFor="display_name">{t("auth.displayName")}</Label>
                <Input id="display_name" name="display_name" required autoComplete="name" aria-invalid={Boolean(fields.display_name)} aria-describedby={fields.display_name ? "display_name-error" : undefined} />
                {fieldError("display_name")}
              </div>
            )}
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">{t("auth.email")}</Label>
              <Input id="email" name="email" required type="email" autoComplete="email" aria-invalid={Boolean(fields.email)} aria-describedby={fields.email ? "email-error" : undefined} />
              {fieldError("email")}
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="password">{t("auth.password")}</Label>
              <Input id="password" name="password" required type="password" minLength={8} autoComplete={isRegister ? "new-password" : "current-password"} aria-invalid={Boolean(fields.password)} aria-describedby={fields.password ? "password-error" : undefined} />
              {fieldError("password")}
            </div>
            {error && !Object.keys(fields).length && <p className="text-sm text-destructive" role="alert">{error}</p>}
            <Button type="submit" disabled={submitting}>{t(`${copy}.submit`)}</Button>
            <Link className="text-center text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline" to={isRegister ? "/login" : "/register"}>
              {t(`${copy}.alternate`)}
            </Link>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}
