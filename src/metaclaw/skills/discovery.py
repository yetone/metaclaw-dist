"""Skill discovery - scan filesystem for SKILL.md files."""

from __future__ import annotations

from pathlib import Path

from metaclaw.config import SkillsConfig
from metaclaw.skills.parser import Skill, parse_skill


def _get_search_paths(config: SkillsConfig) -> list[Path]:
    """Build ordered list of skill search paths (higher priority first)."""
    paths: list[Path] = []

    # Project-level skills
    cwd = Path.cwd()
    paths.append(cwd / ".metaclaw" / "skills")
    paths.append(cwd / ".agents" / "skills")  # Cross-client interop

    # User-level skills
    home = Path.home()
    paths.append(home / ".metaclaw" / "skills")
    paths.append(home / ".agents" / "skills")

    # Custom search paths from config
    for p in config.search_paths:
        paths.append(Path(p).expanduser())

    # Built-in skills (lowest priority)
    builtin = Path(__file__).parent / "builtin"
    paths.append(builtin)

    return paths


def discover_skills(config: SkillsConfig | None = None) -> list[Skill]:
    """Discover all available skills by scanning search paths.

    Higher priority paths override lower priority ones (by skill name).
    """
    if config is None:
        config = SkillsConfig()

    search_paths = _get_search_paths(config)
    skills_by_name: dict[str, Skill] = {}

    # Scan in reverse order so higher-priority paths override
    for base_path in reversed(search_paths):
        if not base_path.exists():
            continue

        # Look for SKILL.md files in subdirectories
        for skill_md in base_path.glob("*/SKILL.md"):
            skill = parse_skill(skill_md)
            if skill:
                skills_by_name[skill.name] = skill

        # Also check for SKILL.md directly in the search path
        direct = base_path / "SKILL.md"
        if direct.exists():
            skill = parse_skill(direct)
            if skill:
                skills_by_name[skill.name] = skill

    return sorted(skills_by_name.values(), key=lambda s: s.name)
