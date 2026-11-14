---
name: token-audit
description: "Audit Claude Code token usage and find where tokens are leaking. Reads ~/.claude/projects/*.jsonl transcripts AND Claude desktop cowork (local-agent-mode) sessions locally, inventories settings/hooks/skills/MCPs, runs ccusage for baseline spend, then flags the highest-$-impact leaks (hook bloat, CLAUDE.md bloat, Opus on simple turns, context rot, skill description overhead, Bash anti-patterns, cache miss storms, redundant file reads) with ballpark weekly savings for each. All analysis is local — transcripts never leave the machine. Use when the user asks to audit their Claude Code usage, find where tokens are leaking, review token spend, optimize Claude Code, or understand why they're hitting weekly limits. Triggers: 'token audit', 'why am I hitting limits', 'optimize my Claude Code', 'token leak', 'audit my usage', 'where are my tokens going'."
---

# Token Audit

Find where Claude Code tokens are leaking — and what to fix first.

## When to use this skill

- User asks to audit their token usage or Claude Code costs
- User hitting weekly plan limits (Pro / Max 5x / Max 20x)
- User wonders why a task burned more tokens than expected
- Before/after installing lots of MCPs, plugins, or skills (drift check)
- As a periodic self-review (weekly or bi-weekly)

## What it does

Runs a local-only audit with three inputs:
1. **ccusage** (external CLI, 13k★ open source) — baseline $ totals per day/model/session
2. **JSONL transcripts** — per-turn analysis for patterns ccusage doesn't see. Walks both:
   - `~/.claude/projects/**/*.jsonl` (Claude Code CLI)
   - `~/Library/Application Support/Claude/local-agent-mode-sessions/**/.claude/projects/**/*.jsonl` (Claude desktop "cowork" / local-agent-mode sessions)
3. **Config inventory** — `~/.claude/settings.json`, plugins, skills, MCP servers

Then produces a ranked report of leaks with ballpark weekly $ savings for each.

## How to run it

```bash
python SKILL_DIR/scripts/audit.py --days 7
```

Outputs JSON to stdout. You (Claude) then synthesize a narrative report in the user's language — default English, switch to match the user's current conversation language.

### Language handling

- Default: English
- If the user's recent messages are in another language, write the report in that language
- Technical terms (ccusage, `/compact`, `/rewind`, MCP, CLAUDE.md) stay untranslated

### Report structure (adapt tone, keep sections)

1. **Spend summary** — total, by model, by project, trend vs prior week (from ccusage)
2. **Top bottlenecks** — session / project / file Pareto view: where to look FIRST
3. **Top leaks ranked by weekly savings** — each with:
   - Severity badge (🔴 critical / 🟡 warning / 🟢 suggestion)
   - Evidence (3-5 bullets with numbers)
   - Estimated weekly cost + savings
   - Concrete fix action
   - Thariq citation where applicable
4. **Other ideas worth considering** — 1-3 user-specific suggestions **you (Claude) brainstorm** based on the user's profile. The canned detectors catch patterns that generalize; this section catches patterns unique to this user. Read `references/additional-optimizations.md` for seeds (language efficiency, off-peak shifting, runaway cron check, local-model offloading, cache-TTL strategy, desktop-client blindness, skill pruning) and the brainstorming pattern. Curate 1-3 that actually apply to THIS user — don't list them all. If nothing fits, skip the section entirely.
3. **One fix to apply this week** — single highest-leverage action
4. **Trend / context** — plan-fee share, savings as % of subscription week

## Leak detectors (v1)

| Detector | What it catches | Source |
|---|---|---|
| `tool_schema` | Full MCP tool schemas loaded every turn (~20k tok) — only fires if `ENABLE_TOOL_SEARCH` is OFF | Samarth Gupta audit |
| `hook_bloat` | Session-start / PreCompact hooks re-injecting large output into every session | Novel |
| `claude_md_bloat` | CLAUDE.md > 2k tokens, paid on every turn | Anthropic cost doc (200-line target) |
| `model_selection` | Opus used on short/simple turns where Sonnet would suffice | Novel |
| `context` | Turns past 400k-token context (context rot zone) | Thariq Shihipar, Anthropic |
| `skill_descriptions` | Total skill-description budget per turn (flags fat individual skills + bloated totals) | Novel |
| `bash_antipatterns` | `cat`/`head`/`tail`/`find`/`grep` via Bash instead of native Read/Glob/Grep | Samarth Gupta audit |
| `cache` | Sessions with <50% cache hit ratio (churn-driven cache misses) | Novel |
| `file_reads` | Same file Read 3+ times in one session (rewind candidate) | Thariq Shihipar, Anthropic |

## Prerequisites

