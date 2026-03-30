"""MetaClaw CLI - Entry point for all user interactions."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from metaclaw import __version__

app = typer.Typer(
    name="metaclaw",
    help="MetaClaw - Skill-first LLM agent platform with multi-channel bridging",
    no_args_is_help=True,
)
console = Console()

# Sub-command groups
skill_app = typer.Typer(help="Manage skills")
channel_app = typer.Typer(help="Manage channels")
app.add_typer(skill_app, name="skill")
app.add_typer(channel_app, name="channel")


@app.command()
def run(
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to metaclaw.toml"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="LLM model to use"),
    working_dir: Optional[str] = typer.Option(None, "--workdir", "-w", help="Working directory"),
) -> None:
    """Start MetaClaw in interactive terminal mode."""
    from metaclaw.config import get_config

    cfg = get_config(config)
    if model:
        cfg.llm.model = model
    if working_dir:
        cfg.agent.working_directory = working_dir

    console.print(
        Panel(
            f"[bold green]MetaClaw v{__version__}[/bold green]\n"
            f"Model: [cyan]{cfg.llm.model}[/cyan] | "
            f"Max iterations: [cyan]{cfg.agent.max_iterations}[/cyan]",
            title="🦀 MetaClaw Agent",
            border_style="green",
        )
    )

    from metaclaw.core.agent import Agent

    agent = Agent(cfg)
    asyncio.run(_interactive_loop(agent))


async def _interactive_loop(agent: "Agent") -> None:
    """Run the interactive REPL loop."""
    from metaclaw.core.context import Session

    session = Session()
    console.print("[dim]Type your message (Ctrl+C to exit)[/dim]\n")

    while True:
        try:
            user_input = Prompt.ask("[bold blue]You[/bold blue]")
            if not user_input.strip():
                continue

            console.print()
            response = await agent.run(session, user_input)
            console.print(f"\n[bold green]MetaClaw[/bold green]: {response}\n")

        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/dim]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error[/bold red]: {e}\n")


@app.command()
def start(
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to metaclaw.toml"),
) -> None:
    """Start MetaClaw server with all configured channels."""
    from metaclaw.config import get_config

    cfg = get_config(config)

    console.print(
        Panel(
            f"[bold green]MetaClaw Server v{__version__}[/bold green]\n"
            f"Model: [cyan]{cfg.llm.model}[/cyan]",
            title="🦀 MetaClaw Server",
            border_style="green",
        )
    )

    from metaclaw.server import start_server

    asyncio.run(start_server(cfg))


@app.command()
def init() -> None:
    """Interactive setup wizard for MetaClaw."""
    console.print(
        Panel(
            "[bold]Welcome to MetaClaw Setup![/bold]\n\n"
            "This wizard will help you configure MetaClaw step by step.\n"
            "You can always edit metaclaw.toml later.",
            title="🦀 MetaClaw Init",
            border_style="cyan",
        )
    )

    # Step 1: LLM Provider
    console.print("\n[bold]Step 1: Choose your LLM provider[/bold]\n")
    providers = {
        "1": ("claude", "Anthropic Claude (recommended)", "ANTHROPIC_API_KEY"),
        "2": ("gpt4", "OpenAI GPT-4", "OPENAI_API_KEY"),
        "3": ("gemini", "Google Gemini", "GEMINI_API_KEY"),
        "4": ("azure", "Azure OpenAI", "AZURE_API_KEY"),
        "5": ("huggingface", "Hugging Face", "HUGGINGFACE_API_KEY"),
    }
    for key, (_, name, _) in providers.items():
        console.print(f"  [cyan]{key}[/cyan]) {name}")

    choice = Prompt.ask("\nSelect provider", choices=list(providers.keys()), default="1")
    model_alias, provider_name, api_key_env = providers[choice]

    # Step 2: API Key
    console.print(f"\n[bold]Step 2: Configure {provider_name}[/bold]\n")
    api_key = Prompt.ask(f"Enter your API key (stored in .env as {api_key_env})", password=True)

    # Step 3: Channels
    console.print("\n[bold]Step 3: Enable channels (optional)[/bold]\n")
    available_channels = [
        "slack", "discord", "telegram", "wechat", "line",
        "whatsapp", "email", "webhook", "twilio",
        "google_chat", "teams", "zoom",
    ]
    enabled_channels: list[str] = []
    for ch in available_channels:
        if Confirm.ask(f"  Enable {ch}?", default=False):
            enabled_channels.append(ch)

    # Generate config files
    config_path = Path("metaclaw.toml")
    env_path = Path(".env")

    # Build metaclaw.toml
    lines = [
        "# MetaClaw Configuration",
        "# Generated by `metaclaw init`\n",
        "[llm]",
        f'model = "{model_alias}"',
        f'api_key_env = "{api_key_env}"',
        "",
        "[agent]",
        "max_iterations = 25",
        'sandbox = "basic"',
        "",
        "[skills]",
        "auto_discover = true",
        "",
    ]
    for ch in available_channels:
        lines.append(f"[channels.{ch}]")
        lines.append(f"enabled = {'true' if ch in enabled_channels else 'false'}")
        lines.append("")

    config_path.write_text("\n".join(lines))

    # Build .env
    env_lines = [
        "# MetaClaw Environment Variables",
        f"{api_key_env}={api_key}",
    ]
    env_path.write_text("\n".join(env_lines) + "\n")

    console.print(
        Panel(
            f"[green]✓[/green] Created [cyan]{config_path}[/cyan]\n"
            f"[green]✓[/green] Created [cyan]{env_path}[/cyan]\n\n"
            "Next steps:\n"
            "  [cyan]metaclaw run[/cyan]     - Start interactive agent\n"
            "  [cyan]metaclaw start[/cyan]   - Start server with channels",
            title="Setup Complete!",
            border_style="green",
        )
    )


@app.command()
def version() -> None:
    """Show MetaClaw version."""
    console.print(f"MetaClaw v{__version__}")


# -- Skill sub-commands --


@skill_app.command("list")
def skill_list() -> None:
    """List all discovered skills."""
    from metaclaw.config import get_config
    from metaclaw.skills.discovery import discover_skills

    cfg = get_config()
    skills = discover_skills(cfg.skills)

    table = Table(title="Installed Skills")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Source", style="dim")

    for skill in skills:
        table.add_row(skill.name, skill.description, skill.source)

    console.print(table)


@skill_app.command("install")
def skill_install(
    source: str = typer.Argument(help="Skill URL, registry name, or local path"),
) -> None:
    """Install a skill from URL, registry, or local path."""
    from metaclaw.skills.installer import install_skill

    console.print(f"Installing skill from [cyan]{source}[/cyan]...")
    result = install_skill(source)
    if result.success:
        console.print(f"[green]✓[/green] Installed skill: [cyan]{result.name}[/cyan]")
    else:
        console.print(f"[red]✗[/red] Failed: {result.error}")


@skill_app.command("create")
def skill_create(
    name: str = typer.Argument(help="Name for the new skill"),
    description: str = typer.Option("", "--desc", "-d", help="Skill description"),
) -> None:
    """Create a new skill template."""
    from metaclaw.skills.creator import create_skill_template

    path = create_skill_template(name, description)
    console.print(f"[green]✓[/green] Created skill template at [cyan]{path}[/cyan]")


# -- Channel sub-commands --


@channel_app.command("list")
def channel_list() -> None:
    """List all configured channels and their status."""
    from metaclaw.config import get_config

    cfg = get_config()
    table = Table(title="Channels")
    table.add_column("Channel", style="cyan")
    table.add_column("Enabled", style="white")

    all_channels = [
        "slack", "discord", "telegram", "wechat", "line",
        "whatsapp", "email", "webhook", "twilio",
        "google_chat", "teams", "zoom",
    ]
    for ch in all_channels:
        ch_cfg = cfg.channels.get(ch)
        enabled = ch_cfg.enabled if ch_cfg else False
        status = "[green]✓[/green]" if enabled else "[dim]✗[/dim]"
        table.add_row(ch, status)

    console.print(table)


if __name__ == "__main__":
    app()
