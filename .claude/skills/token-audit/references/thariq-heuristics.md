# Thariq Shihipar's Claude Code Heuristics (Anthropic)

Authoritative guidance from the Anthropic Claude Code team. Our advisory output cites these directly.

Source: Thariq Shihipar, *Using Claude Code: Session Management & 1M Context*
https://claude.com/blog/using-claude-code-session-management-and-1m-context (Apr 15, 2026)

## The 5-option framework — every turn is a branching point

At each turn, Claude Code offers 5 paths. Default is Continue; the other four are context-management tools.

| Situation | Action | Why |
|---|---|---|
| Same task, context still relevant | **Continue** | No-op. |
| Claude went down a wrong path | **Rewind** (double-Esc) | Keeps useful reads, drops failed attempts. Better than "that didn't work, try X" corrections. |
| Session bloated with stale debugging | **`/compact <hint>`** | Lossy summary with intent steering. |
| Starting a genuinely new task | **`/clear`** or new session | Avoid carrying irrelevant context. |
| Next step produces disposable tool output | **Subagent** (Task tool) | Keeps intermediate output in child's context only. |

## Context rot is real

> "Context rot is the observation that model performance degrades as context grows because attention gets spread across more tokens, and older, irrelevant content starts to distract from the current task."

- Not a limit, a degradation gradient. Starts mattering past ~40% of window.
- 1M is a window, not a goal. Fill it and pay twice: dollars + quality.

## Compact proactively, not reactively

> "Due to context rot, the model is at its least intelligent point when compacting."

- Auto-compact fires when it HAS to — exactly when the model is worst at choosing what to keep.
- Compact BEFORE you have to, with a hint: `/compact focus on the auth refactor, drop the test debugging`.
- With 1M context you have runway to compact proactively instead of reactively.

## Rewind > correction

> "Rewind is often the better approach to correction."

Pattern: Claude reads files, makes an attempt, attempt fails.
- Bad path: tell Claude "that didn't work, try X". Now context has the failed attempt + your correction + retry.
- Better path: `/rewind` (double-Esc) to just after the reads, re-prompt with the learnings. Useful reads preserved, failed attempt dropped.

## Subagent mental test

> "Will I need this tool output again, or just the conclusion?"

If only the conclusion → spin up a subagent. Intermediate tool noise stays in the child's context and never pollutes the parent.

Examples Thariq flags:
- Verifying against a spec → subagent
- Reading another codebase to summarize an approach → subagent
- Writing docs from git changes → subagent

## New task = new session (usually)

> "When you start a new task, you should also start a new session."

Exception: related follow-up tasks where file re-reads would waste tokens (e.g., writing docs right after implementing). Then carry the context.

## How to cite in the audit output

When a leak aligns with one of Thariq's principles, include a short quote + attribution. Example:

> ⚠️ 1,646 turns ran past the 400k-token context rot threshold across 9 sessions.
>
> **Thariq (Anthropic Claude Code team):** "Due to context rot, the model is at its least intelligent point when compacting." Compact PROACTIVELY with an intent hint before you need to — not after.
