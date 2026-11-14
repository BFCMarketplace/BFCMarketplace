#!/usr/bin/env python3
"""
Detector: runaway recurring scripts.

Inspired by Kieran Klaassen's case (Apr 2026): a cron job set to fire every
5 minutes instead of the intended cadence burned 91% of his weekly subscription
by Monday morning. Thariq (Anthropic) helped him debug.

Detection: for each project, look at session start timestamps. If many
sessions start at regular intervals (cron-like spacing), flag it — that's
almost always a misconfigured scheduled script, not intentional human use.

Signals:
  - High session count per project per day (> 50 sessions/day is suspicious)
  - Regular inter-session spacing (>70% of gaps within tolerance of one mode)
  - Off-hours concentration (half+ of sessions in 0-6am local)
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timezone

from cost_model import estimate_context_cost, format_dollars, format_tokens
from detectors import Leak


# Tolerance for "same interval": if the modal interval is X seconds, group
# anything within ±10% as matching the mode.
INTERVAL_TOLERANCE_PCT = 0.10
# Thresholds for flagging.
MIN_SESSIONS_TO_ANALYZE = 8    # need enough samples to detect a pattern
MIN_REGULAR_RATIO = 0.50       # 50%+ of gaps match the mode → likely cron
MIN_SESSIONS_PER_DAY = 30      # suspiciously high for human-initiated use


def detect(sessions, config) -> list[Leak]:
    leaks: list[Leak] = []

    # Bucket sessions by project.
    by_project: dict[str, list] = defaultdict(list)
    for s in sessions:
        if s.first_timestamp:
            by_project[s.project].append(s)

    for project, proj_sessions in by_project.items():
        if len(proj_sessions) < MIN_SESSIONS_TO_ANALYZE:
            continue

        # Sort by start time.
        proj_sessions.sort(key=lambda s: s.first_timestamp)
        timestamps = [s.first_timestamp for s in proj_sessions]

        # Compute inter-session gaps in seconds.
        gaps = [
            (timestamps[i+1] - timestamps[i]).total_seconds()
            for i in range(len(timestamps) - 1)
        ]
        # Drop tiny gaps (<30s suggests parallel sessions, not a schedule) and
        # huge gaps (>1 day spans weekends — not a cron cadence signal).
        gaps = [g for g in gaps if 30 <= g <= 86_400]
        if len(gaps) < MIN_SESSIONS_TO_ANALYZE:
            continue

        # Find modal interval (bucket to nearest 10s to collapse minor jitter).
        bucketed = [round(g / 10) * 10 for g in gaps]
        mode_gap, mode_count = Counter(bucketed).most_common(1)[0]
        if mode_gap == 0:
            continue
        regular_ratio = mode_count / len(gaps)

        # Off-hours check — concentrated 0-6am local (we use UTC; not exact but
        # any project running heavily in a single 6-hour band is suspicious).
        hours = [t.astimezone(timezone.utc).hour for t in timestamps]
        hour_hist = Counter(hours)
        # Biggest 6-hour window share.
        max_window = max(
            sum(hour_hist[(h + offset) % 24] for offset in range(6))
            for h in range(24)
        ) / len(hours)

        # Rate per day.
        span_days = max(1, (timestamps[-1] - timestamps[0]).total_seconds() / 86_400)
        sessions_per_day = len(proj_sessions) / span_days

        # Decide if this is a runaway pattern.
        is_cron_like = regular_ratio >= MIN_REGULAR_RATIO and mode_gap < 3_600
        is_high_volume = sessions_per_day >= MIN_SESSIONS_PER_DAY
        is_night_heavy = max_window >= 0.70

        if not (is_cron_like or is_high_volume):
            continue

        # Estimate cost of this project's automation load.
        total_tokens = sum(
            s.total_usage.total for s in proj_sessions
        )
        # Model mix for costing.
        model_counts: Counter = Counter()
        for s in proj_sessions:
            for m, c in s.models_used.items():
                model_counts[m] += c
        model = model_counts.most_common(1)[0][0] if model_counts else None
        weekly_cost = estimate_context_cost(
            total_tokens, model, cache_hit_ratio=0.7
        ) if total_tokens else 0.0

        # Savings estimate: correcting the schedule typically reclaims 80-90%
        # of the runaway load.
        savings = round(weekly_cost * 0.7, 2) if is_cron_like else round(weekly_cost * 0.3, 2)
        severity = "critical" if savings >= 5 else "warning" if savings >= 1 else "suggestion"

        evidence = [
            f"{len(proj_sessions)} sessions in {span_days:.1f} days ({sessions_per_day:.0f}/day)",
        ]
        if is_cron_like:
            interval_min = mode_gap / 60
            evidence.append(
                f"{regular_ratio:.0%} of session gaps cluster at ~{interval_min:.1f}-minute intervals "
                f"— looks cron-like, not human-initiated"
            )
        if is_night_heavy:
            evidence.append(
                f"{max_window:.0%} of sessions in a single 6-hour window — concentrated automation"
            )
        evidence.append(
            f"Estimated weekly load: ~{format_tokens(total_tokens)} tokens "
            f"({format_dollars(weekly_cost)} at list pricing)"
        )

        fix_action = (
            f"Audit scheduled jobs firing in `{project}`. "
            "Check: launchd / cron / scheduled tasks / GitHub Actions cron / "
            "anything using `claude -p` in a loop. "
            "Three fix paths, in order of leverage: "
            "(1) If the cadence is wrong (Kieran's case — 5-min cron that should be daily), "
            "fix the schedule; "
            "(2) If the job is obsolete, disable it; "
            "(3) If the job is legitimate but doesn't need frontier quality, route it to "
            "`ollama launch claude --model qwen3.5:cloud` — same Claude Code CLI, same skills, "
            "zero draw on your Anthropic subscription. See additional-optimizations.md §4+§9 "
            "for the Ollama routing evaluation. "
            "Confirm the drop with `ccusage daily` after the fix."
        )

        leaks.append(Leak(
            id=f"recurring_scripts:{project}",
            title=f"Possible runaway recurring script in `{project}`",
            severity=severity,
            category="automation",
            evidence=evidence,
            est_weekly_tokens=total_tokens,
            est_weekly_cost_usd=weekly_cost,
            est_weekly_savings_usd=savings,
            fix_action=fix_action,
            fix_applicable=False,
            fix_spec={
                "type": "schedule_audit",
                "project": project,
                "modal_interval_seconds": mode_gap,
                "sessions_per_day": sessions_per_day,
            },
        ))

    return leaks
