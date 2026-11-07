import Link from "next/link";
import { signOut } from "@/app/(auth)/login/actions";
import { ThemeToggle } from "./theme-toggle";

type P = { id: string; name: string };

export function Sidebar({ projects, email }: { projects: P[]; email: string }) {
  return (
    <aside className="flex w-full flex-col gap-4 border-b border-border p-4 md:h-screen md:w-64 md:shrink-0 md:overflow-y-auto md:border-b-0 md:border-r">
      <Link href="/" className="text-xs font-medium tracking-widest">AI SEO HUB</Link>
      <nav className="flex gap-1 text-sm md:flex-col">
        <Link href="/" className="rounded-lg px-3 py-2 hover:bg-black/5 dark:hover:bg-white/5">Dashboard</Link>
        <Link href="/projects/new" className="rounded-lg px-3 py-2 hover:bg-black/5 dark:hover:bg-white/5">Add project</Link>
      </nav>
      <div className="hidden md:block">
        <div className="px-3 pb-1 text-xs uppercase tracking-wider text-muted">Projects</div>
        <ul className="text-sm">
          {projects.map((p) => (
            <li key={p.id}>
              <Link href={`/projects/${p.id}`} className="block truncate rounded-lg px-3 py-1.5 hover:bg-black/5 dark:hover:bg-white/5">{p.name}</Link>
            </li>
          ))}
          {projects.length === 0 && <li className="px-3 py-1.5 text-muted">None yet</li>}
        </ul>
      </div>
      <div className="mt-auto space-y-2">
        <div className="truncate px-1 text-xs text-muted">{email}</div>
        <ThemeToggle />
        <form action={signOut}><button className="btn-ghost w-full text-left">Sign out</button></form>
      </div>
    </aside>
  );
}
