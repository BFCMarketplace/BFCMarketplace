#!/usr/bin/env python3
"""
Detector: redundant file reads.

Same file Read 3+ times in one session is almost always waste — Claude Code
already caches file contents in context. Usually caused by: failed attempts
that caused re-reads, or asking for a file Claude already saw.
"""

from __future__ import annotations

from cost_model import estimate_context_cost, format_dollars, format_tokens
from detectors import Leak


READS_THRESHOLD = 3
BYTES_PER_TOKEN = 4
AVG_FILE_SIZE_BYTES = 4000   # conservative default when we can't measure


def detect(sessions, config) -> list[Leak]:
    redundant_events = []  # (session, path, count)
    total_wasted_tokens = 0
    models: dict[str, int] = {}

    for s in sessions:
        for path, count in s.file_reads.items():
            if count < READS_THRESHOLD:
                continue
            excess_reads = count - 1   # only need the file loaded once
            # Estimate bytes per read by looking at tool_result sizes for Read calls on this path.
            sizes = _estimate_read_size(s, path)
            avg_bytes = sizes or AVG_FILE_SIZE_BYTES
            wasted = (excess_reads * avg_bytes) // BYTES_PER_TOKEN
            total_wasted_tokens += wasted
            redundant_events.append((s, path, count, wasted))
            for m in s.models_used:
                models[m] = models.get(m, 0) + 1

    if not redundant_events:
        return []

    redundant_events.sort(key=lambda x: x[3], reverse=True)
    model = max(models.items(), key=lambda kv: kv[1])[0] if models else None
    weekly_cost = estimate_context_cost(total_wasted_tokens, model, cache_hit_ratio=0.8)
    savings = round(weekly_cost * 0.7, 2)
    severity = "warning" if savings >= 1 else "suggestion"

    top = redundant_events[:5]
    fix_action = (
        f"{len(redundant_events)} file paths were Read 3+ times in one session. "
        "Thariq (Anthropic): `/rewind` (double-Esc) after a failed attempt keeps the useful reads "
        "and drops the failed steps, instead of re-reading. For known-sticky refs, put a pointer "
        "in CLAUDE.md so Claude doesn't have to rediscover them."
    )

    return [Leak(
        id="file_reads:redundant",
        title=f"Redundant Read on {len(redundant_events)} file paths",
        severity=severity,
        category="tools",
        evidence=[
            f"{len(redundant_events)} paths Read 3+ times in a single session",
            *[f"  {_shorten(path)}: {count}× in {s.project}" for s, path, count, _ in top],
            f"Estimated wasted context: ~{format_tokens(total_wasted_tokens)} tok/week",
            f"Weekly cost: {format_dollars(weekly_cost)}",
        ],
        est_weekly_tokens=total_wasted_tokens,
        est_weekly_cost_usd=weekly_cost,
        est_weekly_savings_usd=savings,
        fix_action=fix_action,
        fix_applicable=False,
        fix_spec={"type": "behavioral", "guidance": "rewind_over_reread"},
        thariq_quote="Rewind is often the better approach to correction.",
    )]


def _estimate_read_size(session, path: str) -> int:
    """Look at tool_results tied to Read calls for this path and pick a median size."""
    sizes: list[int] = []
    # Index tool_use_id → path
    read_tool_ids: dict[str, str] = {}
    for turn in session.turns:
        for call in turn.tool_calls:
            if call.name == "Read" and call.input_summary.get("file_path") == path:
                read_tool_ids[call.tool_use_id] = path
    # Collect matching results.
    for turn in session.turns:
        for result in turn.tool_results:
            if result.tool_use_id in read_tool_ids:
                sizes.append(result.content_size)
    if not sizes:
        return 0
    sizes.sort()
    return sizes[len(sizes) // 2]


def _shorten(path: str) -> str:
    if len(path) <= 70:
        return path
    return "…" + path[-67:]
