# AI SEO Hub — Architecture

## Stack
Next.js 16 (App Router) · TypeScript · Tailwind 4 · Supabase (Postgres, Auth, RLS) · zod validation.
Chosen to match the stated preferences; no alternatives were needed.

## Principles
- **Server-only secrets.** Only the Supabase anon key is public; all other keys are read in server code.
- **RLS everywhere.** Every table has Row Level Security; project-scoped tables use `owns_project(project_id)`.
- **Approval-first.** No SEO change is ever published automatically. AI output is stored as a draft/suggestion and requires explicit approval (Phase 3).
- **No fake data.** UI shows only measured values (e.g. API spend comes from recorded `api_usage`); unbuilt modules are labelled, not faked.
- **Provider abstraction.** AI, keyword data, and Google integrations sit behind interfaces (`src/lib/providers/*`, Phase 2+) so vendors can be swapped.
- **Cost control.** `projects.monthly_budget_eur` is a hard cap; every paid call writes `api_usage` (server/service role only) and must check `month_spend_eur()` first. Responses are cached and crawls are throttled to avoid useless scans.

## Data model (Phase 1)
`projects` (owner-scoped) · `api_usage` (read-only to users) · `activity_log` (approval/audit trail).
Planned: `pages`, `audit_issues`, `keywords`, `content_drafts`, `link_suggestions`, `competitors`, `gsc_metrics`, `jobs`.

## Roadmap
| Phase | Scope |
|---|---|
| 1 ✅ | Auth, projects, dashboard, schema+RLS |
| 2 | Crawler (robots-respecting, rate-limited), SEO audit rules, keyword research (DataForSEO, estimates labelled) |
| 3 | AI provider layer (Claude/OpenAI), assistant, content drafts, internal linking, competitor analysis |
| 4 | Search Console (OAuth), PageSpeed Insights, GA4, DataForSEO |
| 5 | Scheduled audits (cron endpoint + optional n8n webhooks), weekly reports, notifications |
| 6 | Hardening, i18n (EN/FR/RO), perf, deploy |

## Keys needed per phase
P1: Supabase URL + anon key. P2: DataForSEO login (paid, pay-as-you-go). P3: Anthropic and/or OpenAI key (paid per token). P4: Google OAuth client, PageSpeed API key (free quota). P5: n8n instance (optional).
