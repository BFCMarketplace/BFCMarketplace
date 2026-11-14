# Leak Taxonomy

Canonical list of detectable token leaks, with examples and detection logic. Used by the skill for ranking and by Claude when narrating findings.

## 1. `tool_schema:bloat` — Tool-schema dumping (CRITICAL if active)

**What it is:** When `ENABLE_TOOL_SEARCH` is off (legacy Claude Code setting), full JSON schemas of every registered tool are included in the system prompt on every turn. Samarth Gupta measured 20k tokens on a standard setup; tool-search on drops this to ~6k.

**Why it hurts:** Per-turn tax that scales with MCP count. Zero value when the vast majority of tools aren't used this turn.

**Detection:** Read `env.ENABLE_TOOL_SEARCH` from settings.json; if absent or explicitly false, flag.

**Fix:** Add `"ENABLE_TOOL_SEARCH": "auto:5"` to `~/.claude/settings.json` → `env`.

## 2. `hook_bloat:*` — Session-start / PreCompact hook output

**What it is:** Hooks that emit large content (briefings, inventories, CRM dumps) get injected into context on every session. If you open 5 sessions a day, a 22 KB hook briefing costs 110 KB of context daily.

**Why it hurts:** Linear in session count. Common culprits: SessionStart hooks that dump daily briefings, inventory snapshots, or CRM status on every session.

**Detection:** Count `hook_success` attachments per `hookName` in JSONL. Weight by content size.

**Fix:** Move large or slow-changing data into a file the agent reads on demand. Cache expensive lookups. Use matchers to restrict firing.

## 3. `claude_md:bloat` — CLAUDE.md oversized

**What it is:** CLAUDE.md > 2k tokens — Anthropic's cost doc recommends under 200 lines.

**Why it hurts:** Every turn, every session, forever. 5k tokens × 100 turns/week = 500k tokens/week.

**Detection:** Stat global + per-cwd + parent CLAUDE.md files; flag > 2k tokens (warn), > 5k (critical).

**Fix:** Trim to who/what/hard-rules. Move playbooks into separate files, reference via `@filename` or skill descriptions.

## 4. `model_selection:opus_on_simple` — Opus on short turns

**What it is:** Opus used on turns where the output was < 1k tokens. Sonnet would have produced the same result for ~1/5 the cost.

**Why it hurts:** 5× multiplier on every applicable turn.

**Detection:** For each Opus turn in JSONL, check output_tokens. Count turns below threshold.

**Fix:** Set default model to Sonnet in `.claude/settings.json`. Explicitly escalate to Opus only for planning, hard reasoning, or complex refactors. Consider a Sonnet sub-agent for lookups.

## 5. `context:late_compact` — Context rot

**What it is:** Turns running with context > 400k tokens. Thariq Shihipar (Anthropic): "Due to context rot, the model is at its least intelligent point when compacting."

**Why it hurts:** Two costs — dollar cost of re-feeding large context + quality cost of degraded attention.

**Detection:** For each assistant turn, check `usage.cache_read + cache_write + input` vs threshold.

**Fix:** `/compact <hint>` proactively. `/rewind` after failed attempts. `/clear` for new tasks. See `thariq-heuristics.md`.

## 6. `skills:description_bloat` — Skill descriptions inflated

**What it is:** Every available skill's `description:` frontmatter is loaded into every turn's `<system-reminder>`. Scales linearly with installed skills.

**Why it hurts:** Unused but installed skills still tax every turn.

**Detection:** Sum description bytes across all SKILL.md in user, plugin, and project scopes.

**Fix:** Tighten descriptions under 500 tokens each. Disable skills you don't actually use. Move long setup detail into the skill body (loads only on invocation).

## 7. `bash:antipatterns` — Bash commands with native equivalents

**What it is:** Shelling out via Bash for `cat`, `head`, `tail`, `find`, `grep`, `rg`, etc., when Read / Glob / Grep tools exist and stream ranged output.

**Why it hurts:** Bash dumps full output into context; native tools truncate and paginate.

**Detection:** Count Bash tool calls whose first token matches a denylist.

**Fix:** Add to `~/.claude/CLAUDE.md`: "Prefer Read / Glob / Grep over `cat` / `find` / `grep`. Native tools stream ranged output; Bash pipes dump everything."

## 8. `cache:miss_storms` — Session cache churn

**What it is:** Sessions with < 50% cache hit ratio are paying cache-write pricing (5-6× cache-read) on most input. Usually caused by mid-session CLAUDE.md edits, project switching, or plugin load/unload.

**Detection:** Per-session `cache_read / (cache_read + input)`. Flag below threshold, ignore tiny sessions.

**Fix:** Start a new session after big CLAUDE.md changes. Don't switch projects mid-session. Stabilize plugin config.

## 9. `file_reads:redundant` — Same file Read 3+ times

**What it is:** Same file path Read multiple times in one session. Usually indicates an attempt → failure → retry pattern where `/rewind` would have preserved the useful read.

**Detection:** Group Read tool calls by `input.file_path` per session; flag path with count ≥ 3.

**Fix:** `/rewind` (double-Esc) after failed attempts instead of "that didn't work, try X". For sticky references, add a pointer in CLAUDE.md so Claude doesn't re-discover them.

---

## Severity scale

| Severity | Criterion | Action |
|---|---|---|
| 🔴 critical | est_weekly_savings ≥ $5 | Fix this week |
| 🟡 warning | $1 ≤ est_weekly_savings < $5 | Fix when convenient |
| 🟢 suggestion | est_weekly_savings < $1 | Nice-to-have |

## Not in v1 (see SKILL.md roadmap)

`thinking:budget_runaway`, `agent_teams:multiplier`, `claudeignore:missing`, `claude_md:pasted_blobs`, `stale_session:resume`, `plan_mode:underuse`, `bad_autocompact`, `desktop:no_statusline`.
