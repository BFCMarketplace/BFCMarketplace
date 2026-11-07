import { ProjectForm } from "@/components/project-form";
import { createProject } from "../actions";

export const metadata = { title: "Add project" };

export default function NewProjectPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Add project</h1>
      <ProjectForm action={createProject} submitLabel="Create project" />
    </div>
  );
}
