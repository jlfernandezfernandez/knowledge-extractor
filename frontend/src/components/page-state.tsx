import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type PageStateProps = {
  title: string;
  description: string;
  loading?: boolean;
};

export function PageState({ title, description, loading = false }: PageStateProps) {
  return (
    <section className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-5 py-8 md:px-8 md:py-10">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">{description}</p>
      </header>
      <Card>
        <CardHeader>
          <CardTitle>{loading ? <Skeleton className="h-5 w-36" /> : title}</CardTitle>
          <CardDescription>
            {loading ? <Skeleton className="h-4 w-72" /> : description}
          </CardDescription>
        </CardHeader>
        {loading && (
          <CardContent className="flex flex-col gap-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-4/5" />
          </CardContent>
        )}
      </Card>
    </section>
  );
}
