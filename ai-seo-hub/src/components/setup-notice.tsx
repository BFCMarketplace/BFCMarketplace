export function SetupNotice() {
  return (
    <div className="card space-y-2 text-sm">
      <p className="font-medium">Supabase is not configured yet.</p>
      <p className="text-muted">
        Copy <code>.env.example</code> to <code>.env.local</code>, fill in
        <code> NEXT_PUBLIC_SUPABASE_URL</code> and <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code>,
        apply <code>supabase/migrations/0001_foundation.sql</code>, then restart. See README.
      </p>
    </div>
  );
}
