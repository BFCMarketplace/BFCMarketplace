"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { projectSchema, STATUSES } from "@/lib/projects";

export type FormState = { error?: string };

export async function createProject(_: FormState, formData: FormData): Promise<FormState> {
  const parsed = projectSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) return { error: parsed.error.issues[0].message };
  const supabase = await createClient();
  const { data, error } = await supabase.from("projects").insert(parsed.data).select("id").single();
  if (error) {
    return { error: error.code === "23505" ? "You already have a project with this URL." : "Could not create project." };
  }
  await supabase.from("activity_log").insert({ project_id: data.id, action: "project.created" });
  revalidatePath("/", "layout");
  redirect(`/projects/${data.id}`);
}

export async function updateProject(id: string, _: FormState, formData: FormData): Promise<FormState> {
  const parsed = projectSchema.safeParse(Object.fromEntries(formData));
  if (!parsed.success) return { error: parsed.error.issues[0].message };
  const supabase = await createClient();
  const { error } = await supabase.from("projects").update(parsed.data).eq("id", id);
  if (error) return { error: error.code === "23505" ? "Another project already uses this URL." : "Could not save changes." };
  await supabase.from("activity_log").insert({ project_id: id, action: "project.updated" });
  revalidatePath("/", "layout");
  redirect(`/projects/${id}`);
}

export async function setProjectStatus(id: string, formData: FormData) {
  const status = String(formData.get("status"));
  if (!(STATUSES as readonly string[]).includes(status)) return;
  const supabase = await createClient();
  await supabase.from("projects").update({ status }).eq("id", id);
  await supabase.from("activity_log").insert({ project_id: id, action: `project.${status}` });
  revalidatePath("/", "layout");
}

export async function deleteProject(id: string) {
  const supabase = await createClient();
  await supabase.from("projects").delete().eq("id", id);
  revalidatePath("/", "layout");
  redirect("/");
}
