import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import { useTranslation } from "react-i18next";
import { Brand } from "@/components/brand";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { useAuth } from "./auth-provider";

type AuthScreenProps = { mode: "login" | "register" };

export function AuthScreen({ mode }: AuthScreenProps) {
  const { t } = useTranslation();
  const { login, register } = useAuth();
  const [fields, setFields] = useState<Record<string, string>>({});
  const [error, setError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);
  const isRegister = mode === "register";
  const copy = isRegister ? "auth.register" : "auth.login";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setFields({});
    setError(null);
    const values = Object.fromEntries(new FormData(event.currentTarget)) as Record<string, string>;

    try {
      if (isRegister) {
        await register({ display_name: values.display_name, email: values.email, password: values.password });
      } else {
        await login({ email: values.email, password: values.password });
      }
    } catch (caught) {
      if (caught instanceof ApiError && caught.fields) setFields(caught.fields);
      setError(caught);
    } finally {
      setSubmitting(false);
    }
  }

  const fieldError = (name: string) => fields[name] && <FieldError id={`${name}-error`}>{t("errors.invalidField")}</FieldError>;

  return (
    <main className="mx-auto flex min-h-dvh max-w-sm flex-col justify-center gap-6 px-5">
      <div className="flex justify-center"><Brand label={t("app.name")} /></div>
      <Card className="w-full">
        <CardHeader>
          <CardTitle><h1 className="text-inherit font-inherit">{t(`${copy}.title`)}</h1></CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-4" onSubmit={submit}>
            <FieldGroup>
              {isRegister && (
                <Field data-invalid={Boolean(fields.display_name) || undefined}>
                  <FieldLabel htmlFor="display_name">{t("auth.displayName")}</FieldLabel>
                  <Input id="display_name" name="display_name" required autoComplete="name" aria-invalid={Boolean(fields.display_name)} aria-describedby={fields.display_name ? "display_name-error" : undefined} />
                  {fieldError("display_name")}
                </Field>
              )}
              <Field data-invalid={Boolean(fields.email) || undefined}>
                <FieldLabel htmlFor="email">{t("auth.email")}</FieldLabel>
                <Input id="email" name="email" required type="email" autoComplete="email" aria-invalid={Boolean(fields.email)} aria-describedby={fields.email ? "email-error" : undefined} />
                {fieldError("email")}
              </Field>
              <Field data-invalid={Boolean(fields.password) || undefined}>
                <FieldLabel htmlFor="password">{t("auth.password")}</FieldLabel>
                <Input id="password" name="password" required type="password" minLength={isRegister ? 8 : undefined} autoComplete={isRegister ? "new-password" : "current-password"} aria-invalid={Boolean(fields.password)} aria-describedby={fields.password ? "password-error" : undefined} />
                {fieldError("password")}
              </Field>
            </FieldGroup>
            {Boolean(error) && !Object.keys(fields).length && (
              <Alert variant="destructive">
                <AlertDescription>{String(error instanceof ApiError ? t(`errors.${error.code}`, { defaultValue: t("errors.requestFailed") }) : t("errors.requestFailed"))}</AlertDescription>
              </Alert>
            )}
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
