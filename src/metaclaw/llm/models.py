"""Model registry with user-friendly aliases and capability detection."""

from __future__ import annotations

from dataclasses import dataclass, field

# User-friendly aliases -> provider/model strings
MODEL_ALIASES: dict[str, str] = {
    # Anthropic
    "claude": "anthropic/claude-sonnet-4-20250514",
    "claude-opus": "anthropic/claude-opus-4-20250514",
    "claude-haiku": "anthropic/claude-haiku-4-5-20251001",
    "claude-sonnet": "anthropic/claude-sonnet-4-20250514",
    # OpenAI
    "gpt4": "openai/gpt-4o",
    "gpt4-mini": "openai/gpt-4o-mini",
    "gpt4-turbo": "openai/gpt-4-turbo",
    "o1": "openai/o1",
    "o1-mini": "openai/o1-mini",
    "o3-mini": "openai/o3-mini",
    # Google
    "gemini": "gemini/gemini-2.0-flash",
    "gemini-pro": "gemini/gemini-2.5-pro-preview-05-06",
    "gemini-flash": "gemini/gemini-2.0-flash",
    # Azure
    "azure": "azure/gpt-4o",
    "azure-mini": "azure/gpt-4o-mini",
    # Hugging Face
    "huggingface": "huggingface/meta-llama/Llama-3.1-70B-Instruct",
}


@dataclass
class ModelCapabilities:
    """Capabilities of a specific model."""

    supports_tools: bool = True
    supports_streaming: bool = True
    supports_vision: bool = False
    max_context_tokens: int = 128000
    max_output_tokens: int = 4096


# Known capabilities per model prefix
_CAPABILITIES: dict[str, ModelCapabilities] = {
    "anthropic/claude-opus": ModelCapabilities(
        supports_vision=True, max_context_tokens=200000, max_output_tokens=32000
    ),
    "anthropic/claude-sonnet": ModelCapabilities(
        supports_vision=True, max_context_tokens=200000, max_output_tokens=16000
    ),
    "anthropic/claude-haiku": ModelCapabilities(
        supports_vision=True, max_context_tokens=200000, max_output_tokens=8192
    ),
    "openai/gpt-4o": ModelCapabilities(
        supports_vision=True, max_context_tokens=128000, max_output_tokens=16384
    ),
    "openai/o1": ModelCapabilities(
        supports_tools=False, supports_streaming=False, max_context_tokens=200000
    ),
    "gemini/": ModelCapabilities(
        supports_vision=True, max_context_tokens=1000000, max_output_tokens=8192
    ),
}


def resolve_model(model_str: str) -> str:
    """Resolve a model alias to a provider/model string."""
    return MODEL_ALIASES.get(model_str, model_str)


def get_capabilities(model_str: str) -> ModelCapabilities:
    """Get capabilities for a model. Returns defaults if unknown."""
    resolved = resolve_model(model_str)
    for prefix, caps in _CAPABILITIES.items():
        if resolved.startswith(prefix):
            return caps
    return ModelCapabilities()
