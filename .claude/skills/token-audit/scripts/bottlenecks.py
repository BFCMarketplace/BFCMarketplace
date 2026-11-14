#!/usr/bin/env python3
"""
Bottleneck analyzer.

Detectors return category-level leaks ("Opus on simple turns"). That's diffuse.
Users want: "WHICH session burned the most? WHICH project is bleeding? WHICH
file is expensive?" — so we can go fix THAT specific thing.

This module post-processes sessions + config to surface the top bottlenecks:
- Top sessions by combined waste
- Top projects by combined waste
- Top files by per-turn tax (CLAUDE.md, etc.)

Fix one bottleneck and the category-level numbers drop visibly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cost_model import estimate_cost, estimate_context_cost, format_dollars, format_tokens, TokenBreakdown


@dataclass
class Bottleneck:
    kind: str                    # "session" | "project" | "file"
    label: str                   # human label
    id: str                      # session_id / project / path
    est_weekly_cost_usd: float
    est_weekly_tokens: int
    share_of_total_pct: float    # this / total waste
    contributing_categories: list[str] = field(default_factory=list)  # ["context_rot", "opus_on_simple", ...]
    evidence: list[str] = field(default_factory=list)
    fix_action: str = ""


# ─────────────────────────────────────────────────────────────────
# Per-session waste score
# ─────────────────────────────────────────────────────────────────


def _session_waste(session) -> tuple[float, list[str], list[str]]:
    """Return (cost_usd_estimate, contributing_categories, evidence_bullets)."""
    cost = 0.0
    cats: list[str] = []
    evidence: list[str] = []

    model = None
    if session.models_used:
        model = max(session.models_used.items(), key=lambda kv: kv[1])[0]

    # Context rot cost: excess-over-400k × cache-write rate, for over-threshold turns.
    excess = 0
    over_count = 0
    peak = 0
    for turn in session.turns:
        if not turn.usage:
            continue
        ctx = turn.usage.context_size
        peak = max(peak, ctx)
        if ctx > 400_000:
            excess += ctx - 400_000
            over_count += 1
    if over_count > 0:
        context_rot_cost = estimate_context_cost(excess, model, cache_hit_ratio=0.7)
        cost += context_rot_cost
        cats.append("context_rot")
        evidence.append(
            f"{over_count:,} turns > 400k context (peak {peak//1000:,}k tok) → "
            f"~{format_dollars(context_rot_cost)}/wk context-rot cost at list pricing"
        )

    # Opus-on-simple cost for this session.
    simple_opus_turns = [
        t for t in session.turns
        if t.usage and t.model and "opus" in t.model.lower()
        and t.usage.output_tokens < 1_000
    ]
    if simple_opus_turns:
        opus_cost = 0.0
        sonnet_cost = 0.0
        for t in simple_opus_turns:
            tokens = TokenBreakdown(
                input_tokens=t.usage.input_tokens,
                output_tokens=t.usage.output_tokens,
                cache_write_tokens=t.usage.cache_creation_input_tokens,
                cache_read_tokens=t.usage.cache_read_input_tokens,
            )
            opus_cost += estimate_cost(tokens, t.model)
            sonnet_cost += estimate_cost(tokens, "claude-sonnet-4")
        delta = opus_cost - sonnet_cost
        if delta > 0:
            cost += delta
            cats.append("opus_on_simple")
            evidence.append(
                f"{len(simple_opus_turns):,} Opus turns with <1k output "
                f"({format_dollars(delta)}/wk overspend vs Sonnet)"
            )

    # Redundant reads cost.
    excess_reads = sum(max(0, c - 1) for c in session.file_reads.values() if c >= 3)
    if excess_reads >= 5:
        redundant_cost = estimate_context_cost(excess_reads * 1_000, model, cache_hit_ratio=0.8)
        cost += redundant_cost
        cats.append("redundant_reads")
        redundant_paths = [p for p, c in session.file_reads.items() if c >= 3]
        evidence.append(
            f"{excess_reads} excess file reads across {len(redundant_paths)} paths"
        )

    # Hook bloat attributable to this session.
    for name, bytes_ in session.hook_content_bytes.items():
        if bytes_ >= 5_000:
            hook_cost = estimate_context_cost(bytes_ // 4, model, cache_hit_ratio=0.5)
            cost += hook_cost
            if "hook_bloat" not in cats:
                cats.append("hook_bloat")
                evidence.append(
                    f"Hook `{name}` injected {bytes_:,} bytes "
                    f"({format_dollars(hook_cost)}/wk)"
                )

    return cost, cats, evidence


# ─────────────────────────────────────────────────────────────────
# Main computation
# ─────────────────────────────────────────────────────────────────


def compute_bottlenecks(sessions, config, top_n: int = 3) -> dict[str, list[Bottleneck]]:
    """Rank top bottlenecks by kind. Returns dict with 'session', 'project', 'file'."""
    # Score every session.
    per_session_scores: list[tuple[object, float, list[str], list[str]]] = []
    for s in sessions:
        cost, cats, evidence = _session_waste(s)
        if cost > 0.01:
            per_session_scores.append((s, cost, cats, evidence))

    total_cost = sum(cost for _, cost, _, _ in per_session_scores) or 1e-9

    # Session-level bottlenecks.
    per_session_scores.sort(key=lambda x: x[1], reverse=True)
    session_bns: list[Bottleneck] = []
    for s, cost, cats, evidence in per_session_scores[:top_n]:
        fix = _session_fix(s, cats)
        session_bns.append(Bottleneck(
            kind="session",
            label=f"{s.project} / {s.session_id[:8]}…",
            id=s.session_id,
            est_weekly_cost_usd=round(cost, 2),
            est_weekly_tokens=sum(t.usage.total for t in s.turns if t.usage),
            share_of_total_pct=round(cost / total_cost * 100, 1),
            contributing_categories=cats,
            evidence=evidence + [f"Total session turns: {s.turn_count:,}"],
            fix_action=fix,
        ))

    # Project-level bottlenecks (sum across sessions of same project).
    per_project: dict[str, dict] = {}
    for s, cost, cats, evidence in per_session_scores:
        proj = s.project
        entry = per_project.setdefault(proj, {
            "cost": 0.0, "cats": set(), "sessions": 0, "turns": 0, "evidence": [],
        })
        entry["cost"] += cost
        entry["cats"].update(cats)
        entry["sessions"] += 1
        entry["turns"] += s.turn_count

    project_bns: list[Bottleneck] = []
    for proj, entry in sorted(per_project.items(), key=lambda kv: kv[1]["cost"], reverse=True)[:top_n]:
        if entry["cost"] < 1:
            continue
        project_bns.append(Bottleneck(
            kind="project",
            label=proj,
            id=proj,
            est_weekly_cost_usd=round(entry["cost"], 2),
            est_weekly_tokens=0,
            share_of_total_pct=round(entry["cost"] / total_cost * 100, 1),
            contributing_categories=sorted(entry["cats"]),
            evidence=[
                f"{entry['sessions']} sessions, {entry['turns']:,} total turns",
                f"Leak categories active in this project: {', '.join(sorted(entry['cats']))}",
            ],
            fix_action=_project_fix(proj, entry["cats"]),
        ))

    # File-level bottlenecks (CLAUDE.md files + most-read files).
    file_bns: list[Bottleneck] = _file_bottlenecks(sessions, config, total_cost, top_n)

    return {
        "session": session_bns,
        "project": project_bns,
        "file": file_bns,
    }


# ─────────────────────────────────────────────────────────────────
# Fix suggestions per bottleneck
# ─────────────────────────────────────────────────────────────────


def _session_fix(session, cats: list[str]) -> str:
    """Suggest the single highest-leverage fix for this session."""
    if "context_rot" in cats:
        return (
            "Long session past the context-rot threshold. Thariq (Anthropic): "
            "compact PROACTIVELY with a scope hint before auto-compact fires, or "
            "start a new session for each fresh task. `/compact focus on X, drop Y`."
        )
    if "opus_on_simple" in cats:
        return (
            "Most turns here are short enough for Sonnet. "
            "Add to this project's `.claude/settings.json`: `\"model\": \"claude-sonnet-4\"`. "
            "Escalate to Opus only for planning/hard reasoning."
        )
    if "hook_bloat" in cats:
        return (
            "A hook re-injects a lot of content into this session. "
            "Trim the hook output — move slow-changing data to a file loaded on demand."
        )
    if "redundant_reads" in cats:
        return "Same file read many times — `/rewind` (double-Esc) after failed attempts instead of re-reading."
    return "Review this session's transcript for the dominant waste pattern."


def _project_fix(project: str, cats: set) -> str:
    parts = []
    if "opus_on_simple" in cats:
        parts.append(
            "Set `\"model\": \"claude-sonnet-4\"` in this project's `.claude/settings.json`"
        )
    if "context_rot" in cats:
        parts.append(
            "Add a project CLAUDE.md rule: 'Start a new session per task; compact proactively with a scope hint'"
        )
    if "hook_bloat" in cats:
        parts.append("Audit session-start hook output for this project")
    if not parts:
        parts.append("Review the session-level bottleneck above for this project's specific fix")
    return "; ".join(parts)


def _file_bottlenecks(sessions, config, total_cost: float, top_n: int) -> list[Bottleneck]:
    """Top files by per-turn tax (CLAUDE.md files)."""
    results: list[Bottleneck] = []
    total_turns = sum(s.turn_count for s in sessions) or 1

    claude_md_paths: set[Path] = set()
    home_cm = Path.home() / "CLAUDE.md"
    claude_cm = Path.home() / ".claude" / "CLAUDE.md"
    if home_cm.exists():
        claude_md_paths.add(home_cm)
    if claude_cm.exists():
        claude_md_paths.add(claude_cm)
    for s in sessions:
        if s.cwd:
            cm = Path(s.cwd) / "CLAUDE.md"
            if cm.exists():
                claude_md_paths.add(cm)

    # Model mix for costing.
    model_counts: dict[str, int] = {}
    for s in sessions:
        for m, c in s.models_used.items():
            model_counts[m] = model_counts.get(m, 0) + c
    model = max(model_counts.items(), key=lambda kv: kv[1])[0] if model_counts else None

    file_costs: list[tuple[Path, int, float]] = []  # (path, tokens, cost)
    for path in claude_md_paths:
        try:
            size_bytes = path.stat().st_size
        except OSError:
            continue
        tokens = size_bytes // 4
        if tokens < 1_500:
            continue
        weekly_tokens = tokens * total_turns
        weekly_cost = estimate_context_cost(weekly_tokens, model, cache_hit_ratio=0.85)
        file_costs.append((path, tokens, weekly_cost))

    file_costs.sort(key=lambda x: x[2], reverse=True)
    for path, tokens, cost in file_costs[:top_n]:
        results.append(Bottleneck(
            kind="file",
            label=_shorten(path),
            id=str(path),
            est_weekly_cost_usd=round(cost, 2),
            est_weekly_tokens=tokens * total_turns,
            share_of_total_pct=round(cost / total_cost * 100, 1) if total_cost > 0 else 0,
            contributing_categories=["claude_md_bloat"],
            evidence=[
                f"~{format_tokens(tokens)} tokens, paid on {total_turns:,} turns this week",
                f"Target: ≤ 2,000 tokens (Anthropic's 200-line recommendation)",
            ],
            fix_action=(
                f"Trim `{_shorten(path)}` from {format_tokens(tokens)} toward the 2k-token target. "
                "Move command recipes and playbooks into separate files referenced via `@filename` "
                "so they load only on demand."
            ),
        ))

    return results


def _shorten(path: Path) -> str:
    s = str(path)
    home = str(Path.home())
    if s.startswith(home):
        s = "~" + s[len(home):]
    if len(s) <= 60:
        return s
    return "…" + s[-57:]
