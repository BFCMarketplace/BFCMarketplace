# Additional optimizations — think beyond the canned detectors

The nine Python detectors catch the patterns that generalize. But every user has unique waste patterns. After presenting audit findings, **brainstorm user-specific optimizations** that the canned detectors can't see.

This file is a prompt, not an exhaustive list. Use it as a starting point, then think harder.

## How to brainstorm

Look at the audit output + what you know about the user + Claude Code token economics. Ask:

- What's unusual about this user's profile that the canned detectors don't capture?
- What does their model mix, session length distribution, tool usage, project mix tell you?
- What language, timing, or cadence patterns jump out?
- Are there patterns that only make sense if you know THIS user's setup?

Then propose 1-3 custom ideas in a "Other ideas worth considering" section at the end of the report.

## Seeds — patterns worth checking per user

These are not auto-detectors (they're too contextual). Consider each for every audit.

### 1. Non-English structural content

**Why:** BPE tokenizers are trained mostly on English. Russian, Chinese, Japanese, Arabic, and other scripts produce 2-3× more tokens per equivalent content. A 4k-token Russian CLAUDE.md is equivalent to a ~1.5k English one.

**Check:** does the user's CLAUDE.md, global CLAUDE.md, or frequently-read structural files contain non-Latin scripts? If yes, suggest:
- Keep structural content (CLAUDE.md, skill descriptions, system instructions) in English. These load on every turn.
- User messages can stay in their preferred language — that's conversational, not structural.
- Output can stay in the user's language — output is cheaper than input in most plans.

**Priority:** high for Russian/Chinese/Japanese/Arabic/Hindi users with large CLAUDE.md files.

### 2. Off-peak shifting for background jobs

**Why:** Thariq Shihipar (Anthropic): *"If you run token-intensive background jobs, shifting them to off-peak hours will stretch your session limits further."* Your 5-hour block starts at your first prompt. If a cron job fires at 9am when you're about to start interactive work, you've now shared the block with the automation.

**Check:** do the user's heavy automations (detected via `recurring_scripts` detector OR hook activity) fire during their working hours?

**Suggest:**
- Shift cron schedules to off-hours (e.g., 3-5am local)
- Run automations as separate authentication / separate `claude-code` invocations if they MUST run during work hours
- Consolidate multiple small cron jobs into one larger batch at off-peak time

**Priority:** medium for anyone with automation running in work hours; high for Max-plan users close to their weekly cap.

### 3. "Why is my sub dying on Monday" — runaway recurring scripts

**Why:** Kieran Klaassen tweeted about burning 91% of his sub by Monday because a cron ran every 5 minutes instead of the intended cadence. This is one of the most common hidden-waste patterns, and the canned `recurring_scripts` detector catches the obvious cases — but not all.

**Check beyond the detector:**
- Launchd agents at `~/Library/LaunchAgents/` and `/Library/LaunchAgents/`
- `crontab -l`
- GitHub Actions scheduled workflows (`.github/workflows/*.yml` with `schedule:` triggers)
- Background scripts in any tool that uses `claude -p` in a loop (e.g., outbound bots, monitoring scripts)
- The user's morning-autopilot equivalent — is it firing at the frequency they think?

**Suggest:** run `launchctl list | grep claude` or `crontab -l`, cross-reference cadence with audit findings.

**Priority:** always check when ccusage shows a jump ≥ 2× weekly average, or when `recurring_scripts` detector surfaces anything.

### 4. Run Claude Code itself on open-source models via Ollama

**Why:** This is bigger than "offload some tasks to Ollama." Ollama's Anthropic-compatible API lets you run the **entire Claude Code CLI** — same tools, same skills, same plugins — backed by open-source models instead of Anthropic's. Zero draw on your subscription.

Source: https://docs.ollama.com/integrations/claude-code

**The command:**
```bash
ollama launch claude --model qwen3.5:cloud
# or, for specific models:
ollama launch claude --model kimi-k2.5:cloud
ollama launch claude --model glm-5:cloud
ollama launch claude --model minimax-m2.7:cloud
```

Cloud models work without a local GPU. Local models (`qwen3.5`, `glm-4.7-flash`) also work if you have the hardware.

**Headless mode** (for cron / scripts):
```bash
ollama launch claude --model kimi-k2.5:cloud --yes -- -p "summarize today's metrics from <file>"
```

**Check:** does the user have cron jobs, hooks, or scheduled skills using `claude -p` that don't actually need Opus? Specifically:
- Morning briefings / digest generation
- Log summarization
- Email/lead triage
- Any deterministic formatting or classification work
- Overnight batch jobs

**Suggest:** keep interactive / high-stakes work on Anthropic-backed Claude Code. Route cron + automation + low-stakes agents to `ollama launch claude --model qwen3.5:cloud` or similar. Same skills, same workflow, different engine.

**Quality caveat:** open-source frontier has closed the gap (~3 months behind Anthropic per recent measurements), but it's still a gap. Don't route code review, deep reasoning, or customer-facing work to OS models until you've sanity-checked quality on YOUR tasks.

**Priority:** high for users with heavy automation load against their weekly cap. A morning autopilot running daily on `qwen3.5:cloud` frees up the equivalent Opus allowance for interactive work.

### 5. Prompt-caching strategy mismatch

**Why:** Anthropic's prompt cache defaults to a **5-minute lifetime**. A 1-hour lifetime exists but requires explicit opt-in via `cache_control: {"type": "ephemeral", "ttl": "1h"}` in the API, and costs 2× base input tokens on write (vs 1.25× for 5-min). Cache reads are 0.1× base input tokens either way.

Source: https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching

So: if the user opens a session, works for 20 minutes, takes a 10-minute coffee break, comes back — cache is dead, next prompt pays full cache-write on the entire system prompt + CLAUDE.md + history.

**Check:** the cache detector (`cache.py`) fires when a session's cache-hit ratio is < 50%. If that fired, this is actionable.

**Suggest (for subscription users — Pro/Max):**
- You can't directly set TTL; Claude Code uses whatever Anthropic ships. The strategy is **behavioral**:
  - Stay engaged during focused work (don't let the 5-min window lapse mid-session)
  - After breaks > 5 min, `/clear` and restart rather than resuming stale sessions (you pay the write either way; restarting is at least clean)
  - Don't edit CLAUDE.md mid-session — it invalidates the prefix cache for the remainder of that session. Edit → commit → start new session.

**Suggest (for API-direct users):**
- Explicitly set `"ttl": "1h"` on high-value prompts where breaks are expected
- Math: 1-hour TTL is worth it if you make ≥ 2 requests against the same prefix per hour
- Verify with actual usage metrics — don't guess

**Priority:** medium for users with cache-hit ratios in the 40-60% range (substantial recoverable waste).

### 6. Desktop / web client blindness

**Why:** the Claude.ai web and Claude Desktop don't show `/cost` or `/context` statuslines. Users who split time between Claude Code and the desktop/web may never see usage until they hit limits.

**Check:** does the user use multiple Claude surfaces?

**Suggest:** use Claude Code for any token-intensive work (because it has telemetry); use desktop/web for brief tasks.

**Priority:** low (informational).

### 7. Skill / plugin over-installation

**Why:** every installed skill's description sits in the `<system-reminder>` available-skills list every turn. 149 skills × 100 tokens/description = 14.9k tokens of per-turn tax. (Already surfaced by the `skills` detector for aggregate bloat, but worth checking individual skills that aren't invocation-justified.)

**Check beyond the detector:** for each skill that has fired < 5 times in the audit window, ask "do I actually need this installed, or can I install on-demand?"

**Suggest:** aggressive skill pruning. Keep the 10-20 you actually use; uninstall the rest. Re-install when needed.

**Priority:** medium-high for heavy plugin users (50+ installed).

### 8. Reading CLAUDE.md that isn't informing answers

**Why:** a large CLAUDE.md that Claude doesn't actually consult is pure tax. Happens when CLAUDE.md has stale content, is too structured/technical to reference naturally, or duplicates info already in the code.

**Check:** do user interactions show Claude repeatedly asking clarifying questions about things ostensibly covered in CLAUDE.md?

**Suggest:** make CLAUDE.md content match how Claude actually reasons. Action-oriented ("When X, do Y") beats declarative ("The system has feature Z"). Review every 2-3 months for staleness.

**Priority:** medium — hard to detect automatically, worth asking the user about.

### 9. Ollama routing for automation-heavy workloads

**Why:** per seed #4, `ollama launch claude --model qwen3.5:cloud` runs the full Claude Code CLI backed by open-source models with zero Anthropic draw. The question per workload: **does this task actually need frontier quality?** If no → route it to Ollama and reclaim the equivalent Anthropic capacity for the work that does.

**This is the FOLLOW-THROUGH for seed #4.** Seed #4 is "Ollama exists and wraps Claude Code." This seed is "for YOUR specific workloads, here's how to decide what to route."

**Signals that a workload is a good Ollama candidate:**
- ✅ Flagged by `recurring_scripts` detector (cron-like cadence)
- ✅ Project where the bottleneck analyzer shows high automation share
- ✅ Deterministic output — formatting, classification, summarization, CSV/JSON shaping
- ✅ Non-interactive — runs unattended, user reviews output later
- ✅ Low-stakes — failure mode is "regenerate" not "ship bad code to prod"
- ✅ User has expressed quality ambivalence ("this doesn't need to be perfect")

**Signals a workload should STAY on Anthropic:**
- ❌ Interactive coding / pair programming
- ❌ Customer-facing content drafting (emails, docs)
- ❌ Code review, security audit, architecture decisions
- ❌ Work that uses Claude's specific tool-use patterns heavily (Read/Edit/Task orchestration matters)
- ❌ User has explicitly said they need frontier quality

**Heuristic: the "would I be okay with this regenerating?" test.** If the worst-case failure is "I notice the output is off and re-run it," Ollama is fine. If the worst-case failure is "this shipped before I noticed," stay on Anthropic.

**Implementation path:**

1. Identify the candidate: pick ONE automation (morning briefing, log summarizer, lead enricher)
2. Clone the script/skill that invokes it
3. Change the invocation:
   ```bash
   # before:
   claude -p "summarize today's metrics from <file>"
   # after:
   ollama launch claude --model qwen3.5:cloud --yes -- -p "summarize today's metrics from <file>"
   ```
4. Run both in parallel for a week (A/B the output quality)
5. If Ollama output is acceptable → cut over. If not → try `kimi-k2.5:cloud` or `glm-5:cloud` (stronger cloud models) before giving up.

**For the audit narrator:** when a user has cron/automation load, include this suggestion with a specific candidate from their actual profile:

```markdown
- [Ollama routing] Your `<project>` has <N> sessions/day with cron-like cadence (see recurring_scripts finding above). This is a prime Ollama candidate — same skills, same workflow:
  `ollama launch claude --model qwen3.5:cloud --yes -- -p "..."`
  Test in parallel for a week; cut over if quality holds.
```

**Priority:** high when `recurring_scripts` fires; medium when bottleneck analyzer shows an automation-heavy project; skip if the user only does interactive work.

## What to do with these ideas in the report

At the end of the standard audit report, add a section:

```markdown
## Other ideas worth considering

(Not auto-detected, but worth a look for your profile:)

- [Language efficiency] Your bayram-os/CLAUDE.md is in English — good. But your daily-log entries are in Russian, and `~/.claude/SOUL.md` is 60% Russian. Consider moving structural rules to English (every-turn load); keep personal voice content in Russian.
- [Off-peak shift] Your `empatika-outreach-agent` scheduled jobs fire at 8am when you're about to start interactive work. Shift them to 3-4am to stop sharing the 5-hour block.
- [Runaway script check] Worth verifying: `launchctl list | grep claude` and `crontab -l`. If anything is set to < hourly cadence, double-check it should be.
```

Keep this section SHORT (3-5 bullets). Prioritize what's likely to matter for THIS user based on their profile. Don't list every seed from this file — curate.

## When to consult external sources

If the user's waste pattern doesn't map to any detector or seed here, **consult** before making stuff up:

- `claude-code-guide` agent — for Claude Code-specific questions (hook API, settings options, skills system)
- https://code.claude.com/en/docs/claude-code/costs — Anthropic's current cost guide
- https://claude.com/blog/using-claude-code-session-management-and-1m-context — Thariq's guide (evergreen for session management)
- ccusage docs (https://ccusage.com/) — for questions about spend measurement

Never fabricate Claude Code features or hook APIs. If you're not sure, ask the user to run a quick diagnostic command, or defer to an external source.
