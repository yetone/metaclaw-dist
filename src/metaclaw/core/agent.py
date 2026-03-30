"""Main agent loop implementing the ReAct pattern."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from metaclaw.config import MetaClawConfig
from metaclaw.core.context import Session
from metaclaw.core.tools import ToolRegistry, create_default_registry
from metaclaw.llm.provider import LLMProvider, LLMResponse, ToolCall

console = Console()

SYSTEM_PROMPT = """\
You are MetaClaw, a powerful AI agent that helps users accomplish tasks by using tools.

You have access to the following tools:
- ReadFile: Read file contents with line numbers. Supports offset/limit for large files.
- WriteFile: Write content to files. Creates directories as needed.
- EditFile: Edit files by replacing text. Supports fuzzy matching for imprecise matches.
- Bash: Execute shell commands with timeout support.

Guidelines:
- Break complex tasks into smaller steps.
- Read files before editing them.
- Use EditFile for targeted changes, WriteFile for new files or complete rewrites.
- Always verify your changes after making them.
- If a tool call fails, analyze the error and try a different approach.
- Be concise in your responses.

{skill_catalog}
"""


class Agent:
    """The main agent that orchestrates the LLM + tool loop."""

    def __init__(self, config: MetaClawConfig):
        self.config = config
        self.llm = LLMProvider(
            model=config.llm.model,
            api_key_env=config.llm.api_key_env,
            base_url=config.llm.base_url,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )
        self.tools = create_default_registry(
            working_directory=config.agent.working_directory,
            sandbox=config.agent.sandbox,
            max_read_size_kb=config.agent.max_read_size_kb,
            max_read_lines=config.agent.max_read_lines,
        )
        self._skill_catalog = ""

    def set_skill_catalog(self, catalog: str) -> None:
        """Set the skill catalog text to include in the system prompt."""
        self._skill_catalog = catalog

    def _build_system_prompt(self, session: Session) -> str:
        """Build the system prompt with skill catalog."""
        skill_section = ""
        if self._skill_catalog:
            skill_section = (
                f"\n\nAvailable Skills:\n{self._skill_catalog}\n"
                "To use a skill, just describe the task and the relevant skill "
                "will be automatically activated."
            )
        return SYSTEM_PROMPT.format(skill_catalog=skill_section)

    async def run(self, session: Session, user_message: str) -> str:
        """Run the agent loop for a single user message.

        Returns the final text response from the agent.
        """
        # Ensure system prompt is set
        system_prompt = self._build_system_prompt(session)
        session.add_system_message(system_prompt)

        # Add user message
        session.add_user_message(user_message)

        for iteration in range(self.config.agent.max_iterations):
            # Check context size and compact if needed
            token_estimate = session.get_token_estimate()
            max_context = self.llm.capabilities.max_context_tokens
            if token_estimate > int(max_context * 0.8):
                session.compact(int(max_context * 0.6))

            # Call LLM
            try:
                response = await self.llm.chat(
                    messages=session.get_messages(),
                    tools=self.tools.get_schemas(),
                )
            except Exception as e:
                return f"LLM Error: {e}"

            # No tool calls -> return the response
            if not response.tool_calls:
                session.add_assistant_message(response.content)
                return response.content

            # Process tool calls
            session.add_assistant_message(
                response.content,
                tool_calls=self._serialize_tool_calls(response.tool_calls),
            )

            # Show thinking if any
            if response.content:
                console.print(
                    f"[dim]{response.content}[/dim]"
                )

            # Execute tools (parallel when multiple)
            results = await self._execute_tools(response.tool_calls)

            for tool_call, result in zip(response.tool_calls, results):
                session.add_tool_result(
                    tool_call_id=tool_call.id,
                    tool_name=tool_call.name,
                    result=result,
                )

                # Display tool usage
                self._display_tool_call(tool_call, result)

        return "Reached maximum iterations. Please try breaking the task into smaller steps."

    async def _execute_tools(self, tool_calls: list[ToolCall]) -> list[str]:
        """Execute tool calls, in parallel when there are multiple."""
        if len(tool_calls) == 1:
            result = await self._execute_single_tool(tool_calls[0])
            return [result]

        tasks = [self._execute_single_tool(tc) for tc in tool_calls]
        return await asyncio.gather(*tasks)

    async def _execute_single_tool(self, tool_call: ToolCall) -> str:
        """Execute a single tool call."""
        tool = self.tools.get(tool_call.name)
        if tool is None:
            return f"Error: Unknown tool '{tool_call.name}'"

        try:
            result = await tool.execute(**tool_call.arguments)
            return result
        except Exception as e:
            return f"Error executing {tool_call.name}: {e}"

    def _serialize_tool_calls(
        self, tool_calls: list[ToolCall]
    ) -> list[dict[str, Any]]:
        """Serialize tool calls for message storage."""
        return [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments),
                },
            }
            for tc in tool_calls
        ]

    def _display_tool_call(self, tool_call: ToolCall, result: str) -> None:
        """Display a tool call and its result in the terminal."""
        # Show tool name and key arguments
        args_summary = ""
        if tool_call.name == "Bash":
            args_summary = tool_call.arguments.get("command", "")
        elif tool_call.name in ("ReadFile", "WriteFile", "EditFile"):
            args_summary = tool_call.arguments.get("file_path", "")

        console.print(
            f"  [dim cyan]⚙ {tool_call.name}[/dim cyan]"
            f"[dim]: {args_summary}[/dim]"
        )

        # Show truncated result
        result_preview = result[:500]
        if len(result) > 500:
            result_preview += f"\n... [{len(result)} chars total]"
        console.print(f"  [dim]{result_preview}[/dim]\n")
