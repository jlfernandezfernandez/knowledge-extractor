import { useEffect, useState } from "react";
import { ReviewFlow } from "@/components/review/review-flow";
import { Toaster } from "@/components/ui/sonner";
import { useReview } from "@/hooks/use-review";
import { API_URL, request } from "@/lib/api/client";

type User = { id: string; name: string; email: string; team: { id: string; name: string; knowledge_base: string } };
type Interview = { id: string; title: string; brief: string; status: string; requester: string };

export default function App() {
  const review = useReview();
  const [user, setUser] = useState<User | null>(null);
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [loading, setLoading] = useState(true);
  const inReview = /^\/review\//.test(location.pathname) || review.session !== null || location.pathname === "/contribute";
  const refresh = async () => {
    try {
      const me = await request<{ user: User }>("/api/auth/me");
      setUser(me.user);
      setInterviews((await request<{ items: Interview[] }>("/api/interviews")).items);
    } catch { setUser(null); } finally { setLoading(false); }
  };
  useEffect(() => { void refresh(); }, []);
  if (loading) return null;
  if (!user) return <Auth onSuccess={refresh} />;
  if (inReview) return <main className="h-dvh"><ReviewFlow review={review} author={user.name} knowledgeBase={user.team.knowledge_base} onCommitted={() => { location.assign("/"); }} /></main>;
  return <main className="mx-auto min-h-dvh max-w-3xl px-5 py-8"><header className="mb-12 flex items-center justify-between"><div><h1 className="text-xl font-semibold">Knowli</h1><p className="text-sm text-muted-foreground">{user.team.name}</p></div><button className="text-sm" onClick={() => fetch(`${API_URL}/api/auth/logout`, { method: "POST", credentials: "include" }).then(() => setUser(null))}>{user.name} · Salir</button></header><button className="mb-10 rounded-xl bg-primary px-4 py-3 text-primary-foreground" onClick={() => { history.pushState(null, "", "/contribute"); review.reset(); }}>Aportar conocimiento</button><section className="mb-10"><h2 className="mb-3 text-lg font-semibold">Entrevistas pendientes</h2>{interviews.filter((i) => i.status === "pending").length ? interviews.filter((i) => i.status === "pending").map((i) => <article className="mb-2 rounded-xl border p-4" key={i.id}><strong>{i.title}</strong><p className="text-sm text-muted-foreground">{i.brief || `Solicitada por ${i.requester}`}</p><button className="mt-3 text-sm underline" onClick={async () => { const r = await request<{session_id:string}>(`/api/interviews/${i.id}/start`, { method: "POST" }); location.assign(`/review/${r.session_id}`); }}>Empezar entrevista</button></article>) : <p className="text-sm text-muted-foreground">No tienes entrevistas pendientes.</p>}</section><section><h2 className="mb-3 text-lg font-semibold">Histórico</h2><p className="text-sm text-muted-foreground">Tus próximas aportaciones y entrevistas aparecerán aquí.</p></section><Toaster position="bottom-right" /></main>;
}

function Auth({ onSuccess }: { onSuccess: () => Promise<void> }) {
  const [register, setRegister] = useState(false); const [error, setError] = useState("");
  async function submit(e: React.FormEvent<HTMLFormElement>) { e.preventDefault(); const data = Object.fromEntries(new FormData(e.currentTarget)); const r = await fetch(`${API_URL}/api/auth/${register ? "register" : "login"}`, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }); if (!r.ok) return setError((await r.json()).detail); await onSuccess(); }
  return <main className="mx-auto flex min-h-dvh max-w-sm items-center px-5"><form className="w-full space-y-3" onSubmit={submit}><h1 className="text-2xl font-semibold">{register ? "Crea tu equipo" : "Entra en Knowli"}</h1>{register && <><input required name="display_name" placeholder="Tu nombre" className="w-full rounded-lg border p-3" /><input name="organisation_name" placeholder="Organización (opcional)" className="w-full rounded-lg border p-3" /></>}<input required name="email" type="email" placeholder="Email" className="w-full rounded-lg border p-3" /><input required name="password" type="password" minLength={8} placeholder="Contraseña" className="w-full rounded-lg border p-3" /><button className="w-full rounded-lg bg-primary p-3 text-primary-foreground">{register ? "Crear cuenta" : "Entrar"}</button>{error && <p className="text-sm text-destructive">{error}</p>}<button type="button" className="text-sm underline" onClick={() => setRegister(!register)}>{register ? "Ya tengo cuenta" : "Crear cuenta"}</button></form></main>;
}
