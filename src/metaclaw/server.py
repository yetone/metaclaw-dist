"""MetaClaw server - starts channels, web server, and agent."""

from __future__ import annotations

import asyncio
import logging

import uvicorn
from rich.console import Console
from rich.table import Table

from metaclaw.channels.manager import ChannelManager
from metaclaw.channels.router import MessageRouter
from metaclaw.config import MetaClawConfig
from metaclaw.core.agent import Agent
from metaclaw.skills.registry import SkillRegistry
from metaclaw.web.app import create_app
from metaclaw.web.routes.webhooks import set_channel_manager

logger = logging.getLogger(__name__)
console = Console()


async def start_server(config: MetaClawConfig) -> None:
    """Start the MetaClaw server with all configured components."""

    # 1. Initialize agent
    agent = Agent(config)

    # 2. Load skills
    skill_registry = SkillRegistry()
    skill_registry.load(config.skills)
    agent.set_skill_catalog(skill_registry.get_catalog())

    skills = skill_registry.get_all()
    if skills:
        console.print(f"[dim]Loaded {len(skills)} skills[/dim]")

    # 3. Initialize channel router and manager
    router = MessageRouter(agent)
    channel_manager = ChannelManager(config, router)

    # 4. Start channels
    started = await channel_manager.start_all()
    if started:
        table = Table(title="Active Channels", show_header=False)
        table.add_column("Channel", style="cyan")
        table.add_column("Status", style="green")
        for ch in started:
            table.add_row(ch, "✓ connected")
        console.print(table)
    else:
        console.print("[yellow]No channels enabled. Use metaclaw.toml to configure channels.[/yellow]")

    # 5. Set up webhook routes
    set_channel_manager(channel_manager)
    webhook_channels = channel_manager.get_webhook_channels()

    # 6. Start web server (for webhooks and API)
    app = create_app(config)
    web_config = uvicorn.Config(
        app,
        host=config.web.host,
        port=config.web.port,
        log_level="info",
    )
    web_server = uvicorn.Server(web_config)

    console.print(
        f"\n[bold green]MetaClaw server running[/bold green] at "
        f"http://{config.web.host}:{config.web.port}\n"
        f"  API docs: http://localhost:{config.web.port}/docs\n"
        f"  Health:   http://localhost:{config.web.port}/health\n"
    )

    try:
        await web_server.serve()
    except KeyboardInterrupt:
        pass
    finally:
        console.print("\n[dim]Shutting down...[/dim]")
        await channel_manager.stop_all()
