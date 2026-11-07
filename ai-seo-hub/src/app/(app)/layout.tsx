import { redirect } from "next/navigation";
import { createClient, isSupabaseConfigured } from "@/lib/supabase/server";
import { Sidebar } from "@/components/sidebar";
import { SetupNotice } from "@/components/setup-notice";

export default async function AppLayout({ children }: LayoutProps<"/">) {
  if (!isSupabaseConfigured()) {
    return <main className="mx-auto max-w-lg p-8"><SetupNotice /></main>;
  }
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  const { data: projects } = await supabase
    .from("projects").select("id,name").neq("status", "archived").order("name");

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <Sidebar projects={projects ?? []} email={user.email ?? ""} />
      <main className="min-w-0 flex-1 p-4 md:p-8">{children}</main>
    </div>
  );
}
