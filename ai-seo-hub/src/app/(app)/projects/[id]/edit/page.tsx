import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { ProjectForm } from "@/components/project-form";
import { updateProject } from "../../actions";

export const metadata = { title: "Edit project" };

export default async function EditProjectPage({ params }: PageProps<"/projects/[id]/edit">) {
  const { id } = await params;
  const supabase = await createClient();
  const { data: p } = await supabase.from("projects").select("*").eq("id", id).maybeSingle();
  if (!p) notFound();
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Edit {p.name}</h1>
      <ProjectForm action={updateProject.bind(null, id)} defaults={p} submitLabel="Save changes" />
    </div>
  );
}
