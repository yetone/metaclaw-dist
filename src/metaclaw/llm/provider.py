"""Unified LLM provider interface using native SDKs (openai, anthropic)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from metaclaw.llm.models import resolve_model, get_capabilities


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
    def from_openai(cls, response: Any) -> LLMResponse:
        """Parse an OpenAI-compatible completion response."""
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

    @classmethod
    def from_anthropic(cls, response: Any) -> LLMResponse:
        """Parse an Anthropic Messages response."""
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=block.input)
                )

        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }

        return cls(
            content=content,
            tool_calls=tool_calls,
            finish_reason=response.stop_reason or "",
            usage=usage,
        )


def _parse_provider(model: str) -> tuple[str, str]:
    """Extract provider prefix and model name from 'provider/model' string."""
    if "/" in model:
        provider, _, model_name = model.partition("/")
        return provider, model_name
    return "", model


# Provider-specific base URLs for OpenAI-compatible endpoints
_OPENAI_COMPAT_URLS: dict[str, tuple[str, str]] = {
    # provider -> (base_url, api_key_env)
    "gemini": (
        "https://generativelanguage.googleapis.com/v1beta/openai/",
        "GEMINI_API_KEY",
    ),
    "huggingface": (
        "https://api-inference.huggingface.co/v1/",
        "HF_TOKEN",
    ),
}


class LLMProvider:
    """Unified LLM provider using native SDKs."""

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

        self._api_key = None
        if api_key_env:
            self._api_key = os.getenv(api_key_env)
        self._base_url = base_url or None

        self._provider, self._model_name = _parse_provider(self.model)

    def _get_openai_client(self) -> Any:
        """Create an OpenAI-compatible async client."""
        from openai import AsyncOpenAI

        kwargs: dict[str, Any] = {}
        if self._api_key:
            kwargs["api_key"] = self._api_key

        if self._base_url:
            kwargs["base_url"] = self._base_url
        elif self._provider in _OPENAI_COMPAT_URLS:
            url, key_env = _OPENAI_COMPAT_URLS[self._provider]
            kwargs["base_url"] = url
            if not kwargs.get("api_key"):
                kwargs["api_key"] = os.getenv(key_env)

        return AsyncOpenAI(**kwargs)

    def _get_azure_client(self) -> Any:
        """Create an Azure OpenAI async client."""
        from openai import AsyncAzureOpenAI

        kwargs: dict[str, Any] = {}
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["azure_endpoint"] = self._base_url
        else:
            kwargs["azure_endpoint"] = os.getenv("AZURE_API_BASE", "")
        kwargs["api_version"] = os.getenv("AZURE_API_VERSION", "2024-02-01")

        return AsyncAzureOpenAI(**kwargs)

    def _get_anthropic_client(self) -> Any:
        """Create an Anthropic async client."""
        from anthropic import AsyncAnthropic

        kwargs: dict[str, Any] = {}
        if self._api_key:
            kwargs["api_key"] = self._api_key
        if self._base_url:
            kwargs["base_url"] = self._base_url

        return AsyncAnthropic(**kwargs)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        """Send a chat completion request."""
        if self._provider == "anthropic":
            return await self._chat_anthropic(messages, tools, stream, **kwargs)
        return await self._chat_openai(messages, tools, stream, **kwargs)

    # ------------------------------------------------------------------
    # OpenAI-compatible providers (openai, azure, gemini, huggingface)
    # ------------------------------------------------------------------

    async def _chat_openai(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        if self._provider == "azure":
            client = self._get_azure_client()
        else:
            client = self._get_openai_client()

        params: dict[str, Any] = {
            "model": self._model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        if tools and self.capabilities.supports_tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        params.update(kwargs)

        if stream and self.capabilities.supports_streaming:
            return await self._stream_openai(client, params)

        response = await client.chat.completions.create(**params)
        return LLMResponse.from_openai(response)

    async def _stream_openai(self, client: Any, params: dict[str, Any]) -> LLMResponse:
        params["stream"] = True
        content_parts: list[str] = []
        tool_calls_data: dict[int, dict[str, Any]] = {}
        finish_reason = ""

        response = await client.chat.completions.create(**params)

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

    # ------------------------------------------------------------------
    # Anthropic
    # ------------------------------------------------------------------

    async def _chat_anthropic(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> LLMResponse:
        client = self._get_anthropic_client()

        # Anthropic requires system messages as a separate parameter
        system = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"] if isinstance(m["content"], str) else ""
            else:
                chat_messages.append(m)

        params: dict[str, Any] = {
            "model": self._model_name,
            "messages": chat_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if system:
            params["system"] = system

        if tools and self.capabilities.supports_tools:
            # Convert OpenAI tool format → Anthropic tool format
            anthropic_tools = []
            for tool in tools:
                func = tool.get("function", {})
                anthropic_tools.append({
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {}),
                })
            params["tools"] = anthropic_tools

        # Strip kwargs that Anthropic doesn't support
        kwargs.pop("tool_choice", None)
        params.update(kwargs)

        if stream and self.capabilities.supports_streaming:
            return await self._stream_anthropic(client, params)

        response = await client.messages.create(**params)
        return LLMResponse.from_anthropic(response)

    async def _stream_anthropic(
        self, client: Any, params: dict[str, Any]
    ) -> LLMResponse:
        content_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        current_tool: dict[str, Any] | None = None
        finish_reason = ""
        usage: dict[str, int] = {}

        async with client.messages.stream(**params) as stream:
            async for event in stream:
                if event.type == "message_start":
                    if hasattr(event, "message") and event.message.usage:
                        usage["prompt_tokens"] = event.message.usage.input_tokens
                elif event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        current_tool = {
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "arguments": "",
                        }
                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        content_parts.append(event.delta.text)
                    elif event.delta.type == "input_json_delta":
                        if current_tool is not None:
                            current_tool["arguments"] += event.delta.partial_json
                elif event.type == "content_block_stop":
                    if current_tool is not None:
                        args = current_tool["arguments"]
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                args = {}
                        tool_calls.append(
                            ToolCall(
                                id=current_tool["id"],
                                name=current_tool["name"],
                                arguments=args,
                            )
                        )
                        current_tool = None
                elif event.type == "message_delta":
                    if hasattr(event.delta, "stop_reason"):
                        finish_reason = event.delta.stop_reason or ""
                    if hasattr(event, "usage") and event.usage:
                        usage["completion_tokens"] = event.usage.output_tokens

        if "prompt_tokens" in usage and "completion_tokens" in usage:
            usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]

        return LLMResponse(
            content="".join(content_parts),
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=usage,
        )

    # ------------------------------------------------------------------
    # Token counting
    # ------------------------------------------------------------------

    async def count_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Count tokens for a message list (rough estimate)."""
        # ~4 chars per token is a reasonable cross-model approximation
        total_chars = sum(len(str(m.get("content", ""))) for m in messages)
        return total_chars // 4
