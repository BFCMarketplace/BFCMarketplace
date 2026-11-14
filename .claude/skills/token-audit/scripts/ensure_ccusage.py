#!/usr/bin/env python3
"""
Ensure ccusage is available. Returns the command to invoke it.

Strategy: prefer `npx ccusage@latest` (zero-install, always fresh).
Fall back to `ccusage` on PATH if npx is missing. If neither, return None
and let the caller report a clear install hint.
"""

from __future__ import annotations

import shutil
import subprocess


def find_ccusage() -> list[str] | None:
    """Return the command (as argv list) to invoke ccusage, or None."""
    if shutil.which("ccusage"):
        return ["ccusage"]
    if shutil.which("npx"):
        return ["npx", "ccusage@latest"]
    return None


def run_ccusage(extra_args: list[str] | None = None, timeout: int = 60) -> tuple[int, str, str]:
    """Run ccusage. Returns (returncode, stdout, stderr)."""
    cmd = find_ccusage()
    if cmd is None:
        return 127, "", _install_hint()
    full = cmd + (extra_args or [])
    try:
        proc = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"ccusage timed out after {timeout}s"
    except OSError as e:
        return 1, "", f"ccusage failed to launch: {e}"


def _install_hint() -> str:
    return (
        "ccusage not found. Options:\n"
        "  1. Install Node.js 20+ (https://nodejs.org) — then `npx ccusage@latest` works with zero install.\n"
        "  2. Or install globally: `npm install -g ccusage`.\n"
        "ccusage is 13k★ open-source (MIT, by @ryoppippi). All analysis is local."
    )


if __name__ == "__main__":
    cmd = find_ccusage()
    if cmd:
        print(f"Found ccusage: {' '.join(cmd)}")
        rc, out, err = run_ccusage(["--version"], timeout=30)
        if rc == 0:
            print(f"Version check OK: {out.strip()}")
        else:
            print(f"Version check failed (rc={rc}): {err.strip()}")
    else:
        print(_install_hint())
