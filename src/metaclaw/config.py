"""Configuration management for MetaClaw.

Three-tier config: CLI flags > environment variables > metaclaw.toml > defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import toml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


def _find_config_file() -> Path | None:
    """Search for metaclaw.toml in current directory and parents."""
    current = Path.cwd()
    for directory in [current, *current.parents]:
        candidate = directory / "metaclaw.toml"
        if candidate.exists():
            return candidate
    return None


class LLMConfig(BaseModel):
    model: str = "claude"
    api_key_env: str = ""
    max_tokens: int = 4096
    temperature: float = 0.0
    base_url: str = ""


class AgentConfig(BaseModel):
    max_iterations: int = 25
    max_reflections: int = 3
    working_directory: str = "."
    sandbox: str = "basic"  # none, basic, docker
    max_read_size_kb: int = 100
    max_read_lines: int = 2000


class SkillsConfig(BaseModel):
    auto_discover: bool = True
    auto_create: bool = False
    auto_install: bool = False
    search_paths: list[str] = Field(default_factory=list)


class ChannelConfig(BaseModel):
    enabled: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class WebConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])


class MetaClawConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    channels: dict[str, ChannelConfig] = Field(default_factory=dict)
    web: WebConfig = Field(default_factory=WebConfig)

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> MetaClawConfig:
        """Load config from file, env vars, and defaults."""
        # Load .env first
        load_dotenv()

        raw: dict[str, Any] = {}
        path = Path(config_path) if config_path else _find_config_file()
        if path and path.exists():
            raw = toml.loads(path.read_text())

        # Apply env var overrides
        if model := os.getenv("METACLAW_MODEL"):
            raw.setdefault("llm", {})["model"] = model
        if max_iter := os.getenv("METACLAW_MAX_ITERATIONS"):
            raw.setdefault("agent", {})["max_iterations"] = int(max_iter)
        if port := os.getenv("METACLAW_PORT"):
            raw.setdefault("web", {})["port"] = int(port)

        # Parse channel configs
        channels_raw = raw.pop("channels", {})
        channels = {}
        for name, cfg in channels_raw.items():
            if isinstance(cfg, dict):
                channels[name] = ChannelConfig(**cfg)

        config = cls(**{**raw, "channels": channels})
        return config

    def save(self, path: str | Path) -> None:
        """Save config to a TOML file."""
        data = self.model_dump(exclude_defaults=False)
        # Convert ChannelConfig objects to plain dicts
        if "channels" in data:
            data["channels"] = {
                k: v if isinstance(v, dict) else v
                for k, v in data["channels"].items()
            }
        Path(path).write_text(toml.dumps(data))


# Singleton
_config: MetaClawConfig | None = None


def get_config(config_path: str | Path | None = None) -> MetaClawConfig:
    """Get or load the global config."""
    global _config
    if _config is None:
        _config = MetaClawConfig.load(config_path)
    return _config


def reset_config() -> None:
    """Reset the global config (for testing)."""
    global _config
    _config = None
