#!/usr/bin/env python3
"""
Detector: skill-description overhead.

Every available skill's YAML `description` sits in context via the
<system-reminder> "available skills" list on every turn while loaded.
Overhead scales linearly with skill count. Flags total description budget
>5k tokens, individual skill descriptions >500 tokens.
"""

from __future__ import annotations

from cost_model import estimate_context_cost, format_dollars, format_tokens
from detectors import Leak


SINGLE_SKILL_WARN_TOKENS = 500
TOTAL_SKILLS_WARN_TOKENS = 5_000
BYTES_PER_TOKEN = 4


def detect(sessions, config) -> list[Leak]:
    if not config.skills:
        return []

    total_tokens = 0
    fat_skills: list[tuple[str, int, str]] = []   # (name, tokens, scope)

    for skill in config.skills:
        desc_bytes = len(skill.description)
        tokens = desc_bytes // BYTES_PER_TOKEN
        total_tokens += tokens
        if tokens >= SINGLE_SKILL_WARN_TOKENS:
            fat_skills.append((skill.name, tokens, skill.scope))

    if total_tokens < TOTAL_SKILLS_WARN_TOKENS and not fat_skills:
        return []

    total_turns = sum(s.turn_count for s in sessions)
    if total_turns < 50:
        return []

    weekly_tokens = total_tokens * total_turns
    model_counts: dict[str, int] = {}
    for s in sessions:
        for m, c in s.models_used.items():
            model_counts[m] = model_counts.get(m, 0) + c
    model = max(model_counts.items(), key=lambda kv: kv[1])[0] if model_counts else None

    weekly_cost = estimate_context_cost(weekly_tokens, model, cache_hit_ratio=0.9)
    savings = round(weekly_cost * 0.3, 2)  # pruning fat skills typically recovers 30%
    severity = "warning" if savings >= 1 else "suggestion"

    fat_skills.sort(key=lambda x: x[1], reverse=True)
    top_fat = fat_skills[:5]

    evidence = [
        f"{len(config.skills)} skills installed, total description budget ~{format_tokens(total_tokens)} tok",
        f"Per-turn tax: ~{total_tokens:,} tokens × ~{total_turns:,} turns = "
        f"~{format_tokens(weekly_tokens)} tok/week",
        f"Estimated weekly cost: {format_dollars(weekly_cost)}",
    ]
    if top_fat:
        evidence.append(f"Fattest {len(top_fat)} skills:")
        for name, toks, scope in top_fat:
            evidence.append(f"  {name} ({scope}): ~{toks:,} tok description")

    fix_action = (
        "Audit skill descriptions. Target: under 500 tokens per skill, under 5k tokens total. "
        "Tighten or disable skills you don't actually use. "
        "For skills you keep, move long setup detail into the skill body (loaded on invocation) "
        "and keep `description:` short and trigger-rich."
    )

    return [Leak(
        id="skills:description_bloat",
        title=f"Skill descriptions total ~{format_tokens(total_tokens)} tok (per-turn tax)",
        severity=severity,
        category="skills",
        evidence=evidence,
        est_weekly_tokens=weekly_tokens,
        est_weekly_cost_usd=weekly_cost,
        est_weekly_savings_usd=savings,
        fix_action=fix_action,
        fix_applicable=False,
        fix_spec={"type": "manual_trim", "targets": [n for n, _, _ in top_fat]},
    )]
