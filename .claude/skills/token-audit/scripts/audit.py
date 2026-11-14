#!/usr/bin/env python3
"""
token-audit orchestrator.

Runs ccusage for $/token totals, parses local JSONL transcripts for deeper
per-turn analysis, inventories settings/plugins/skills, then calls each
leak detector. Emits structured JSON for a Claude skill to narrate.

All analysis is local. Transcript content is never sent over the network.

Usage:
    python audit.py [--days 7] [--json-only]
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

# Import siblings (works whether run as `python audit.py` or `-m scripts.audit`).
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))

import bottlenecks as bottleneck_mod  # type: ignore
import config_inspector  # type: ignore
import cost_model  # type: ignore
import ensure_ccusage  # type: ignore
import jsonl_parser  # type: ignore


# Detector registry — order is display priority when savings tie.
DETECTOR_MODULES = [
    "detectors.tool_schema",
    "detectors.hook_bloat",
    "detectors.claude_md_bloat",
    "detectors.model_selection",
    "detectors.context",
    "detectors.recurring_scripts",
    "detectors.skill_descriptions",
    "detectors.bash_antipatterns",
    "detectors.cache",
    "detectors.file_reads",
]


def run_audit(days: int = 7) -> dict:
    """Run the full audit. Returns a JSON-serializable dict."""
    # 1. ccusage totals (best-effort — absence shouldn't block the audit).
    ccusage_data, ccusage_error = _run_ccusage(days)

    # 2. Parse JSONL transcripts.
    sessions = jsonl_parser.parse_all_sessions(since_days=days)

    # 3. Inventory config.
    config = config_inspector.build_snapshot()

    # 4. Run all detectors.
    all_leaks = []
    detector_errors: list[str] = []
    for mod_path in DETECTOR_MODULES:
        try:
            mod = importlib.import_module(mod_path)
            leaks = mod.detect(sessions, config)
            all_leaks.extend(leaks)
        except Exception as e:
            detector_errors.append(f"{mod_path}: {type(e).__name__}: {e}")

    # 5. Rank leaks by weekly savings (desc).
    all_leaks.sort(key=lambda l: l.est_weekly_savings_usd, reverse=True)

    # 6. Assemble summary.
    total_sessions = len(sessions)
    total_turns = sum(s.turn_count for s in sessions)
    model_mix: dict[str, int] = {}
    for s in sessions:
        for m, c in s.models_used.items():
            model_mix[m] = model_mix.get(m, 0) + c

    summary = {
        "window_days": days,
        "session_count": total_sessions,
        "turn_count": total_turns,
        "model_mix": model_mix,
        "tool_search_enabled": config.tool_search_enabled,
        "tool_search_mode": config.tool_search_mode,
        "hooks_configured": len(config.hooks),
        "skills_installed": len(config.skills),
        "mcp_servers_configured": len(config.mcp_servers_configured),
        "plugins_enabled": len(config.enabled_plugins),
    }

    # 7. Top-line savings potential + plan context.
    total_weekly_savings = sum(l.est_weekly_savings_usd for l in all_leaks)
    savings_as_plan_share = cost_model.plan_savings_summary(total_weekly_savings, "max20x")

    # 8. Bottleneck analysis — where to look first.
    bns = bottleneck_mod.compute_bottlenecks(sessions, config, top_n=3)
    bottlenecks_out = {
        kind: [_bottleneck_to_dict(b) for b in bns_list]
        for kind, bns_list in bns.items()
    }

    return {
        "summary": summary,
        "ccusage": ccusage_data,
        "ccusage_error": ccusage_error,
        "detector_errors": detector_errors,
        "bottlenecks": bottlenecks_out,
        "leaks": [_leak_to_dict(l) for l in all_leaks],
        "total_weekly_savings_usd": round(total_weekly_savings, 2),
        "savings_share_of_plan": savings_as_plan_share,
        "generated_at": jsonl_parser.datetime.now(jsonl_parser.timezone.utc).isoformat(),
    }


def _bottleneck_to_dict(b) -> dict:
    return {
        "kind": b.kind,
        "label": b.label,
        "id": b.id,
        "est_weekly_cost_usd": round(b.est_weekly_cost_usd, 2),
        "est_weekly_tokens": b.est_weekly_tokens,
        "share_of_total_pct": b.share_of_total_pct,
        "contributing_categories": b.contributing_categories,
        "evidence": b.evidence,
        "fix_action": b.fix_action,
    }


def _run_ccusage(days: int) -> tuple[dict | None, str | None]:
    """Run `ccusage daily --since=YYYYMMDD --until=YYYYMMDD --json`.

    Scope tightly by `--until` as well so users with months of history don't
    time out. Uses a generous timeout but still best-effort — if it fails,
    the audit continues without it and the report notes the absence.
    """
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days)).strftime("%Y%m%d")
    until = now.strftime("%Y%m%d")
    rc, out, err = ensure_ccusage.run_ccusage(
        ["daily", f"--since={since}", f"--until={until}", "--json"], timeout=180
    )
    if rc != 0:
        return None, (err.strip() or "ccusage failed") + f" (try: npx ccusage@latest daily --since={since})"
    try:
        return json.loads(out), None
    except json.JSONDecodeError as e:
        return None, f"ccusage JSON parse failed: {e}"


def _leak_to_dict(leak) -> dict:
    d = asdict(leak)
    # Round cost fields to 2 decimals for readability.
    for key in ("est_weekly_cost_usd", "est_weekly_savings_usd"):
        if key in d:
            d[key] = round(d[key], 2)
    return d


def main():
    ap = argparse.ArgumentParser(description="Audit Claude Code token usage for leaks.")
    ap.add_argument("--days", type=int, default=7, help="Audit window in days (default: 7)")
    ap.add_argument("--json-only", action="store_true", help="Suppress human-readable prelude")
    args = ap.parse_args()

    result = run_audit(days=args.days)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
