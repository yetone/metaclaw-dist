"""Tests for LLM provider abstraction."""

from __future__ import annotations

from metaclaw.llm.models import resolve_model, get_capabilities, MODEL_ALIASES


def test_resolve_alias():
    assert resolve_model("claude") == "anthropic/claude-sonnet-4-20250514"
    assert resolve_model("gpt4") == "openai/gpt-4o"
    assert resolve_model("gemini") == "gemini/gemini-2.0-flash"


def test_resolve_passthrough():
    """Unknown model strings pass through unchanged."""
    assert resolve_model("custom/model-v1") == "custom/model-v1"


def test_capabilities():
    caps = get_capabilities("claude")
    assert caps.supports_tools is True
    assert caps.supports_streaming is True
    assert caps.max_context_tokens >= 200000


def test_all_aliases_valid():
    """All aliases should resolve to non-empty strings."""
    for alias, model in MODEL_ALIASES.items():
        assert model, f"Alias '{alias}' maps to empty string"
        assert "/" in model, f"Alias '{alias}' should be in 'provider/model' format"
