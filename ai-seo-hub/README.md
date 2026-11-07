# AI SEO Hub

Centralized, AI-assisted SEO platform for managing many sites/apps from one account.
**Status: Phase 1 (foundation) complete.** See `ARCHITECTURE.md` for the design and roadmap.

## Setup

1. Create a Supabase project (or reuse one — tables are namespaced in `public`; a dedicated project is recommended for data isolation).
2. Apply the schema: run `supabase/migrations/0001_foundation.sql` in the Supabase SQL editor (or `supabase db push` with the CLI).
3. `cp .env.example .env.local` and fill `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
   In Supabase Auth settings, add your site URL and `<site>/auth/callback` to the redirect URLs.
4. `npm install && npm run dev` → http://localhost:3000

## Verify

- `npm run build` — type-checks and builds.
- `./supabase/tests/rls_test.sh` — applies migrations to a throwaway local PostgreSQL and asserts Row Level Security isolation.

## Deploy (Vercel)

Import the repo, set **Root Directory** to `ai-seo-hub`, add the env vars above. The repo root's `index.html` (BFC Marketplace storefront) is unaffected.
`SUPABASE_SERVICE_ROLE_KEY` must only ever be set as a server env var.
