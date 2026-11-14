#!/usr/bin/env python3
"""
Detector: hook output bloat.

Hooks that emit large content (SessionStart briefings, PreCompact summaries)
get re-injected into context on every session. For users who start many
sessions per day, this compounds. Flags any hook whose average output
exceeds a threshold OR whose total weekly tokens exceed the floor.
"""

from __future__ import annotations

from cost_model import estimate_context_cost, format_dollars, format_tokens
from detectors import Leak


# Thresholds
MIN_AVG_CONTENT_BYTES = 5_000       # ~1.25k tokens avg per fire, worth flagging
MIN_WEEKLY_TOKEN_FLOOR = 20_000     # skip if under this — not worth user's attention
BYTES_PER_TOKEN = 4                 # rough heuristic; tokens are ~3-5 bytes for English/code


def detect(sessions, config) -> list[Leak]:
    leaks: list[Leak] = []

    # Aggregate across sessions: per hook name → (total_bytes, fire_count, sessions_touched).
    by_hook: dict[str, dict] = {}
    for s in sessions:
        for name, count in s.hook_fire_counts.items():
            bytes_here = s.hook_content_bytes.get(name, 0)
            entry = by_hook.setdefault(name, {"bytes": 0, "fires": 0, "sessions": 0, "models": set()})
            entry["bytes"] += bytes_here
            entry["fires"] += count
            entry["sessions"] += 1
            entry["models"].update(s.models_used.keys())

    # Normalize to weekly basis.
    # parse_all_sessions defaults to --since-days=7, so sums are already ≈1 week.
    for name, agg in by_hook.items():
        if agg["fires"] == 0:
            continue
        avg_bytes = agg["bytes"] / agg["fires"]
        if avg_bytes < MIN_AVG_CONTENT_BYTES:
            continue

        weekly_tokens = int(agg["bytes"] / BYTES_PER_TOKEN)
        if weekly_tokens < MIN_WEEKLY_TOKEN_FLOOR:
            continue

        # Cost assumes hook content is paid as cache-write on session start (worst case)
        # and cache-read on resume. Use blended estimate.
        dominant_model = _pick_dominant_model(agg["models"])
        weekly_cost = estimate_context_cost(weekly_tokens, dominant_model, cache_hit_ratio=0.5)

        # A reasonable fix (trim to essentials, cache expensive lookups, gate by matcher)
        # typically recovers 60-80% of this cost. We claim 60% to stay conservative.
        savings = round(weekly_cost * 0.6, 2)

        severity = _score_severity(weekly_cost)
        fix_applicable = False   # too risky to edit hook scripts automatically
        fix_action = (
            f"Trim `{name}` hook output — ~{format_tokens(weekly_tokens)} tok/week "
            f"({format_dollars(weekly_cost)}) gets re-injected into every session. "
            "Options: (a) move rarely-changing data to a file the agent reads on demand, "
            "(b) cache expensive lookups with a TTL, (c) restrict via matcher so it fires only when needed."
        )

        leaks.append(Leak(
            id=f"hook_bloat:{name}",
            title=f"Hook `{name}` re-injects ~{format_tokens(weekly_tokens)} tok/week",
            severity=severity,
            category="hooks",
            evidence=[
                f"Fires: {agg['fires']}× across {agg['sessions']} sessions in last ~7d",
                f"Avg output size: {int(avg_bytes):,} bytes (~{int(avg_bytes/BYTES_PER_TOKEN):,} tokens) per fire",
                f"Weekly re-injection: ~{format_tokens(weekly_tokens)} tokens",
                f"Estimated weekly cost ({dominant_model or 'default model'}): {format_dollars(weekly_cost)}",
            ],
            est_weekly_tokens=weekly_tokens,
            est_weekly_cost_usd=weekly_cost,
            est_weekly_savings_usd=savings,
            fix_action=fix_action,
            fix_applicable=fix_applicable,
            fix_spec={"type": "hook_trim_manual", "hook_name": name},
        ))

    return leaks


def _pick_dominant_model(models: set) -> str | None:
    """Return a representative model for cost estimates."""
    if not models:
        return None
    for m in models:
        if m and "opus" in m.lower():
            return m
    return next(iter(models), None)


def _score_severity(weekly_cost: float) -> str:
    if weekly_cost >= 5:
        return "critical"
    if weekly_cost >= 1:
        return "warning"
    return "suggestion"
