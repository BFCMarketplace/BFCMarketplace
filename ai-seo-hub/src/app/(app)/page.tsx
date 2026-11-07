import Link from "next/link";
import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Dashboard" };

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: projects } = await supabase
    .from("projects").select("id,name,url,category,languages,countries,status,monthly_budget_eur")
    .neq("status", "archived").order("created_at", { ascending: false });

  const spend = new Map<string, number>();
  for (const p of projects ?? []) {
    const { data } = await supabase.rpc("month_spend_eur", { p_project_id: p.id });
    spend.set(p.id, Number(data ?? 0));
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <Link href="/projects/new" className="btn-primary">Add project</Link>
      </div>
      {!projects?.length ? (
        <div className="card max-w-lg space-y-2">
          <p className="font-medium">No projects yet</p>
          <p className="text-sm text-muted">Add your first site or app to start tracking SEO work.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {projects.map((p) => (
            <Link key={p.id} href={`/projects/${p.id}`} className="card block transition-colors hover:border-accent">
              <div className="flex items-start justify-between gap-2">
                <h2 className="truncate font-medium">{p.name}</h2>
                <span className="rounded-full border border-border px-2 py-0.5 text-xs text-muted">{p.status}</span>
              </div>
              <p className="mt-1 truncate text-sm text-muted">{p.url}</p>
              <p className="mt-3 text-xs text-muted">
                {p.category} · {p.languages.join(", ") || "no language"} · {p.countries.join(", ") || "no country"}
              </p>
              <p className="mt-3 text-xs text-muted">
                API spend this month: €{(spend.get(p.id) ?? 0).toFixed(2)} / €{Number(p.monthly_budget_eur).toFixed(2)}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
