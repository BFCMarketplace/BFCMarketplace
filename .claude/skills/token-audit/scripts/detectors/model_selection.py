#!/usr/bin/env python3
"""
Detector: Opus on simple turns.

Heuristic: a turn where the assistant only produced a short response
(<1k total output+input) and the model is Opus-class probably didn't
need Opus. Switching to Sonnet (same prompt, same tool flow) typically
costs ~5× less.
"""

from __future__ import annotations

from cost_model import estimate_cost, format_dollars, format_tokens, TokenBreakdown
from detectors import Leak


SIMPLE_OUTPUT_THRESHOLD = 1_000    # tokens output — below this, Sonnet is almost always enough
MIN_SIMPLE_TURNS_TO_FLAG = 30      # fewer than this and it's not worth surfacing


def detect(sessions, config) -> list[Leak]:
    simple_opus_turns = []  # (turn, session) for cost estimation

    for s in sessions:
        for turn in s.turns:
            if not turn.usage or not turn.model:
                continue
            if "opus" not in turn.model.lower():
                continue
            # Output-centric heuristic: short outputs are the clearest "could've been Sonnet" signal.
            if turn.usage.output_tokens < SIMPLE_OUTPUT_THRESHOLD:
                simple_opus_turns.append((turn, s))

    if len(simple_opus_turns) < MIN_SIMPLE_TURNS_TO_FLAG:
        return []

    # Compute current cost on Opus and projected cost on Sonnet.
    opus_cost = 0.0
    sonnet_cost = 0.0
    total_tokens = 0
    for turn, _ in simple_opus_turns:
        u = turn.usage
        tokens = TokenBreakdown(
            input_tokens=u.input_tokens,
            output_tokens=u.output_tokens,
            cache_write_tokens=u.cache_creation_input_tokens,
            cache_read_tokens=u.cache_read_input_tokens,
        )
        opus_cost += estimate_cost(tokens, turn.model)
        # Project onto Sonnet 4: ~5× cheaper across input/output/cache-read, ~5× cheaper on write.
        sonnet_cost += estimate_cost(tokens, "claude-sonnet-4")
        total_tokens += u.total

    savings = round(opus_cost - sonnet_cost, 2)
    severity = "critical" if savings >= 5 else "warning" if savings >= 1 else "suggestion"

    fix_action = (
        f"{len(simple_opus_turns):,} Opus turns produced <{SIMPLE_OUTPUT_THRESHOLD}-token outputs "
        f"(~{format_tokens(total_tokens)} tok total). Sonnet would have handled these. "
        "Fix: (a) set project default model to Sonnet in `.claude/settings.json`, "
        "(b) explicitly escalate to Opus only for planning / hard reasoning, "
        "(c) use a sub-agent on Sonnet for simple lookups."
    )

    return [Leak(
        id="model_selection:opus_on_simple",
        title=f"Opus used on {len(simple_opus_turns):,} simple turns",
        severity=severity,
        category="model",
        evidence=[
            f"{len(simple_opus_turns):,} Opus turns with <{SIMPLE_OUTPUT_THRESHOLD} output tokens",
            f"Current cost on Opus: {format_dollars(opus_cost)}",
            f"Projected on Sonnet: {format_dollars(sonnet_cost)}",
            f"Delta (weekly): {format_dollars(savings)}",
        ],
        est_weekly_tokens=total_tokens,
        est_weekly_cost_usd=round(opus_cost, 2),
        est_weekly_savings_usd=savings,
        fix_action=fix_action,
        fix_applicable=False,  # behavior change required
        fix_spec={"type": "model_default_change", "suggested": "claude-sonnet-4"},
    )]
