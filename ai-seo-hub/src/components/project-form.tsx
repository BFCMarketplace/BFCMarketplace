"use client";

import { useActionState } from "react";
import { CATEGORIES } from "@/lib/projects";
import type { FormState } from "@/app/(app)/projects/actions";

type Defaults = {
  name?: string; url?: string; description?: string; category?: string; market?: string;
  languages?: string[]; countries?: string[]; monthly_budget_eur?: number;
};

export function ProjectForm({
  action, defaults = {}, submitLabel,
}: {
  action: (s: FormState, f: FormData) => Promise<FormState>;
  defaults?: Defaults; submitLabel: string;
}) {
  const [state, formAction, pending] = useActionState(action, {});
  return (
    <form action={formAction} className="card grid max-w-2xl gap-4">
      <Field label="Name"><input name="name" required defaultValue={defaults.name} className="input" placeholder="InspectAI" /></Field>
      <Field label="Site URL"><input name="url" required defaultValue={defaults.url} className="input" placeholder="https://example.com" /></Field>
      <Field label="Description"><textarea name="description" rows={3} defaultValue={defaults.description} className="input" /></Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Category">
          <select name="category" defaultValue={defaults.category ?? "other"} className="input">
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </Field>
        <Field label="Target market"><input name="market" defaultValue={defaults.market} className="input" placeholder="French craftspeople" /></Field>
        <Field label="Languages (codes, comma-separated)"><input name="languages" defaultValue={defaults.languages?.join(", ")} className="input" placeholder="fr, en" /></Field>
        <Field label="Countries (ISO codes)"><input name="countries" defaultValue={defaults.countries?.join(", ")} className="input" placeholder="FR, BE" /></Field>
      </div>
      <Field label="Monthly paid-API budget (EUR) — hard cap for AI/API spend">
        <input name="monthly_budget_eur" type="number" min={0} step="0.01" defaultValue={defaults.monthly_budget_eur ?? 10} className="input sm:max-w-40" />
      </Field>
      {state.error && <p role="alert" className="text-sm text-danger">{state.error}</p>}
      <div><button disabled={pending} className="btn-primary">{pending ? "Saving…" : submitLabel}</button></div>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return <label className="block text-sm"><span className="text-muted">{label}</span><div className="mt-1">{children}</div></label>;
}
