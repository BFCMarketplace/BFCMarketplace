#!/usr/bin/env python3
"""
Detector: cache miss storms.

Sessions with a low cache-hit ratio pay cache-write pricing on most context.
Usually caused by: CLAUDE.md edits mid-session, project-switching in one
session, or system-prompt churn (plugins loaded/unloaded).
"""

from __future__ import annotations

from cost_model import PRICING, format_dollars
from detectors import Leak


LOW_CACHE_HIT_THRESHOLD = 0.5
MIN_INPUT_TOKENS_TO_FLAG = 500_000   # don't flag tiny sessions


def detect(sessions, config) -> list[Leak]:
    offenders = []
    total_extra_cost = 0.0

    for s in sessions:
        total_in = (
            s.total_usage.input_tokens
            + s.total_usage.cache_read_input_tokens
        )
        if total_in < MIN_INPUT_TOKENS_TO_FLAG:
            continue
        hit_ratio = s.total_usage.cache_read_input_tokens / total_in if total_in else 0
        if hit_ratio >= LOW_CACHE_HIT_THRESHOLD:
            continue

        # Extra cost: the non-cache-read portion paid cache-write rates when it could have
        # been cache-read. Approximate delta: cache_creation at write-rate minus what it
        # would have cost at read-rate.
        model = _pick_model(s.models_used)
        pricing = _resolve_pricing(model)
        extra = (
            s.total_usage.cache_creation_input_tokens
            * (pricing["cache_write"] - pricing["cache_read"])
            / 1_000_000
        )
        total_extra_cost += extra
        offenders.append((s, hit_ratio, extra))

    if not offenders:
        return []

    # Only flag once, summarizing top 3 sessions.
    offenders.sort(key=lambda x: x[2], reverse=True)
    top = offenders[:3]
    savings = round(total_extra_cost * 0.6, 2)  # well-cached sessions recover most of the delta
    severity = "critical" if savings >= 5 else "warning" if savings >= 1 else "suggestion"

    fix_action = (
        f"{len(offenders)} sessions ran with <{int(LOW_CACHE_HIT_THRESHOLD*100)}% cache-hit ratio. "
        "Common causes: (a) CLAUDE.md edited mid-session, (b) project switched in same session, "
        "(c) many plugins/skills installed and the system prompt still stabilizing. "
        "Fix: start a new session after big CLAUDE.md changes; don't switch projects mid-session."
    )

    return [Leak(
        id="cache:miss_storms",
        title=f"Cache miss storms in {len(offenders)} sessions",
        severity=severity,
        category="cache",
        evidence=[
            f"{len(offenders)} sessions below {int(LOW_CACHE_HIT_THRESHOLD*100)}% cache-hit ratio",
            *[f"  {s.project} ({s.session_id[:8]}…): hit={ratio:.0%}, extra≈{format_dollars(extra)}"
              for s, ratio, extra in top],
            f"Total extra cache-write cost: {format_dollars(total_extra_cost)}/week",
        ],
        est_weekly_tokens=sum(s.total_usage.cache_creation_input_tokens for s, _, _ in offenders),
        est_weekly_cost_usd=round(total_extra_cost, 2),
        est_weekly_savings_usd=savings,
        fix_action=fix_action,
        fix_applicable=False,
        fix_spec={"type": "behavioral", "guidance": "avoid_mid_session_churn"},
    )]


def _pick_model(models: dict) -> str | None:
    if not models:
        return None
    # Most frequent wins.
    return max(models.items(), key=lambda kv: kv[1])[0]


def _resolve_pricing(model: str | None) -> dict:
    if not model:
        return PRICING["claude-opus-4"]
    m = model.lower()
    for key, prices in PRICING.items():
        if m.startswith(key):
            return prices
    return PRICING["claude-opus-4"]
