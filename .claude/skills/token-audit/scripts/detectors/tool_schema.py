#!/usr/bin/env python3
"""
Detector: tool-schema bloat when tool search is off.

If ENABLE_TOOL_SEARCH is disabled, full JSON schemas for every registered
tool (Claude Code built-ins + plugins + MCP servers) get dumped into the
system prompt on every turn. Samarth Gupta measured ~20k tokens → ~6k when
flipping tool search on (Apr 2026).

When tool search IS on (user's ENABLE_TOOL_SEARCH=auto:N), this detector
reports a non-action informational note instead of a leak.
"""

from __future__ import annotations

from cost_model import estimate_context_cost, format_dollars, format_tokens
from detectors import Leak


# Conservative estimate: tool schemas add ~500 tokens per MCP server plus
# ~2k tokens for Claude Code built-ins. Numbers from Samarth's /context audit.
SCHEMA_TOKENS_PER_MCP_SERVER = 500
BUILTIN_TOOL_SCHEMA_TOKENS = 2_000
# Per-turn cost of schema injection (cache-write first turn, cache-read after).
CACHE_HIT_ASSUMPTION = 0.85


def detect(sessions, config) -> list[Leak]:
    # If tool search is on, no leak — but we surface the fact for transparency.
    if config.tool_search_enabled:
        return []

    # Tool search is OFF. Estimate the schema load.
    n_mcps = len(config.mcp_servers_configured)
    schema_tokens_per_turn = BUILTIN_TOOL_SCHEMA_TOKENS + n_mcps * SCHEMA_TOKENS_PER_MCP_SERVER

    # Total turns in audit window
    total_turns = sum(s.turn_count for s in sessions)
    if total_turns < 50:
        return []   # not enough signal

    weekly_schema_tokens = schema_tokens_per_turn * total_turns

    # Pick dominant model for costing.
    model_counts: dict[str, int] = {}
    for s in sessions:
        for m, c in s.models_used.items():
            model_counts[m] = model_counts.get(m, 0) + c
    model = max(model_counts.items(), key=lambda kv: kv[1])[0] if model_counts else None

    weekly_cost = estimate_context_cost(weekly_schema_tokens, model, cache_hit_ratio=CACHE_HIT_ASSUMPTION)
    # Flipping tool search on reduces schema to ~6k flat → ~70% recovery.
    savings = round(weekly_cost * 0.7, 2)
    severity = "critical" if savings >= 5 else "warning" if savings >= 1 else "suggestion"

    fix_action = (
        f"Set `ENABLE_TOOL_SEARCH=auto:5` in `~/.claude/settings.json` → `env`. "
        "Tool schemas then load on-demand (3-5 relevant tools per search) instead of "
        f"dumping all {n_mcps} MCP servers + built-ins into every turn. "
        "Source: Samarth Gupta measured 20k → 6k tokens on his setup."
    )

    return [Leak(
        id="tool_schema:bloat",
        title=f"Tool search is OFF — ~{format_tokens(schema_tokens_per_turn)} tok/turn schema load",
        severity=severity,
        category="context",
        evidence=[
            f"`ENABLE_TOOL_SEARCH` not set to `auto:*` or `true` (current: `{config.tool_search_mode}`)",
            f"{n_mcps} MCP servers configured → ~{schema_tokens_per_turn:,} tok of schemas per turn",
            f"{total_turns:,} turns in audit window → ~{format_tokens(weekly_schema_tokens)} weekly schema tax",
            f"Estimated weekly cost: {format_dollars(weekly_cost)}",
        ],
        est_weekly_tokens=weekly_schema_tokens,
        est_weekly_cost_usd=weekly_cost,
        est_weekly_savings_usd=savings,
        fix_action=fix_action,
        fix_applicable=True,
        fix_spec={
            "type": "settings_env",
            "path": "~/.claude/settings.json",
            "key": "env.ENABLE_TOOL_SEARCH",
            "value": "auto:5",
        },
    )]
