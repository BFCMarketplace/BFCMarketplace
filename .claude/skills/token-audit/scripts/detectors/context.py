#!/usr/bin/env python3
"""
Detector: late compact / context rot (cites Thariq Shihipar).

Sessions that spend many turns above ~400k tokens of context waste money
(cache writes) AND quality (attention degrades — "context rot"). Anthropic's
Claude Code team recommends proactive /compact with an intent hint instead
of reactive auto-compact.
"""

from __future__ import annotations

from cost_model import estimate_context_cost, format_dollars, format_tokens
from detectors import Leak


CONTEXT_ROT_THRESHOLD = 400_000   # Thariq: middle-loss degradation kicks in here
MIN_BAD_TURNS_TO_FLAG = 10
THARIQ_QUOTE = "Due to context rot, the model is at its least intelligent point when compacting."


def detect(sessions, config) -> list[Leak]:
    bad_turns = []
    bad_sessions: dict[str, int] = {}  # session_id → turns above threshold
    total_wasted_context_tokens = 0
    dominant_models: dict[str, int] = {}

    for s in sessions:
        turns_above = 0
        for turn in s.turns:
            if not turn.usage:
                continue
            if turn.usage.context_size > CONTEXT_ROT_THRESHOLD:
                turns_above += 1
                bad_turns.append(turn)
                # Excess over threshold is the "wasted" portion (not strictly wasted, but
                # the zone where attention degrades — compacting sooner avoids re-feeding it).
                total_wasted_context_tokens += (turn.usage.context_size - CONTEXT_ROT_THRESHOLD)
                if turn.model:
                    dominant_models[turn.model] = dominant_models.get(turn.model, 0) + 1
        if turns_above > 0:
            bad_sessions[s.session_id] = turns_above

    if len(bad_turns) < MIN_BAD_TURNS_TO_FLAG:
        return []

    model = max(dominant_models.items(), key=lambda kv: kv[1])[0] if dominant_models else None
    weekly_cost = estimate_context_cost(total_wasted_context_tokens, model, cache_hit_ratio=0.7)
    # Compacting proactively typically reclaims 40-60% of the excess context cost.
    savings = round(weekly_cost * 0.5, 2)
    severity = "critical" if savings >= 5 else "warning" if savings >= 1 else "suggestion"

    # Worst offender session.
    worst_session_id = max(bad_sessions.items(), key=lambda kv: kv[1])[0]
    worst_count = bad_sessions[worst_session_id]

    fix_action = (
        f"{len(bad_turns):,} turns ran with >{CONTEXT_ROT_THRESHOLD//1000}k context "
        f"across {len(bad_sessions)} sessions. Thariq (Anthropic): compact PROACTIVELY with a hint "
        "(e.g., `/compact focus on auth refactor, drop debugging`). "
        "For a fresh task, `/clear` or start a new session instead of continuing."
    )

    return [Leak(
        id="context:late_compact",
        title=f"{len(bad_turns):,} turns ran past the context-rot threshold",
        severity=severity,
        category="context",
        evidence=[
            f"{len(bad_turns):,} turns with context >{CONTEXT_ROT_THRESHOLD//1000}k tokens "
            f"across {len(bad_sessions)} sessions",
            f"Worst session: {worst_session_id[:8]}… with {worst_count} over-threshold turns",
            f"Excess context fed into model: ~{format_tokens(total_wasted_context_tokens)} tokens/week",
            f"Estimated weekly waste: {format_dollars(weekly_cost)}",
        ],
        est_weekly_tokens=total_wasted_context_tokens,
        est_weekly_cost_usd=weekly_cost,
        est_weekly_savings_usd=savings,
        fix_action=fix_action,
        fix_applicable=False,  # behavior change
        fix_spec={"type": "behavioral", "guidance": "proactive_compact"},
        thariq_quote=THARIQ_QUOTE,
    )]
