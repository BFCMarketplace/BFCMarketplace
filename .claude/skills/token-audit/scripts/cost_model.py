#!/usr/bin/env python3
"""
Cost model for Claude Code token usage.

Gives ballpark dollar estimates for leak detections and fix savings.
Prices are approximate (USD per million tokens) and intentionally
conservative — this is guidance, not billing.

Sources: public Anthropic pricing as of 2026-Q1. ccusage uses LiteLLM
for exact pricing; if you need precise numbers, prefer `ccusage --json`.
"""

from __future__ import annotations

from dataclasses import dataclass


# Prices in $ per million tokens. Keys match model family prefix (lowercased).
# We match loosely so claude-opus-4-6, claude-opus-4-5-20251101, etc. all resolve.
PRICING = {
    "claude-opus-4": {
        "input": 15.00,
        "output": 75.00,
        "cache_write": 18.75,
        "cache_read": 1.50,
    },
    "claude-sonnet-4": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "claude-haiku-4": {
        "input": 1.00,
        "output": 5.00,
        "cache_write": 1.25,
        "cache_read": 0.10,
    },
    # Fallbacks for older model IDs that still show up in transcripts.
    "claude-3-5-sonnet": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    "claude-3-opus": {
        "input": 15.00,
        "output": 75.00,
        "cache_write": 18.75,
        "cache_read": 1.50,
    },
}

# Fallback pricing when the model can't be resolved (Opus-ish, on the safe side
# of "don't underestimate the cost of a leak").
DEFAULT_PRICING = PRICING["claude-opus-4"]


@dataclass
class TokenBreakdown:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_write_tokens
            + self.cache_read_tokens
        )


def resolve_pricing(model: str | None) -> dict:
    """Match a model ID to its pricing table."""
    if not model:
        return DEFAULT_PRICING
    m = model.lower()
    for key, prices in PRICING.items():
        if m.startswith(key):
            return prices
    return DEFAULT_PRICING


def estimate_cost(tokens: TokenBreakdown, model: str | None) -> float:
    """Ballpark USD cost for a given token breakdown on a model."""
    p = resolve_pricing(model)
    cost = (
        tokens.input_tokens * p["input"]
        + tokens.output_tokens * p["output"]
        + tokens.cache_write_tokens * p["cache_write"]
        + tokens.cache_read_tokens * p["cache_read"]
    ) / 1_000_000
    return round(cost, 4)


def estimate_context_cost(context_tokens: int, model: str | None, cache_hit_ratio: float = 0.7) -> float:
    """Ballpark cost to feed `context_tokens` into the model on a typical turn.

    Most of Claude Code's spend is cache-read + some cache-write. Assume the
    given cache hit ratio (default 70%, matches typical well-warmed sessions).
    """
    cache_read = int(context_tokens * cache_hit_ratio)
    cache_write = context_tokens - cache_read
    tokens = TokenBreakdown(cache_read_tokens=cache_read, cache_write_tokens=cache_write)
    return estimate_cost(tokens, model)


def format_dollars(amount: float) -> str:
    """Format a dollar amount with sensible precision."""
    if amount < 0.01:
        return f"<$0.01"
    if amount < 1:
        return f"${amount:.2f}"
    if amount < 10:
        return f"${amount:.2f}"
    return f"${amount:.0f}"


def format_tokens(n: int) -> str:
    """Format a token count compactly."""
    if n < 1_000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1_000:.1f}k"
    if n < 1_000_000_000:
        return f"{n / 1_000_000:.1f}M"
    return f"{n / 1_000_000_000:.2f}B"


# ─────────────────────────────────────────────────────────────────
# Claude Code plan limits (public data, subject to change).
# Source: Anthropic support + Portkey / TrueFoundry analyses, early 2026.
# ─────────────────────────────────────────────────────────────────

PLAN_LIMITS = {
    "pro":    {"price_usd": 20,  "weekly_sonnet_hours": (40, 80),  "weekly_opus_hours": (0, 0)},
    "max5x":  {"price_usd": 100, "weekly_sonnet_hours": (140, 280), "weekly_opus_hours": (15, 35)},
    "max20x": {"price_usd": 200, "weekly_sonnet_hours": (240, 480), "weekly_opus_hours": (24, 40)},
}

LONG_CONTEXT_THRESHOLD_TOKENS = 200_000    # above this, long-context premium on input/cache-write
CONTEXT_ROT_ZONE_TOKENS = 400_000          # Thariq: attention degrades past here
CACHE_TTL_SECONDS = {"default": 300, "premium": 3600}


def plan_savings_summary(weekly_savings_usd: float, plan: str = "max20x") -> str:
    """Express weekly savings as a share of the user's monthly plan price."""
    price = PLAN_LIMITS.get(plan, {}).get("price_usd", 0)
    if not price:
        return ""
    share = weekly_savings_usd / (price / 4)
    return f"≈ {share:.0%} of one {plan} subscription-week"


if __name__ == "__main__":
    # Smoke tests — synthetic numbers, not tied to any real user.
    cost = estimate_context_cost(200_000, "claude-opus-4-6", cache_hit_ratio=0.7)
    print(f"200k-tok Opus turn @ 70% cache hit: {format_dollars(cost)}")
    weekly = estimate_cost(
        TokenBreakdown(cache_read_tokens=500_000_000, cache_write_tokens=50_000_000,
                       input_tokens=1_000_000, output_tokens=500_000),
        "claude-opus-4-6",
    )
    print(f"Sample weekly usage: {format_dollars(weekly)}")
    print(f"$10/wk saved vs Max20x: {plan_savings_summary(10, 'max20x')}")
