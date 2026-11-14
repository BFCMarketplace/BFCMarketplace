#!/usr/bin/env python3
"""
Detector: CLAUDE.md bloat.

Anthropic's cost doc recommends CLAUDE.md under 200 lines. Every turn pays
the token cost of every CLAUDE.md in the memory tree. Flags files > 2k
tokens (warning) and > 5k tokens (critical).
"""

from __future__ import annotations

from pathlib import Path

from cost_model import estimate_context_cost, format_dollars, format_tokens
from detectors import Leak


WARNING_TOKEN_THRESHOLD = 2_000
CRITICAL_TOKEN_THRESHOLD = 5_000
BYTES_PER_TOKEN = 4


def detect(sessions, config) -> list[Leak]:
    # CLAUDE.md locations we check:
    #   ~/.claude/CLAUDE.md               (global)
    #   Each project cwd seen in sessions: <cwd>/CLAUDE.md
    #   Workspace roots above cwd (up to 3 levels) for inherited CLAUDE.md
    candidates: set[Path] = set()

    global_cm = Path.home() / ".claude" / "CLAUDE.md"
    if global_cm.exists():
        candidates.add(global_cm)

    cwd_list: set[Path] = set()
    for s in sessions:
        if s.cwd:
            p = Path(s.cwd)
            cwd_list.add(p)
            # walk up 2 parents for inherited memory files
            for up in (p.parent, p.parent.parent):
                cwd_list.add(up)

    for cwd in cwd_list:
        cm = cwd / "CLAUDE.md"
        if cm.exists():
            candidates.add(cm)

    # Evaluate size.
    bloated = []  # (path, token_estimate, bytes)
    for path in sorted(candidates):
        try:
            size_bytes = path.stat().st_size
        except OSError:
            continue
        tokens = size_bytes // BYTES_PER_TOKEN
        if tokens < WARNING_TOKEN_THRESHOLD:
            continue
        bloated.append((path, tokens, size_bytes))

    if not bloated:
        return []

    # Compute per-turn tax: sum of bloat × turns in audit.
    total_turns = sum(s.turn_count for s in sessions)
    if total_turns < 20:
        return []

    # Each turn loads ALL applicable CLAUDE.md files (global + project). For a
    # conservative single-figure estimate, use the largest file × turn count.
    worst_tokens = max(t for _, t, _ in bloated)
    weekly_cost_tokens = worst_tokens * total_turns

    # Cost model: CLAUDE.md content is highly cacheable (rarely changes mid-day),
    # so assume 85% cache-read.
    # Model selection: pick dominant across sessions.
    model_counts: dict[str, int] = {}
    for s in sessions:
        for m, c in s.models_used.items():
            model_counts[m] = model_counts.get(m, 0) + c
    model = max(model_counts.items(), key=lambda kv: kv[1])[0] if model_counts else None

    weekly_cost = estimate_context_cost(weekly_cost_tokens, model, cache_hit_ratio=0.85)
    # Trimming CLAUDE.md to the 200-line target usually halves size → ~40% cost recovery.
    savings = round(weekly_cost * 0.4, 2)

    worst_path, worst_tok, worst_bytes = max(bloated, key=lambda x: x[1])
    severity = (
        "critical" if worst_tok >= CRITICAL_TOKEN_THRESHOLD
        else "warning" if worst_tok >= WARNING_TOKEN_THRESHOLD
        else "suggestion"
    )

    evidence = [f"{len(bloated)} CLAUDE.md file(s) over {WARNING_TOKEN_THRESHOLD:,}-token recommendation"]
    for path, tokens, bytes_ in bloated[:5]:
        evidence.append(f"  {_shorten(path)}: ~{format_tokens(tokens)} tok ({bytes_:,} bytes)")
    evidence.append(f"Worst file × {total_turns:,} turns = ~{format_tokens(weekly_cost_tokens)} weekly tax")
    evidence.append(f"Estimated weekly cost: {format_dollars(weekly_cost)}")

    fix_action = (
        f"Trim `{_shorten(worst_path)}` from ~{format_tokens(worst_tok)} toward the 200-line target. "
        "Best practice (Anthropic cost doc + community): keep CLAUDE.md scoped to stable context "
        "(who, what, hard rules). Move detailed playbooks to separate files and reference via `@filename` or "
        "skill descriptions so they load on demand only."
    )

    return [Leak(
        id="claude_md:bloat",
        title=f"CLAUDE.md bloat: {len(bloated)} oversized file(s), worst ~{format_tokens(worst_tok)} tok",
        severity=severity,
        category="context",
        evidence=evidence,
        est_weekly_tokens=weekly_cost_tokens,
        est_weekly_cost_usd=weekly_cost,
        est_weekly_savings_usd=savings,
        fix_action=fix_action,
        fix_applicable=False,  # surgical trimming is a judgment call
        fix_spec={"type": "manual_trim", "paths": [str(p) for p, _, _ in bloated]},
    )]


def _shorten(path: Path) -> str:
    s = str(path)
    home = str(Path.home())
    if s.startswith(home):
        s = "~" + s[len(home):]
    if len(s) <= 60:
        return s
    return "…" + s[-57:]
