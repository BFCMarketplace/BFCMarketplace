"""Leak detectors. Each module exports a `detect(sessions, config) -> list[Leak]`."""

from __future__ import annotations

from dataclasses import dataclass, field


# Severity is one of: "critical" | "warning" | "suggestion".
# Using plain str for dataclass ergonomics; validated at construction.
Severity = str
VALID_SEVERITIES = {"critical", "warning", "suggestion"}


@dataclass
class Leak:
    """A detected inefficiency, with evidence and a ballpark saving estimate."""

    id: str                                          # stable machine key, e.g. "hook_bloat_session_start"
    title: str                                       # short human label
    severity: str                                    # 'critical' | 'warning' | 'suggestion'
    category: str                                    # "hooks", "model", "context", "cache", "skills", ...
    evidence: list[str] = field(default_factory=list)  # short bullet strings
    est_weekly_tokens: int = 0                       # ballpark tokens wasted per week
    est_weekly_cost_usd: float = 0.0                 # ballpark $ wasted per week
    est_weekly_savings_usd: float = 0.0              # ballpark $ recoverable if fix applied
    fix_action: str = ""                             # one-liner recommendation
    fix_applicable: bool = False                     # can apply_fix.py touch this?
    fix_spec: dict = field(default_factory=dict)     # machine-readable fix hint
    thariq_quote: str = ""                           # Anthropic citation where relevant

    def __lt__(self, other: "Leak") -> bool:
        # Enables sorted(leaks) — highest savings first.
        return self.est_weekly_savings_usd > other.est_weekly_savings_usd
