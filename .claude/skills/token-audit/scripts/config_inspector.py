#!/usr/bin/env python3
"""
Inventory the user's Claude Code configuration.

Reads ~/.claude/settings.json, installed plugins, and skills dirs to build a
ConfigSnapshot that detectors query. Avoids making assumptions about defaults:
tool search state, hooks, skills, MCPs are read from disk, not inferred.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"


@dataclass
class HookConfig:
    event: str      # SessionStart, PreCompact, ...
    matcher: str
    command: str
    timeout: int
    is_async: bool
    scope: str      # "global" or "project:<path>"


@dataclass
class SkillInfo:
    name: str
    path: Path
    scope: str      # "user", "plugin", "project"
    description: str = ""


@dataclass
class ConfigSnapshot:
    tool_search_enabled: bool
    tool_search_mode: str                        # raw ENABLE_TOOL_SEARCH value or "default"
    hooks: list[HookConfig] = field(default_factory=list)
    mcp_servers_configured: list[str] = field(default_factory=list)
    mcp_servers_disabled: list[str] = field(default_factory=list)
    enabled_plugins: list[str] = field(default_factory=list)
    skills: list[SkillInfo] = field(default_factory=list)
    env_vars: dict[str, str] = field(default_factory=dict)
    settings_paths_read: list[Path] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────
# Readers
# ─────────────────────────────────────────────────────────────────


def _load_json_safe(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _detect_tool_search(settings_env: dict, process_env: dict) -> tuple[bool, str]:
    """Return (enabled, mode_string).

    Precedence: process env overrides settings.json. Absence of the var means
    the Claude Code default, which is "on" per Anthropic docs — but we flag
    that as "default" so downstream detectors can be explicit in output.
    """
    raw = process_env.get("ENABLE_TOOL_SEARCH") or settings_env.get("ENABLE_TOOL_SEARCH") or ""
    raw = str(raw).strip()
    if not raw:
        return True, "default"
    # Accepted values: "true"/"false"/"1"/"0"/"auto"/"auto:N"
    low = raw.lower()
    if low in ("false", "0", "off", "no", "disabled"):
        return False, raw
    return True, raw


def _read_hooks(settings: dict, scope: str) -> list[HookConfig]:
    hooks = []
    for event, groups in (settings.get("hooks") or {}).items():
        if not isinstance(groups, list):
            continue
        for group in groups:
            matcher = group.get("matcher", "")
            for hook in group.get("hooks", []) or []:
                hooks.append(HookConfig(
                    event=event,
                    matcher=matcher,
                    command=hook.get("command", ""),
                    timeout=int(hook.get("timeout", 30)),
                    is_async=bool(hook.get("async", False)),
                    scope=scope,
                ))
    return hooks


def _read_mcp_config() -> tuple[list[str], list[str]]:
    """Return (configured_servers, disabled_servers) from settings files."""
    configured: set[str] = set()
    disabled: set[str] = set()

    for settings_path in (CLAUDE_DIR / "settings.json", Path.cwd() / ".claude" / "settings.json"):
        s = _load_json_safe(settings_path)
        if not s:
            continue
        for name in (s.get("mcpServers") or {}).keys():
            configured.add(name)
        for name in s.get("disabledMcpjsonServers") or []:
            disabled.add(name)

    # Also scan ~/.claude.json for user-level MCP config (alternate location).
    alt = _load_json_safe(HOME / ".claude.json")
    if alt:
        for name in (alt.get("mcpServers") or {}).keys():
            configured.add(name)

    return sorted(configured), sorted(disabled)


def _read_skills() -> list[SkillInfo]:
    """Enumerate skills from user, plugin, and project locations."""
    skills: list[SkillInfo] = []

    def _scan_dir(root: Path, scope: str) -> None:
        if not root.exists():
            return
        for skill_md in root.rglob("SKILL.md"):
            skill_dir = skill_md.parent
            desc = _extract_description(skill_md)
            skills.append(SkillInfo(
                name=skill_dir.name,
                path=skill_dir,
                scope=scope,
                description=desc,
            ))

    _scan_dir(CLAUDE_DIR / "skills", "user")
    plugin_cache = CLAUDE_DIR / "plugins" / "cache"
    _scan_dir(plugin_cache, "plugin")
    project_skills = Path.cwd() / ".claude" / "skills"
    _scan_dir(project_skills, "project")

    return skills


def _extract_description(skill_md: Path) -> str:
    """Pull the `description:` line out of SKILL.md frontmatter."""
    try:
        with skill_md.open("r", encoding="utf-8", errors="replace") as f:
            in_frontmatter = False
            for line in f:
                if line.strip() == "---":
                    if in_frontmatter:
                        break
                    in_frontmatter = True
                    continue
                if in_frontmatter and line.lower().startswith("description:"):
                    return line.split(":", 1)[1].strip().strip('"')
    except OSError:
        pass
    return ""


# ─────────────────────────────────────────────────────────────────
# Main snapshot builder
# ─────────────────────────────────────────────────────────────────


def build_snapshot() -> ConfigSnapshot:
    paths_read: list[Path] = []
    user_settings_path = CLAUDE_DIR / "settings.json"
    user_settings = _load_json_safe(user_settings_path) or {}
    if user_settings_path.exists():
        paths_read.append(user_settings_path)

    project_settings_path = Path.cwd() / ".claude" / "settings.json"
    project_settings = _load_json_safe(project_settings_path) or {}
    if project_settings_path.exists():
        paths_read.append(project_settings_path)

    settings_env = {**(user_settings.get("env") or {}), **(project_settings.get("env") or {})}
    tool_search_on, tool_search_mode = _detect_tool_search(settings_env, dict(os.environ))

    hooks = _read_hooks(user_settings, "global") + _read_hooks(project_settings, "project")
    configured_mcps, disabled_mcps = _read_mcp_config()
    enabled_plugins = list(user_settings.get("enabledPlugins") or [])
    skills = _read_skills()

    # Retain a privacy-safe env subset (no tokens, no paths).
    env_subset = {
        k: v for k, v in settings_env.items()
        if k in ("ENABLE_TOOL_SEARCH", "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS",
                 "DISABLE_AUTOCOMPACT", "CLAUDE_CODE_MAX_OUTPUT_TOKENS")
    }

    return ConfigSnapshot(
        tool_search_enabled=tool_search_on,
        tool_search_mode=tool_search_mode,
        hooks=hooks,
        mcp_servers_configured=configured_mcps,
        mcp_servers_disabled=disabled_mcps,
        enabled_plugins=enabled_plugins,
        skills=skills,
        env_vars=env_subset,
        settings_paths_read=paths_read,
    )


if __name__ == "__main__":
    snap = build_snapshot()
    print(f"Tool search: {'ON' if snap.tool_search_enabled else 'OFF'} (mode: {snap.tool_search_mode})")
    print(f"Hooks configured: {len(snap.hooks)}")
    for h in snap.hooks:
        mode = "async" if h.is_async else "sync"
        print(f"  {h.event:16s}  {h.matcher or '(*)':12s}  {mode:5s}  {h.command}")
    print(f"MCP servers: {len(snap.mcp_servers_configured)} configured, "
          f"{len(snap.mcp_servers_disabled)} disabled")
    print(f"Enabled plugins: {len(snap.enabled_plugins)}")
    print(f"Installed skills: {len(snap.skills)}")
    print(f"Env: {snap.env_vars}")
