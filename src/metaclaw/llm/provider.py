"""Unified LLM provider interface wrapping litellm."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from metaclaw.llm.models import resolve_model, get_capabilities, ModelCapabilities


@dataclass
class ToolCall:
    """A tool call from the LLM."""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Unified response from any LLM provider."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = ""
    usage: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_litellm(cls, response: Any) -> LLMResponse:
        """Parse a litellm completion response."""
        choice = response.choices[0]
        message = choice.message

        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    args = json.loads(args)
                tool_calls.append(
                    ToolCall(id=tc.id, name=tc.function.name, arguments=args)
                )

        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return cls(
            content=message.content or "",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason or "",
            usage=usage,
        )


class LLMProvider:
    """Unified LLM provider using litellm as the backend."""

    def __init__(
        self,
        model: str,
        api_key_env: str = "",
        base_url: str = "",
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ):
        self.model = resolve_model(model)
        self.capabilities = get_capabilities(model)
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Set API key from env var if specified
        self._api_key = None
        if api_key_env:
            self._api_key = os.getenv(api_key_env)
        self._base_url = base_url or None

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a chat completion request."""
        import litellm

        params: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if self._api_key:
            params["api_key"] = self._api_key
        if self._base_url:
            params["base_url"] = self._base_url

        if tools and self.capabilities.supports_tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        params.update(kwargs)

        if stream and self.capabilities.supports_streaming:
            return await self._stream_chat(params)

        response = await litellm.acompletion(**params)
        return LLMResponse.from_litellm(response)

    async def _stream_chat(self, params: dict[str, Any]) -> LLMResponse:
        """Handle streaming chat completion, accumulating chunks into a full response."""
        import litellm

        params["stream"] = True
        content_parts: list[str] = []
        tool_calls_data: dict[int, dict[str, Any]] = {}
        finish_reason = ""

        response = await litellm.acompletion(**params)

        async for chunk in response:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if chunk.choices[0].finish_reason:
                finish_reason = chunk.choices[0].finish_reason

            if delta.content:
                content_parts.append(delta.content)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_data:
                        tool_calls_data[idx] = {
                            "id": tc.id or "",
                            "name": tc.function.name or "" if tc.function else "",
                            "arguments": "",
                        }
                    if tc.id:
                        tool_calls_data[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls_data[idx]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls_data[idx]["arguments"] += tc.function.arguments

        # Build tool calls
        tool_calls = []
        for idx in sorted(tool_calls_data.keys()):
            data = tool_calls_data[idx]
            args = data["arguments"]
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            tool_calls.append(ToolCall(id=data["id"], name=data["name"], arguments=args))

        return LLMResponse(
            content="".join(content_parts),
            tool_calls=tool_calls,
            finish_reason=finish_reason,
        )

    async def count_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Count tokens for a message list."""
        import litellm

        try:
            return litellm.token_counter(model=self.model, messages=messages)
        except Exception:
            # Rough estimate: 4 chars per token
            total_chars = sum(len(str(m.get("content", ""))) for m in messages)
            return total_chars // 4
