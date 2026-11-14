# Designing User-Specific Hooks

Rather than shipping canned "sentinel hooks," this skill teaches you — Claude — how to design hooks matched to THIS user's actual waste profile.

**Core principle:** the audit tells you *what* is wasting tokens. You then design a hook that prevents *that specific waste pattern* for *this specific user*.

## When to propose hooks

**After** the user has reviewed the audit and accepted (or declined) the one-shot config/CLAUDE.md fixes. Hooks are a second-tier suggestion for users who want real-time prevention, not a default push.

Good triggers:
- User says "how do I prevent this from happening again?"
- User has tried a fix, it helped, they want more
- User asks "can Claude Code warn me about X?"

Don't propose hooks:
- On first run (too much at once)
- For waste categories the user doesn't actually have (e.g., no Bash-anti-pattern leaks → don't suggest a Bash hook)

## Before you write any hook code

**Consult the current Claude Code hook docs.** The hook API changes and this reference file may be stale. Two ways:

1. **Preferred:** call the `claude-code-guide` agent with a specific question, e.g., "What's the current JSON contract for PreToolUse hook responses? Does `permissionDecision: 'deny'` still block, and what fields does the hook receive on stdin?"

2. **Fallback:** fetch https://code.claude.com/en/docs/claude-code/hooks (the authoritative spec). Version may have shifted since 2026-04.

Never write a hook from memory — always verify the event names, input/output contract, and state-persistence story before proposing code.

## Design principles (don't break these)

1. **Informational at objective thresholds, not prescriptive on tool choice.** Fire when a measurable state crosses a threshold (context > 400k, turn > 150). Don't fire based on heuristics about what Claude "should have" done (e.g., blocking `Bash: cat`). Objective beats heuristic every time — no false positives.

2. **Warn, don't block.** Use `systemMessage` or context-injecting stdout to put information in front of Claude. Let Claude decide what to do. Blocking tool calls frustrates the agent and produces weird retry loops.

3. **Silent by default.** A hook that fires every turn is noise. A hook that fires once a week at exactly the right moment is a gift. Keep thresholds high.

4. **Kill-switchable.** Every hook must have an instant escape valve. Options:
   - Env var: `TOKEN_AUDIT_SENTINEL=off` — script checks at top, exits 0 if set
   - Matcher scoping: only fire in specific projects where the leak lives
   - Keep the hook script self-contained in `~/.claude/hooks/token-audit-*` so uninstall is a file delete + settings.json patch

5. **Scoped to the leak.** If only `onsa-gtm` has context rot, the hook should only fire in that project's cwd. Don't make every user with one noisy project suffer global hooks.

6. **Never auto-install.** Show the user:
   - The exact hook script (full source)
   - The exact settings.json diff
   - Ask y/N for each hook separately
   - Back up settings.json with timestamp before writing
   - Explain the uninstall command

## Mapping leaks to hook ideas

Use this table as a starting point, not a prescription. Customize based on the user's actual thresholds and projects.

| Detected leak | Hook pattern | Event | Key check |
|---|---|---|---|
| Context rot (many turns > 400k) | Context watchdog | `PostToolUse` (async) | Track per-session turn counter; emit `systemMessage` at the specific threshold that matches the user's over-400k pattern |
| Opus on simple turns in specific projects | Project-scoped SessionStart tip | `SessionStart` | Read audit JSON; if `cwd` matches a flagged project, prepend "this project's simple tasks should default to Sonnet" |
| CLAUDE.md bloat unaddressed | One-time SessionStart nag | `SessionStart` | Emit reminder if the bloated file's mtime hasn't changed since audit flagged it; self-disable after trim |
| Chronic redundant reads | Read-counter per session | `PostToolUse` matcher=Read | Count Read calls per file path; when same path hit 3+ times, emit "consider /rewind to preserve the original read" |
| Hook-bloat (user's own hook too big) | Don't use a hook — fix the existing hook | — | Irony. Just trim the source hook output. |

## Example pattern: project-scoped context watchdog

Say the audit shows context rot concentrated in `onsa-gtm`. Don't install a global watchdog — scope it:

```bash
#!/bin/bash
# ~/.claude/hooks/token-audit-watchdog.sh
# Fires only when cwd is onsa-gtm AND turn count crosses the user's
# profile threshold (150 turns in their audit data).

[ "${TOKEN_AUDIT_SENTINEL:-on}" = "off" ] && exit 0

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd // ""')
SID=$(echo "$INPUT" | jq -r '.session_id // ""')

# Scope: only fire in the specific project(s) flagged by the audit
case "$CWD" in
  */onsa-gtm*) ;;
  *) exit 0 ;;
esac

COUNTER_DIR="${CLAUDE_PLUGIN_DATA:-$HOME/.claude/token-audit}/session-counters"
mkdir -p "$COUNTER_DIR"
F="$COUNTER_DIR/$SID.txt"
COUNT=$(cat "$F" 2>/dev/null || echo 0)
COUNT=$((COUNT + 1))
echo "$COUNT" > "$F"

# Only emit at the user's audited threshold (150 for onsa-gtm heavy-use profile)
if [ "$COUNT" -eq 150 ]; then
  jq -n '{systemMessage: "🔔 onsa-gtm session crossed 150 turns (your audit showed context rot past this point). Thariq: /compact focus on <current scope>, or /clear if starting a fresh task."}'
fi

exit 0
```

Note the choices:
- Kill-switch at the top (`TOKEN_AUDIT_SENTINEL=off`)
- Project-scoped via cwd match
- Threshold tuned to the specific user's audit data (150 for Bayram-style heavy use, different for others)
- Self-contained data dir (clean uninstall)
- Silent except at the one threshold

## Uninstall story

Whatever you install, show the user how to remove it. Example:

```bash
# Remove hook script
rm ~/.claude/hooks/token-audit-watchdog.sh

# Remove from settings.json — back up first
cp ~/.claude/settings.json ~/.claude/settings.json.bak.$(date +%s)
# then edit settings.json to remove the hooks entry (show them the diff)
```

Or in a single env-var kill-switch: `export TOKEN_AUDIT_SENTINEL=off` → no code change needed.

## What to NEVER do

- Never write hooks that exfiltrate data (no curl/network calls)
- Never install hooks that read transcript contents (stick to metadata: sizes, counts, cwd)
- Never write hooks that modify files (settings.json, CLAUDE.md, anything) — read-only
- Never silently replace existing hooks — if the user has a `SessionStart` hook configured, compose alongside it, don't overwrite
- Never install hooks at the global level when the leak is project-specific
