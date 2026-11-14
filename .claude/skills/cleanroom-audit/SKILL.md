---
name: audit
description: Audit the plugins, MCP servers and skills loaded in this project, switch off the irrelevant ones for this project only, ask about borderline ones four at a time, report measured token savings, and list startup load errors with fixes. Arguments - restore, --dry-run.
argument-hint: "[--dry-run] [restore]"
disable-model-invocation: true
allowed-tools: Read, Glob, Grep
---

# Cleanroom audit

Trim this project's always-on context. Classify every switchable plugin, MCP server and skill against this project, switch off the clearly irrelevant ones, ask the user about the borderline ones four per AskUserQuestion call, then report the measured savings.

Switches go to `<project>/.claude/settings.local.json` (this project only, reversible) and take effect in the next session. User-scope changes happen only in Step 8, only after the user says yes.

## Running commands

- Use the Bash tool. If there is no Bash tool (Windows without Git for Windows), tell the user the audit needs Git Bash and stop.
- Run every command from the project root (the session's working directory). Copy commands exactly; change only `<placeholders>` and `sleep 20`.
- Set the Bash timeout to 300000 ms for the Step 1 and Step 5 commands. Each takes 25-50 s.
- Measuring runs start `claude -p` and send `/context`, a local command: no model call, no billed tokens. The `GUARD` line proves it.
- All state lives in `<project>/.claude/cleanroom/`. Step 1 writes a `.gitignore` there that ignores the folder.
- The Step 1 run also writes Claude Code's debug log, with MCP lines filtered out, to `.claude/cleanroom/before.debug`. The same command prints only the plugin and skill error lines and deletes the log. Never Read or print the log.
- Never run `claude plugin list --json`, `claude mcp list`, `claude mcp get` or `/doctor` yourself, and never read Claude Code's global config file in the home folder (only the settings files named in this skill). They print server configuration or call the model.
- Before Step 1, tell the user: the audit runs two shell commands (measure now, forecast later), then edits the settings file and its undo log, and each step asks for permission.

## Arguments: `$ARGUMENTS`

- Contains `restore`: follow Restore at the end. Stop after it.
- Contains `--dry-run`: never edit or create settings files or undo logs. Classify, ask, forecast, and label the summary "dry run, nothing changed". In Step 8, show the guidance only.

## Step 1: Measure

Run:

```bash
mkdir -p .claude/cleanroom && printf '*\n' > .claude/cleanroom/.gitignore && rm -f .claude/cleanroom/before.debug .claude/cleanroom/latest
(sleep 20; printf '%s\n' '{"type":"user","message":{"role":"user","content":"/context"}}') | claude -p --input-format stream-json --output-format stream-json --verbose --no-session-persistence --permission-mode default --debug='!mcp' --debug-file .claude/cleanroom/before.debug > .claude/cleanroom/before.jsonl 2> .claude/cleanroom/before.err
grep -q '"type":"result"' .claude/cleanroom/before.jsonl || { echo "NO RESULT"; head -20 .claude/cleanroom/before.err; }
awk '
function tok(x) { gsub(/[ ~,]/, "", x); if (x ~ /^</) return 10; m = 1; if (x ~ /k$/) { m = 1000; sub(/k$/, "", x) } return x * m }
function flush(  i, s) { if (!k) return; print "| Server | Tools | Names in context (est.) | Schemas on demand | Sample tools |"; print "|---|---|---|---|---|"
  for (i = 1; i <= k; i++) { s = ord[i]; printf "| %s | %d | ~%d | %d | %s |\n", s, n[s], nm[s], sc[s], smp[s] } print ""; k = 0 }
function row(L,  f, s, t) {
  if (L ~ /^### /) { if (mcp) flush(); mcp = (L ~ /^### MCP Tools/); sk = (L ~ /^### Skills/) }
  if (sk && L ~ /^\| / && L !~ /^\| Skill \|/) { skills++; if (L ~ /< 20/) nameonly++ }
  if (mcp && L ~ /^\| mcp__/) { split(L, f, "|"); s = f[3]; gsub(/ /, "", s); t = f[2]; gsub(/ /, "", t)
    if (!(s in n)) ord[++k] = s; n[s]++; nm[s] += int((length(t) + 2) / 3) + 1; sc[s] += tok(f[4])
    if (n[s] <= 3) smp[s] = smp[s] (n[s] > 1 ? ", " : "") substr(t, length(s) + 8); return }
  if (mcp && L ~ /^\|/) return
  print L
}
/"subtype":"init"/ {
  if (match($(0), /"mcp_servers":\[[^]]*\]/)) print substr($(0), RSTART, RLENGTH)
  if (match($(0), /"plugins":\[[^]]*\]/)) print substr($(0), RSTART, RLENGTH)
  r = $(0); p = ""; while (match(r, /"name":"[^"]*","status":"pending"/)) { p = p " " substr(r, RSTART + 8, RLENGTH - 28); r = substr(r, RSTART + RLENGTH) }
  print "PENDING:" (p == "" ? " none" : p)
  r = $(0); e = ""; while (match(r, /"name":"[^"]*","status":"(failed|needs-auth)"/)) { q = substr(r, RSTART + 8, RLENGTH - 9); sub(/","status":"/, " (", q); e = e (e == "" ? " " : "; ") q ")"; r = substr(r, RSTART + RLENGTH) }
  print "MCP_ERRORS:" (e == "" ? " none" : e)
}
/"type":"result"/ {
  g = "GUARD"; if (match($(0), /"num_turns":[0-9]+/)) g = g " " substr($(0), RSTART, RLENGTH)
  if (match($(0), /"total_cost_usd":[0-9.eE+-]+/)) g = g " " substr($(0), RSTART, RLENGTH); gsub(/"/, "", g); print g
  s = substr($(0), index($(0), "\"result\":\"") + 10); len = length(s); L = ""
  for (j = 1; j <= len; j++) { c = substr(s, j, 1)
    if (c == "\\") { j++; c = substr(s, j, 1); if (c == "n") { row(L); L = ""; continue } if (c == "t") c = " " }
    else if (c == "\"") break
    L = L c }
  row(L); if (mcp) flush()
  print "SKILLS listed=" skills + 0 " name_only=" nameonly + 0
}' .claude/cleanroom/before.jsonl
echo "## Recent commits"; git log -12 --format=%s 2>/dev/null
echo "## Switched off in this repo"; cat .claude/settings.json .claude/settings.local.json 2>/dev/null | grep -Eo '"[^"]*": *("off"|false)|"serverName": *"[^"]*"' | sort -u | wc -l
echo "## Switched off in 2+ sibling repos (repos, key)"; here=$(basename "$PWD")
for d in ../*/; do [ "$d" = "../$here/" ] && continue; cat "$d.claude/settings.json" "$d.claude/settings.local.json" 2>/dev/null | grep -Eo '"[^"]*": *("off"|false)|"serverName": *"[^"]*"' | tr -d ' ' | sort -u; done | sort | uniq -c | sort -rn | grep -v '^ *1 ' | head -80
echo "## Load errors"; f=.claude/cleanroom/before.debug; k='hooks\.json|manifest|Failed to load|failed to parse|path not found|escapes plugin'
grep -E '\[ERROR\] ' "$f" 2>/dev/null | grep -E "$k" | sed -E 's/^.*\[ERROR\] //; s#[a-z]+://[^ ]*#<url>#g' | cut -c1-300 | sort -u
echo "Other logged errors: $(grep -E '\[ERROR\] ' "$f" 2>/dev/null | grep -v -E "$k|CA certs" | wc -l)"
pl=$(claude plugin list 2>/dev/null); for p in $(grep -E '\[ERROR\] ' "$f" 2>/dev/null | grep -E "$k" | sed -nE 's/^.*\[ERROR\] (Plugin )?([A-Za-z0-9._-]+)(:| has).*/\2/p' | sort -u); do echo "== $p"; printf '%s\n' "$pl" | grep -A3 -F " $p@" || echo "   not installed"; done
rm -f "$f" .claude/cleanroom/latest
```

Then:
- `NO RESULT`: show the error lines and stop.
- `GUARD` shows `num_turns` or `total_cost_usd` other than 0: stop. Tell the user `/context` reached the model, so the measurement is invalid.
- `PENDING` lists servers: run the whole Step 1 command once more with `sleep 45` instead of `sleep 20`, and use `sleep 45` in Step 5 too. Servers still pending after that: note them; their cost is unknown.
- `MCP_ERRORS` lists servers, or `## Load errors` has lines: handle them in Step 2a.
- `Other logged errors` above 0: say so in one line in the summary; `claude --debug` shows them.
- Read the whole output. It holds the `mcp_servers` and `plugins` lists, the `/context` report with one row per MCP server, the `SKILLS` counts, recent commits, the account-wide counts, and the load errors.

## Step 2: Build the candidate list

Assign refs in this order: `P1..` plugins, `M1..` MCP servers, `S1..` skills.

- `Skill listing: FULL` when `SKILLS` shows `name_only` above 0. Then every skill's token saving is 0: the remaining skills expand into the freed space.
- Plugins: each `plugins` entry, except sources ending in `@inline` (loaded with `--plugin-dir`) or `@builtin`, and except `cleanroom` itself. Key: the `source` value (`name@marketplace`). Cost: its MCP servers' `Names in context` (`mcp_servers` entries with source `plugin` named `<name>` or `plugin:<name>:...`), plus its agents (Custom Agents rows `<name>:...`), plus its skills (Skills rows with Source `Plugin (<name>)`, 0 while the listing is FULL). Hooks are not counted.
- MCP servers: each `mcp_servers` entry with source other than `plugin`. Key: `name` exactly as listed (for example `claude.ai HubSpot`). Cost: `Names in context` from the server row whose Server equals the name with every character other than letters, digits, `_` and `-` replaced by `_`. A failed, pending or tool-less server costs 0 here; still classify it.
- Skills: Skills rows with Source `User`, `Project` or `claude.ai sync`. Key: the name; for `claude.ai sync` rows use `anthropic-skills:<name>`. Cost: the row's tokens, or 0 while the listing is FULL.
- `ask-only`: project skills (Source `Project`), MCP servers with source `project` or `local`, and plugins enabled in `.claude/settings.json`. Never auto-remove these.
- Not switchable (summary only): Built-in skills, custom agents, memory files, `@inline` and `@builtin` plugins.
- Every cost here except the final forecast is an estimate. MCP server instructions (`MCP server instructions` row) are not split per server.

Gather descriptions and project signals with Read, Glob and Grep only:
- Skill descriptions: Grep `^description:` in `**/SKILL.md` under `~/.claude/skills` (use the absolute home path), under `.claude/skills`, and under each plugin `path`. Plugin descriptions: Read `<path>/.claude-plugin/plugin.json`.
- MCP servers: judge by name and the `Sample tools` column.
- Project: Glob the top level and `**/*` (ignore `.git`, `.claude`, `node_modules`); Read manifests (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `*.csproj`, `Gemfile`, `composer.json`, `pom.xml`), `CLAUDE.md` or `AGENTS.md`, and the README. Use the recent commits from Step 1.
- `EMPTY PROJECT`: fewer than 3 files outside `.git` and `.claude`.
- Existing switches: Read `.claude/settings.local.json` and `.claude/settings.json` if they exist.

## Step 2a: Load errors

Assign refs `E1..` to each `MCP_ERRORS` server and each `## Load errors` line. Record who owns the fix (the user, a plugin author, or the server) and the fix.

- Never edit, move or delete files under `~/.claude/plugins`. Never run `claude plugin update`, `uninstall` or `marketplace` commands; print them for the user. Never fetch repository or issue pages; print the URL.
- `<plugin>: hooks.json: unknown keys ... ignored`: Claude Code ignores those keys and still loads the hooks. It reads the hooks file of every installed plugin, so switching the plugin off does not clear the warning. Fixes, in order:
  - Update: `claude plugin marketplace update <marketplace>`, then `claude plugin update <plugin>@<marketplace>`.
  - If the user does not use it: `claude plugin uninstall <plugin>@<marketplace> --scope <Scope>`. Say that this deletes the plugin's data unless `--keep-data` is added, and that `restore` cannot undo it.
  - Report it: Read `~/.claude/plugins/cache/<marketplace>/<plugin>/<Version>/.claude-plugin/plugin.json` (Version and Scope come from the `== <plugin>` block) and give its `repository` or `homepage` URL.
- `Plugin <name> has a corrupt manifest`, `Failed to load`, `path not found`, `escapes plugin directory`: parts of the plugin are missing or broken. Same fixes. `not installed` means a folder loaded with `--plugin-dir`; tell the user to fix that folder.
- `[skills] YAML frontmatter in <path> failed to parse`: Read the first 10 lines of `<path>` and name the cause (usually an unquoted `: ` inside `description`; wrap the value in double quotes). Show the corrected line as text. When `<path>` is under `~/.claude/skills` or this project's `.claude/skills` and the user asks, apply it with the Edit tool. When it is under `~/.claude/plugins`, give the plugin author's URL instead. Switching the skill off does not clear this error.
- MCP server `failed`: classify it like any other server. Switching it off also stops the failed connection at startup. If it stays on: `/mcp`, select the server, read its error, then Reconnect.
- MCP server `needs-auth`: if it stays on, `/mcp`, select it, Authenticate. For a `claude.ai` connector, connect it on claude.ai under Settings > Connectors.

## Step 3: Classify every candidate

Put each ref in exactly one bucket.

- `remove`: serves a different domain or workflow than this project, with no plausible use during work here. Examples: video-editing skills in a backend API repo; a CRM connector in a firmware repo; cloud-provider skills for a provider the project does not use.
- `ask`: could plausibly help, is general-purpose, or you are not sure.
- `keep`: a concrete project signal ties it to this work (a dependency, file type, CLAUDE.md instruction, commit subject, folder). Note the signal.

Rules:
- Never put an `ask-only` ref in `remove`.
- `EMPTY PROJECT`: put nothing in `remove`; tell the user why; offer only `ask` items.
- Keep or ask, never remove, anything the user's CLAUDE.md files or memory files reference (a named skill, tool, or workflow). Read the memory files listed in the report when in doubt.
- Keep general dev tools that fit any code repo (code review, git, docs lookup) unless the project clearly is not code.
- Skill listing FULL: still put clear-mismatch skills in `remove` (they crowd the listing). For a borderline skill, default to `keep`; put it in `ask` only if it could trigger wrongly during work here (its description matches tasks this project does, but it serves another purpose).
- Token size never decides relevance. It only orders the questions.
- Between `remove` and `ask`, pick `ask`.

Show the `remove` set as a compact table: ref, kind, name, est. tokens, one-line reason. For skills while the listing is FULL, write `0 (frees listing room)`. Group by kind if more than 15 rows. If `remove` is empty, say so in one line. The switches are written in Step 6.

## Step 4: Ask about the `ask` set, four at a time

- Order: plugins and MCP servers first (largest est. tokens first), then skills.
- Send AskUserQuestion with 4 questions per call (fewer only in the last batch). Repeat until every `ask` ref has been asked. Before each call, print `Batch N of M`.
- One question per item, `multiSelect: false`:
  - `header`: item name, at most 12 characters (strip `anthropic-skills:`, `claude.ai ` and `@marketplace`).
  - Plugin or MCP server, or a skill when the listing fits:
    - `question`: `<Kind> <name> (~N tokens per request): <what it does, one clause>. <why it might or might not matter here>. Switch it off for this project?`
    - `Switch off` description: `Saves ~N tokens per request in this project. /cleanroom:audit restore undoes it.`
  - Skill while the listing is FULL:
    - `question`: `Skill <name>: <what it does, one clause>. <how it could trigger wrongly here>. Switch it off for this project? (No token saving: the skill listing is full.)`
    - `Switch off` description: `Frees description room for the other skills; no token saving. /cleanroom:audit restore undoes it.`
  - MCP server listed in `MCP_ERRORS`: add `It failed to connect at startup.` or `It needs sign-in.` to the question.
  - `Keep` description: the most plausible use in this project.
  - Put your recommendation first with ` (Recommended)` appended to its label. While the listing is FULL, recommend `Keep` for skills unless wrong triggering is likely.
- Never state a token saving for a skill while the listing is FULL.
- Free-text ("Other") answers: act on clear intent; otherwise keep.
- If the user dismisses a batch, stop asking and keep everything not yet answered.

## Step 5: Forecast

The plan is every ref in `remove` plus every ref the user answered `Switch off`. If the plan is empty, skip to Step 7 and say the harness already fits this project.

Build two settings overlays from the plan's keys:
- `all`: every planned item.
- `nonskill`: only the planned plugins and MCP servers (`{}` if none).
- Format: `{"enabledPlugins": {"<plugin key>": false}, "deniedMcpServers": [{"serverName": "<mcp key>"}], "skillOverrides": {"<skill key>": "off"}}`. Omit empty sections.

Run, with each overlay on one line in place of its placeholder:

```bash
cat > .claude/cleanroom/overlay-all.json <<'JSON'
<all overlay>
JSON
cat > .claude/cleanroom/overlay-nonskill.json <<'JSON'
<nonskill overlay>
JSON
for k in all nonskill; do (sleep 20; printf '%s\n' '{"type":"user","message":{"role":"user","content":"/context"}}') | claude -p --input-format stream-json --output-format stream-json --verbose --no-session-persistence --permission-mode default --settings ".claude/cleanroom/overlay-$k.json" > ".claude/cleanroom/after-$k.jsonl" 2>/dev/null & done; wait
for f in before after-all after-nonskill; do echo "== $f"; awk '
/"subtype":"init"/ { r = $(0); p = ""; while (match(r, /"name":"[^"]*","status":"pending"/)) { p = p " " substr(r, RSTART + 8, RLENGTH - 28); r = substr(r, RSTART + RLENGTH) } print "PENDING:" (p == "" ? " none" : p) }
/"type":"result"/ { g = "GUARD"; if (match($(0), /"num_turns":[0-9]+/)) g = g " " substr($(0), RSTART, RLENGTH)
  if (match($(0), /"total_cost_usd":[0-9.eE+-]+/)) g = g " " substr($(0), RSTART, RLENGTH); gsub(/"/, "", g); print g
  bs = "\\"; n = split($(0), a, bs bs "n")
  for (i = 1; i <= n; i++) { L = a[i]; if (L ~ /^### /) { cat = (L ~ /Estimated usage/); sk = (L ~ /^### Skills/) }
    if (L ~ /^\*\*Tokens/ || (cat && L ~ /^\| [A-Z]/ && L !~ /^\| Category/)) print L
    if (sk && L ~ /^\| / && L !~ /^\| Skill \|/) { s++; if (L ~ /< 20/) o++ } }
  print "SKILLS listed=" s + 0 " name_only=" o + 0 }' ".claude/cleanroom/$f.jsonl"; done
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then git check-ignore -q .claude/settings.local.json && echo "settings.local.json: git-ignored" || echo "settings.local.json: NOT git-ignored"; else echo "settings.local.json: not a git repo"; fi
```

- Apply the Step 1 rules for `GUARD` and `PENDING` to each run. If `before` and an `after` run differ in which servers are pending (other than planned ones), run Step 5 again with `sleep 45`.
- Compute from the `**Tokens:**` lines (k = 1000):
  - `measured` = before - after-all.
  - `names` = sum of `Names in context` of every planned MCP server and of the MCP servers of every planned plugin. `/context` does not count these names.
  - `saved` = measured + names. `pct` = saved / (before + sum of `Names in context` of all servers), whole percent.
  - From plugins and MCP servers: (before - after-nonskill) + names. From skills: after-nonskill - after-all, floored at 0.
  - Per 50-request session: saved x 50.
- Category table: before and after-all for each category that changed. Merge `Skills` and `System tools` into one row, `Skills + System tools (skill listing)`, because the skill listing moves between them. Leave out `Free space`, `Autocompact buffer` and `Messages`. Label `MCP tools (deferred)` as `MCP tool schemas, loaded on demand`.

## Step 6: Apply

Skip this step on `--dry-run`.

- Make every settings and undo-log change with the Write or Edit tool, so the user sees the diff in the permission prompt. Never write these files through Bash, PowerShell or a script. Files under `.claude/` always ask for permission; if the user declines, stop and say nothing was changed.
- Read `.claude/settings.local.json`; if it does not exist, start from `{}`.
- For each planned item not already off: plugin → `"enabledPlugins": {"<key>": false}`; skill → `"skillOverrides": {"<key>": "off"}`; MCP server → append `{"serverName": "<key>"}` to `deniedMcpServers`.
- Keep every other key and value exactly as it was. Write valid JSON with 2-space indentation.
- Then write `.claude/cleanroom/undo.json`: a JSON array of batches. Read the existing file first and append. Batch: `{"at": "<ISO time>", "file": ".claude/settings.local.json", "changes": [{"kind": "plugin|skill|mcp", "key": "<key>", "before": <previous value or null>}]}`. Log only items you changed.
- `settings.local.json: NOT git-ignored` in Step 5: tell the user to add `.claude/settings.local.json` to `.gitignore` before committing.

## Step 7: Summary

Present in this order:
1. Headline: `~X fewer always-on tokens per request (Y%)`, then the split (from plugins/MCP servers, from skills), then the per-session figure.
2. If skills were switched off while the listing was FULL: one sentence saying they saved no tokens but restored descriptions, with name-only counts before and after.
3. Table of switched-off items: ref, kind, name, est. tokens, `auto` or `you chose`. Skills while the listing is FULL: `0 (frees listing room)`.
4. Kept after asking: names only, one line.
5. Kept as relevant: names with the signal, one line each, at most 10 (then `+N more`).
6. Category before/after table from Step 5.
7. Not switchable per project (built-in skills, agents, memory files, inline plugins) with their token counts, as one short list. If a memory file is over 5k tokens, say it is the next biggest lever.
8. Load errors: one line per `E` ref with the message (shortened), the owner, and the fix or commands to run. Otherwise `No load errors.`
9. Next steps: restart Claude Code in this project to apply; `/cleanroom:audit restore` to undo; any `.gitignore` note.

Quote measured numbers from Step 5; never invent or round them further. Mark per-item numbers as estimates.

## Step 8: Switch these off everywhere (only when triggered)

Trigger if any of these hold:
- 10 or more items in the plan.
- Step 1 shows 10 or more items switched off in this repo.
- Any candidate key appears in Step 1's sibling-repo list with a count of 2 or more.

When triggered, add a `Switch these off everywhere` section to the summary:
- List items that look irrelevant across the whole account: items off in 2+ sibling repos, plus items tied to one client, product or domain that most repos would not use. Leave out items that fit some of the user's repos (judge from the CLAUDE.md and memory files). One line each: name, kind, why.
- Give the method for each kind present, exactly as below:
  - Plugin: `"enabledPlugins": { "<name>@<marketplace>": false }` in `~/.claude/settings.json`. A repo that needs it sets `true` in its own `.claude/settings.local.json`; the narrower scope wins.
  - Skill (user or claude.ai synced): `"skillOverrides": { "<name>": "off" }` in `~/.claude/settings.json`. A repo that needs it sets `"<name>": "on"` in its own `.claude/settings.local.json`. For synced skills there is also `"syncClaudeAiSkills": false` in `~/.claude/settings.json`, which stops syncing all claude.ai skills into Claude Code.
  - User-scope MCP server: run `claude mcp get <name>` and save its config first, then `claude mcp remove <name> --scope user`, then `claude mcp add ... --scope local` (or `--scope project`) in each repo that uses it. Do not suggest a user-level `deniedMcpServers` entry for it: deny lists merge across scopes, so no repo could turn it back on.
  - claude.ai connector: keep switching it off per project. If the user never uses it in Claude Code, a user-level `"deniedMcpServers": [{ "serverName": "claude.ai <Name>" }]` blocks it everywhere with no per-repo exception; `"disableClaudeAiConnectors": true` blocks every connector. Disconnecting it on claude.ai also changes claude.ai itself.
- Unless `--dry-run`, ask one AskUserQuestion: `Switch the listed plugins and skills off for every project now? (MCP servers and connectors stay manual.)` Options: `Yes, user scope` (description: `Edits ~/.claude/settings.json; /cleanroom:audit restore can undo it`) and `No, I'll do it myself` (description: `Nothing changes; the steps above stay in the summary`). Mark neither as recommended.
- On yes: edit `~/.claude/settings.json` exactly as Step 6 does (plugins and skills only; skip ask-only items), and append a batch to `~/.claude/cleanroom/user-undo.json` with `"file": "~/.claude/settings.json"`. Remind the user how a repo turns an item back on.

## Restore

- Edit files only with the Write or Edit tool, as in Step 6.
- Read `.claude/cleanroom/undo.json`. Take batches without a `restored` field, newest first.
- For each change, look at the current value in the batch's file:
  - Still what cleanroom set (`false`, `"off"`, or the `deniedMcpServers` entry present): set it back to `before`. `null` means delete the key or remove the entry. Drop a section that becomes empty.
  - Anything else: leave it and report it as changed by hand.
- Write the settings file, then add `"restored": "<ISO time>"` to each processed batch in `undo.json`.
- If `~/.claude/cleanroom/user-undo.json` has unrestored batches, ask whether to undo the user-scope changes too, and restore them the same way on yes.
- Report what was restored and that it takes effect in the next session.
