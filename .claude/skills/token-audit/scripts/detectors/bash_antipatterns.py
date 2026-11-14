#!/usr/bin/env python3
"""
Detector: Bash anti-patterns.

Shelling out via Bash to run `cat`, `head`, `tail`, `find`, `grep` dumps
full output into context, whereas the native Read/Glob/Grep tools stream
ranged/truncated output. Samarth's audit: 662 such calls in one codebase.

We identified each Bash tool_use and check its `command_head` (first token)
against a denylist.
"""

from __future__ import annotations

from cost_model import estimate_context_cost, format_dollars, format_tokens
from detectors import Leak


ANTIPATTERN_COMMANDS = {
    "cat": "Read",
    "head": "Read",
    "tail": "Read",
    "less": "Read",
    "more": "Read",
    "find": "Glob",
    "grep": "Grep",
    "rg": "Grep",
    "fgrep": "Grep",
    "egrep": "Grep",
    "awk": "Read/Grep",
    "sed": "Edit",
}

MIN_COUNT_TO_FLAG = 10


def detect(sessions, config) -> list[Leak]:
    offense_counts: dict[str, int] = {}
    session_touches: set[str] = set()
    total_antipattern_turns = 0

    # We approximate the wasted context as avg-result-size × offending calls.
    # Without result sizes per call, use a heuristic 2k tokens per offense.
    HEURISTIC_TOKENS_PER_CALL = 2_000

    for s in sessions:
        hit_this_session = False
        for turn in s.turns:
            for call in turn.tool_calls:
                if call.name != "Bash":
                    continue
                head = call.input_summary.get("command_head", "")
                if head in ANTIPATTERN_COMMANDS:
                    offense_counts[head] = offense_counts.get(head, 0) + 1
                    total_antipattern_turns += 1
                    hit_this_session = True
        if hit_this_session:
            session_touches.add(s.session_id)

    if total_antipattern_turns < MIN_COUNT_TO_FLAG:
        return []

    weekly_tokens = total_antipattern_turns * HEURISTIC_TOKENS_PER_CALL
    model_counts: dict[str, int] = {}
    for s in sessions:
        for m, c in s.models_used.items():
            model_counts[m] = model_counts.get(m, 0) + c
    model = max(model_counts.items(), key=lambda kv: kv[1])[0] if model_counts else None

    weekly_cost = estimate_context_cost(weekly_tokens, model, cache_hit_ratio=0.7)
    savings = round(weekly_cost * 0.6, 2)
    severity = "warning" if savings >= 1 else "suggestion"

    top = sorted(offense_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    evidence = [
        f"{total_antipattern_turns:,} Bash calls using commands that have native Claude Code equivalents",
        f"Across {len(session_touches)} sessions",
        "Breakdown:",
        *[f"  `{cmd}` → use `{ANTIPATTERN_COMMANDS[cmd]}` instead ({count:,}×)" for cmd, count in top],
        f"Estimated weekly waste: ~{format_tokens(weekly_tokens)} tok → {format_dollars(weekly_cost)}",
    ]

    fix_action = (
        "Add a rule to `~/.claude/CLAUDE.md` under 'Tool preferences': "
        "\"Prefer Read over `cat`/`head`/`tail`. Prefer Glob over `find`. "
        "Prefer Grep over `grep`/`rg`. Native tools stream ranged output; Bash pipes dump everything.\""
    )

    return [Leak(
        id="bash:antipatterns",
        title=f"{total_antipattern_turns:,} Bash calls that should use native tools",
        severity=severity,
        category="tools",
        evidence=evidence,
        est_weekly_tokens=weekly_tokens,
        est_weekly_cost_usd=weekly_cost,
        est_weekly_savings_usd=savings,
        fix_action=fix_action,
        fix_applicable=False,
        fix_spec={"type": "claude_md_rule", "content": "prefer_native_tools"},
    )]
