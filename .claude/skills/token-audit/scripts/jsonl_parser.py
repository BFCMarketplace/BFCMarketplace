#!/usr/bin/env python3
"""
JSONL transcript parser for Claude Code sessions.

Walks transcripts from two locations and emits structured Turn + Session data
for downstream leak detectors. All analysis is local — transcript content
never leaves the machine.

Scan roots:
  1. ~/.claude/projects/**/*.jsonl
     — Claude Code CLI sessions
  2. ~/Library/Application Support/Claude/local-agent-mode-sessions/
        **/.claude/projects/**/*.jsonl
     — Claude desktop cowork (local-agent-mode) sessions. Each cowork session
     ships its own nested .claude/projects/ tree with the same JSONL schema.
     The `audit.jsonl` at each session root has a DIFFERENT schema and is
     intentionally skipped.

Schema reverse-engineered from real JSONLs (Apr 2026):
  Top-level types: assistant, user, system, attachment, file-history-snapshot,
                   permission-mode, last-prompt, queue-operation
  Common fields:   parentUuid, uuid, sessionId, cwd, timestamp, isSidechain, type
  assistant turns: message.{model, content[], usage}
  user turns:      message.content[] with tool_result items
  attachment:      attachment.{type, hookName, hookEvent, content}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Optional


# ─────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────


@dataclass
class Usage:
    input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return (
            self.input_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
            + self.output_tokens
        )

    @property
    def context_size(self) -> int:
        """Approximate tokens fed into the model on this turn."""
        return (
            self.input_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
        )

    @property
    def cache_hit_ratio(self) -> float:
        total_in = self.input_tokens + self.cache_read_input_tokens
        if total_in == 0:
            return 0.0
        return self.cache_read_input_tokens / total_in


@dataclass
class ToolCall:
    name: str
    input_summary: dict  # small subset, not the full input
    tool_use_id: str = ""


@dataclass
class ToolResult:
    tool_use_id: str
    is_error: bool
    content_size: int  # characters in content, not tokens


@dataclass
class HookEvent:
    hook_event: str  # SessionStart, PreCompact, PostToolUse, ...
    hook_name: str   # SessionStart:startup, SessionStart:resume, ...
    content_size: int  # characters of hook output


@dataclass
class Turn:
    turn_type: str
    uuid: str
    parent_uuid: Optional[str]
    session_id: str
    cwd: str
    timestamp: Optional[datetime]
    is_sidechain: bool

    model: Optional[str] = None
    usage: Optional[Usage] = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    hook: Optional[HookEvent] = None
    text_chars: int = 0  # size of text output (chars, not tokens)


@dataclass
class Session:
    session_id: str
    jsonl_path: Path
    cwd: str
    first_timestamp: Optional[datetime] = None
    last_timestamp: Optional[datetime] = None
    turns: list[Turn] = field(default_factory=list)

    # Lazily-computed aggregates (filled by aggregate()).
    total_usage: Usage = field(default_factory=Usage)
    turn_count: int = 0
    sidechain_turn_count: int = 0
    models_used: dict[str, int] = field(default_factory=dict)  # model → turn count
    tool_call_counts: dict[str, int] = field(default_factory=dict)
    hook_fire_counts: dict[str, int] = field(default_factory=dict)  # hookName → count
    hook_content_bytes: dict[str, int] = field(default_factory=dict)  # hookName → bytes
    file_reads: dict[str, int] = field(default_factory=dict)  # file_path → read count
    peak_context_size: int = 0

    @property
    def project(self) -> str:
        """Human-readable project name from cwd."""
        return Path(self.cwd).name if self.cwd else "unknown"

    @property
    def duration_minutes(self) -> float:
        if not (self.first_timestamp and self.last_timestamp):
            return 0.0
        return (self.last_timestamp - self.first_timestamp).total_seconds() / 60.0


# ─────────────────────────────────────────────────────────────────
# Parsing
# ─────────────────────────────────────────────────────────────────


def _parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        # JSONL timestamps are ISO 8601 with Z
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _parse_usage(usage_dict: Optional[dict]) -> Optional[Usage]:
    if not isinstance(usage_dict, dict):
        return None
    return Usage(
        input_tokens=int(usage_dict.get("input_tokens", 0) or 0),
        cache_creation_input_tokens=int(usage_dict.get("cache_creation_input_tokens", 0) or 0),
        cache_read_input_tokens=int(usage_dict.get("cache_read_input_tokens", 0) or 0),
        output_tokens=int(usage_dict.get("output_tokens", 0) or 0),
    )


def _parse_assistant_content(content: list) -> tuple[list[ToolCall], int]:
    """Return (tool_calls, text_char_count)."""
    tool_calls = []
    text_chars = 0
    for item in content or []:
        if not isinstance(item, dict):
            continue
        t = item.get("type")
        if t == "tool_use":
            name = item.get("name", "")
            raw_input = item.get("input", {}) or {}
            # Keep a small, privacy-safe summary only.
            input_summary = {}
            if name in ("Read", "Edit", "Write"):
                input_summary["file_path"] = raw_input.get("file_path", "")
            elif name == "Bash":
                cmd = raw_input.get("command", "")
                # Strip to first token for signal (e.g., "git", "npm"); avoid capturing secrets.
                input_summary["command_head"] = cmd.split()[0] if cmd else ""
            elif name == "Task":
                input_summary["subagent_type"] = raw_input.get("subagent_type", "general-purpose")
            elif name == "Grep":
                input_summary["has_pattern"] = bool(raw_input.get("pattern"))
            tool_calls.append(ToolCall(
                name=name,
                input_summary=input_summary,
                tool_use_id=item.get("id", ""),
            ))
        elif t == "text":
            text_chars += len(item.get("text", "") or "")
    return tool_calls, text_chars


def _parse_user_content(content) -> list[ToolResult]:
    """Extract tool_result items from a user turn. Sizes only, not content."""
    results = []
    if not isinstance(content, list):
        return results
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "tool_result":
            continue
        raw = item.get("content", "")
        # Count characters; don't retain the payload.
        if isinstance(raw, list):
            size = sum(len(str(p.get("text", "") if isinstance(p, dict) else p)) for p in raw)
        else:
            size = len(str(raw))
        results.append(ToolResult(
            tool_use_id=item.get("tool_use_id", ""),
            is_error=bool(item.get("is_error", False)),
            content_size=size,
        ))
    return results


def _parse_attachment(attachment: dict) -> Optional[HookEvent]:
    """Only extracts hook events. Other attachment types return None."""
    if not isinstance(attachment, dict):
        return None
    att_type = attachment.get("type", "")
    if "hook" not in att_type.lower():
        return None
    content = attachment.get("content", "") or ""
    return HookEvent(
        hook_event=attachment.get("hookEvent", ""),
        hook_name=attachment.get("hookName", ""),
        content_size=len(str(content)),
    )


def parse_turn(raw: dict) -> Optional[Turn]:
    """Parse one JSONL line into a Turn. Returns None for irrelevant types."""
    turn_type = raw.get("type", "")
    # Skip types that carry no usage/hook/tool signal.
    if turn_type in ("permission-mode", "last-prompt", "queue-operation", "file-history-snapshot"):
        return None

    turn = Turn(
        turn_type=turn_type,
        uuid=raw.get("uuid", ""),
        parent_uuid=raw.get("parentUuid"),
        session_id=raw.get("sessionId", ""),
        cwd=raw.get("cwd", ""),
        timestamp=_parse_timestamp(raw.get("timestamp")),
        is_sidechain=bool(raw.get("isSidechain", False)),
    )

    if turn_type == "assistant":
        msg = raw.get("message", {}) or {}
        turn.model = msg.get("model")
        turn.usage = _parse_usage(msg.get("usage"))
        turn.tool_calls, turn.text_chars = _parse_assistant_content(msg.get("content", []))
    elif turn_type == "user":
        msg = raw.get("message", {}) or {}
        content = msg.get("content") if isinstance(msg, dict) else None
        turn.tool_results = _parse_user_content(content)
    elif turn_type == "attachment":
        turn.hook = _parse_attachment(raw.get("attachment", {}))
        # Attachments with no hook signal are kept as blank turns for ordering.
    # "system" turns carry metadata; we include them for ordering but extract nothing.

    return turn


# ─────────────────────────────────────────────────────────────────
# Session-level walk + aggregation
# ─────────────────────────────────────────────────────────────────


# Default scan roots for `iter_session_jsonls(None, ...)`.
# Claude Code CLI writes here:
CLAUDE_CODE_PROJECTS_DIR = Path.home() / ".claude" / "projects"
# Claude desktop "cowork" / local-agent-mode sessions write here. Each session
# folder contains its own nested .claude/projects/<encoded-cwd>/<uuid>.jsonl
# transcript in the same schema. The session root also contains an audit.jsonl
# with a DIFFERENT schema — we exclude it by requiring `.claude/projects/`
# in the path.
CLAUDE_COWORK_SESSIONS_DIR = (
    Path.home() / "Library" / "Application Support" / "Claude" / "local-agent-mode-sessions"
)


def _default_jsonl_paths() -> Iterator[Path]:
    """Yield all transcript JSONLs from Claude Code CLI + Claude desktop cowork."""
    if CLAUDE_CODE_PROJECTS_DIR.exists():
        yield from CLAUDE_CODE_PROJECTS_DIR.rglob("*.jsonl")
    if CLAUDE_COWORK_SESSIONS_DIR.exists():
        # Restrict to transcripts under each cowork session's `.claude/projects/`
        # so we skip the session-root `audit.jsonl` (different schema).
        marker = f"{Path('.claude') / 'projects'}{Path('/')}"  # ".claude/projects/"
        for p in CLAUDE_COWORK_SESSIONS_DIR.rglob("*.jsonl"):
            if marker in str(p):
                yield p


def iter_session_jsonls(
    claude_projects_dir: Optional[Path] = None,
    since_days: Optional[int] = None,
) -> Iterator[Path]:
    """Yield JSONL transcript paths, optionally filtered by mtime.

    With `claude_projects_dir=None` (default), walks both:
      - ~/.claude/projects/                                          (Claude Code CLI)
      - ~/Library/Application Support/Claude/local-agent-mode-sessions/
                                                                    (Claude desktop cowork)
    Pass an explicit Path to walk only that directory (with `**/*.jsonl`).
    """
    cutoff_ts = None
    if since_days is not None:
        cutoff_ts = datetime.now(timezone.utc).timestamp() - (since_days * 86400)
    if claude_projects_dir is None:
        source = _default_jsonl_paths()
    else:
        if not claude_projects_dir.exists():
            return
        source = claude_projects_dir.rglob("*.jsonl")
    seen: set[Path] = set()
    for p in source:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        if cutoff_ts is not None and p.stat().st_mtime < cutoff_ts:
            continue
        yield p


def parse_session(jsonl_path: Path, since: Optional[datetime] = None) -> Session:
    """Parse one JSONL into a Session with aggregates.

    If `since` is given, turns older than that are skipped. This is critical
    because session files are appended to on resume — a file with recent
    mtime can contain months of earlier turns.
    """
    session = Session(
        session_id=jsonl_path.stem,
        jsonl_path=jsonl_path,
        cwd="",
    )

    with jsonl_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            turn = parse_turn(raw)
            if turn is None:
                continue

            # Turn-level time filter — session files grow on resume, so a
            # recent mtime doesn't mean all turns are recent.
            if since is not None and turn.timestamp and turn.timestamp < since:
                continue

            # Fill session-level cwd from first turn that has one.
            if not session.cwd and turn.cwd:
                session.cwd = turn.cwd
            if not session.session_id and turn.session_id:
                session.session_id = turn.session_id

            # Track first/last timestamps.
            if turn.timestamp:
                if session.first_timestamp is None or turn.timestamp < session.first_timestamp:
                    session.first_timestamp = turn.timestamp
                if session.last_timestamp is None or turn.timestamp > session.last_timestamp:
                    session.last_timestamp = turn.timestamp

            session.turns.append(turn)
            _accumulate(session, turn)

    session.turn_count = len(session.turns)
    return session


def _accumulate(session: Session, turn: Turn) -> None:
    """Fold one turn into session-level aggregates."""
    if turn.is_sidechain:
        session.sidechain_turn_count += 1

    if turn.usage:
        session.total_usage.input_tokens += turn.usage.input_tokens
        session.total_usage.cache_creation_input_tokens += turn.usage.cache_creation_input_tokens
        session.total_usage.cache_read_input_tokens += turn.usage.cache_read_input_tokens
        session.total_usage.output_tokens += turn.usage.output_tokens
        ctx = turn.usage.context_size
        if ctx > session.peak_context_size:
            session.peak_context_size = ctx

    if turn.model:
        session.models_used[turn.model] = session.models_used.get(turn.model, 0) + 1

    for call in turn.tool_calls:
        session.tool_call_counts[call.name] = session.tool_call_counts.get(call.name, 0) + 1
        if call.name == "Read":
            fp = call.input_summary.get("file_path", "")
            if fp:
                session.file_reads[fp] = session.file_reads.get(fp, 0) + 1

    if turn.hook:
        name = turn.hook.hook_name or turn.hook.hook_event
        session.hook_fire_counts[name] = session.hook_fire_counts.get(name, 0) + 1
        session.hook_content_bytes[name] = (
            session.hook_content_bytes.get(name, 0) + turn.hook.content_size
        )


def parse_all_sessions(
    claude_projects_dir: Optional[Path] = None,
    since_days: Optional[int] = 7,
) -> list[Session]:
    """Parse every JSONL transcript across the default scan roots.

    With `claude_projects_dir=None`, walks both Claude Code CLI sessions
    (~/.claude/projects/) AND Claude desktop cowork sessions
    (~/Library/Application Support/Claude/local-agent-mode-sessions/).

    Two-stage filter: mtime skips whole files, then turn timestamp skips
    old turns inside resumed files.
    """
    sessions = []
    since: Optional[datetime] = None
    if since_days is not None:
        since = datetime.now(timezone.utc) - timedelta(days=since_days)
    for jsonl_path in iter_session_jsonls(claude_projects_dir, since_days=since_days):
        try:
            sess = parse_session(jsonl_path, since=since)
            if sess.turn_count > 0:
                sessions.append(sess)
        except Exception as e:
            # Don't let one malformed session kill the whole audit.
            print(f"warn: failed to parse {jsonl_path}: {e}", flush=True)
    return sessions


if __name__ == "__main__":
    # CLI smoke test: `python jsonl_parser.py [--days N]`
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()
    sessions = parse_all_sessions(since_days=args.days)
    print(f"Parsed {len(sessions)} sessions from last {args.days} days")
    total_cost_tokens = sum(s.total_usage.total for s in sessions)
    print(f"Total tokens across sessions: {total_cost_tokens:,}")
    top = sorted(sessions, key=lambda s: s.total_usage.total, reverse=True)[:5]
    for s in top:
        print(f"  {s.project:40s}  {s.turn_count:4d} turns  {s.total_usage.total:>12,} tok  "
              f"peak_ctx={s.peak_context_size:>9,}")
