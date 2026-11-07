import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { MODULES } from "@/lib/modules";
import { deleteProject, setProjectStatus } from "../actions";

export default async function ProjectPage({ params }: PageProps<"/projects/[id]">) {
  const { id } = await params;
  const supabase = await createClient();
  const { data: p } = await supabase.from("projects").select("*").eq("id", id).maybeSingle();
  if (!p) notFound();

  const [{ data: spendRaw }, { data: activity }] = await Promise.all([
    supabase.rpc("month_spend_eur", { p_project_id: id }),
    supabase.from("activity_log").select("id,action,created_at").eq("project_id", id)
      .order("created_at", { ascending: false }).limit(10),
  ]);
  const spend = Number(spendRaw ?? 0);
  const budget = Number(p.monthly_budget_eur);
  const pct = budget > 0 ? Math.min(100, (spend / budget) * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold">{p.name}</h1>
          <a href={p.url} target="_blank" rel="noopener noreferrer" className="text-sm text-muted hover:text-foreground">{p.url}</a>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={`/projects/${id}/edit`} className="btn-ghost">Edit</Link>
          <form action={setProjectStatus.bind(null, id)}>
            <input type="hidden" name="status" value={p.status === "paused" ? "active" : "paused"} />
            <button className="btn-ghost">{p.status === "paused" ? "Resume" : "Pause"}</button>
          </form>
          <form action={setProjectStatus.bind(null, id)}>
            <input type="hidden" name="status" value="archived" />
            <button className="btn-ghost">Archive</button>
          </form>
          <form action={deleteProject.bind(null, id)}><button className="btn-danger">Delete</button></form>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <section className="card space-y-2 text-sm lg:col-span-2">
          <h2 className="font-medium">Configuration</h2>
          <dl className="grid grid-cols-[8rem_1fr] gap-y-1.5">
            <dt className="text-muted">Status</dt><dd>{p.status}</dd>
            <dt className="text-muted">Category</dt><dd>{p.category}</dd>
            <dt className="text-muted">Market</dt><dd>{p.market || "—"}</dd>
            <dt className="text-muted">Languages</dt><dd>{p.languages.join(", ") || "—"}</dd>
            <dt className="text-muted">Countries</dt><dd>{p.countries.join(", ") || "—"}</dd>
            <dt className="text-muted">Description</dt><dd className="whitespace-pre-line">{p.description || "—"}</dd>
          </dl>
        </section>

        <section className="card space-y-3 text-sm">
          <h2 className="font-medium">API budget (this month)</h2>
          <div className="h-2 overflow-hidden rounded-full bg-black/10 dark:bg-white/10">
            <div className="h-full bg-accent" style={{ width: `${pct}%` }} />
          </div>
          <p className="text-muted">€{spend.toFixed(2)} of €{budget.toFixed(2)} · measured from recorded usage</p>
        </section>
      </div>

      <section className="card text-sm">
        <h2 className="mb-3 font-medium">Modules</h2>
        <ul className="grid gap-2 sm:grid-cols-2">
          {MODULES.map((m) => (
            <li key={m.name} className="flex items-center justify-between rounded-lg border border-border px-3 py-2">
              <span>{m.name}</span><span className="text-xs text-muted">Phase {m.phase} · not built yet</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="card text-sm">
        <h2 className="mb-3 font-medium">Recent activity</h2>
        {activity?.length ? (
          <ul className="space-y-1">
            {activity.map((a) => (
              <li key={a.id} className="flex justify-between gap-4">
                <span>{a.action}</span>
                <time className="text-muted" dateTime={a.created_at}>{new Date(a.created_at).toISOString().slice(0, 16).replace("T", " ")} UTC</time>
              </li>
            ))}
          </ul>
        ) : <p className="text-muted">Nothing yet.</p>}
      </section>
    </div>
  );
}
