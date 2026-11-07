import { isSupabaseConfigured } from "@/lib/supabase/server";
import { LoginForm } from "./login-form";
import { SetupNotice } from "@/components/setup-notice";

export const metadata = { title: "Sign in — AI SEO Hub" };

export default function LoginPage() {
  return (
    <main className="min-h-screen grid place-items-center p-6">
      <div className="w-full max-w-sm space-y-6">
        <div>
          <div className="text-xs font-medium tracking-widest text-muted">AI SEO HUB</div>
          <h1 className="mt-2 text-2xl font-semibold">Sign in to your workspace</h1>
        </div>
        {isSupabaseConfigured() ? <LoginForm /> : <SetupNotice />}
      </div>
    </main>
  );
}