- **Node.js 20+** for ccusage (auto-fetched via `npx` — no install needed)
- **Python 3.11+** for the analyzer
- Read access to `~/.claude/projects/`, `~/.claude/settings.json`, and (if you use the Claude desktop app's cowork mode) `~/Library/Application Support/Claude/local-agent-mode-sessions/` (already yours)

If ccusage is unavailable, the audit proceeds without baseline $ totals — detectors still work from JSONLs alone.

## How to frame savings — READ THIS

Most users are on a flat-rate subscription (Pro $20 / Max 5x $100 / Max 20x $200). Reporting "saves $2,200/week" when they pay $200 flat is misleading — they won't "save" that from their pocket. What they actually gain:

1. **Headroom before hitting weekly rate limits** (the real pain for Max users)
2. **Better model quality** (less context rot, fewer cache-miss penalties)
3. **Capacity for more projects on the same plan**
4. **If API user: actual dollar savings**

**Narration rules when writing the report:**

- **Lead with tokens reclaimed per week**, not dollars. "~3.9B tokens/week reclaimable" is honest.
- **Frame as category reduction**: "~80% reduction in Opus spend on this category". Percentages ground the claim in the leak itself.
- **Mention plan capacity** when helpful: "≈ 15% of your Max 20x weekly Opus allowance". Ask the user for their plan only if they haven't said; otherwise don't guess.
- **Put dollar figures in parentheses as context, not the headline**: "(≈ $6,800/week at Anthropic API list pricing — reference only; your subscription is flat-fee)".
- **For the total line at the bottom, use "capacity reclaimable" not "savings"**. If user hits rate limits, optionally add: "this could let you stay on your current plan instead of buying a second subscription".
- **API users are the exception** — for them, dollar savings are direct. If you know they're API-direct, lead with $.

Detectors compute all of:
- `est_weekly_tokens` — honest, plan-neutral primary metric
- `est_weekly_cost_usd` — at API list pricing
- `est_weekly_savings_usd` — what the fix would eliminate (at list pricing)

Plan limits are published in `scripts/cost_model.py` (Pro/Max5x/Max20x ranges). Use `plan_savings_summary(amount, plan)` helper to generate the "≈ X% of subscription-week" phrasing.

**Why we still compute dollars internally:** for ranking. Dollar impact is the cleanest way to prioritize leaks across heterogeneous categories.

## What the skill does NOT do

- Does not edit your CLAUDE.md, settings.json, hooks, or skills automatically
- Does not send transcripts, settings, or any content over the network
- Does not authenticate to Anthropic or any external service
- Does not analyze other coding assistants (Codex, Cursor, Aider) in v1 — see roadmap

## Recommended invocation pattern

1. Run `audit.py --days 7`
2. Read the JSON output
3. Present findings in the user's language as a tight report (see "Report structure" above)
4. **After presenting**, offer to walk through fixes inline — no separate subcommand:
   > "Want me to apply any of these? I can: (a) add the Sonnet default to `<project>/.claude/settings.json`, (b) trim the oversized CLAUDE.md, (c) enable `ENABLE_TOOL_SEARCH`. Pick any."
   - For each fix the user picks: show the exact diff, ask y/N, back up the file with a timestamped copy, then write.
   - Never modify settings.json, hooks, or CLAUDE.md without explicit per-fix confirmation.
5. **If the user wants real-time prevention** (they ask "how do I stop this from happening again?"), propose user-specific hooks. See `references/hook-design.md` for principles and patterns. Critical rules:
   - Consult the `claude-code-guide` agent or https://code.claude.com/en/docs/claude-code/hooks for the current hook API before writing any hook code — the spec changes, don't rely on memory
   - Design hooks matched to THIS user's actual waste profile (project, thresholds, leak type), not generic one-size-fits-all hooks
   - Informational at objective thresholds, never prescriptive on tool choice
   - Always show the exact script + settings.json diff, per-hook y/N, kill-switch included
6. Re-run after 1-2 weeks to measure delta

## Roadmap (v2+, not shipped)

- **User-specific hook designer** — guidance for Claude to propose hooks matched to the user's audit profile (principles already in `references/hook-design.md`; surface this in step 5 of the invocation pattern)
- **Cross-assistant support**: Codex (`AGENTS.md`, reasoning_effort), Aider (`.aider.conf.yml`, map-tokens), Cursor (Auto vs API pool routing)
- **More detectors**: extended-thinking budget runaway, agent-team 7x multiplier, `.claudeignore` absence, plan-mode underuse, stale-session resume, pasted-blob vs `@file` mentions
- **Auto-weekly cron digest** (to Telegram or email)
- **Trend tracking**: store audit results over time, show week-over-week deltas

## Authoritative references

Baked into the analysis:
- Thariq Shihipar (Anthropic Claude Code team), *Using Claude Code: Session Management & 1M Context* — https://claude.com/blog/using-claude-code-session-management-and-1m-context
- Anthropic cost management doc — https://code.claude.com/en/docs/claude-code/costs
- Samarth Gupta, *anthropic isn't the only reason you're hitting claude code limits* — https://medium.com/@samarthgupta1911
- ccusage by @ryoppippi — https://github.com/ryoppippi/ccusage (13k★)

## Privacy & safety

- All analysis is **local**. No network calls except the optional `npx ccusage@latest` fetch.
- Transcript content (tool result payloads, file contents, user messages) is parsed for size/counts/tool-names only — never retained, never transmitted.
- Settings.json is read-only. Nothing is written.
- Detectors summarize patterns; specific content (e.g., customer names, code) is not extracted into the report.
