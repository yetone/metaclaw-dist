"""In-memory skill catalog and management."""

from __future__ import annotations

from metaclaw.config import SkillsConfig
from metaclaw.skills.discovery import discover_skills
from metaclaw.skills.parser import Skill


class SkillRegistry:
    """In-memory registry of available skills.

    Provides a catalog for the system prompt (tier 1: names + descriptions)
    and full skill content on activation (tier 2: full SKILL.md body).
    """

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def load(self, config: SkillsConfig | None = None) -> None:
        """Discover and load all available skills."""
        for skill in discover_skills(config):
            self._skills[skill.name] = skill

    def register(self, skill: Skill) -> None:
        """Register a single skill."""
        self._skills[skill.name] = skill

    def unregister(self, name: str) -> bool:
        """Unregister a skill by name. Returns True if it existed."""
        return self._skills.pop(name, None) is not None

    def get(self, name: str) -> Skill | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def get_all(self) -> list[Skill]:
        """Get all registered skills."""
        return list(self._skills.values())

    def get_catalog(self) -> str:
        """Generate the skill catalog text for the system prompt.

        This is tier 1 of progressive disclosure: just names and descriptions.
        Roughly 50-100 tokens per skill.
        """
        if not self._skills:
            return ""

        entries = [skill.catalog_entry for skill in sorted(
            self._skills.values(), key=lambda s: s.name
        )]
        return "\n".join(entries)

    def get_skill_content(self, name: str) -> str | None:
        """Get the full skill content for context injection (tier 2).

        Returns the SKILL.md body wrapped in structured tags.
        """
        skill = self._skills.get(name)
        if skill is None:
            return None

        parts = [f'<skill_content name="{skill.name}">']
        parts.append(skill.body)

        if skill.resources:
            parts.append("<skill_resources>")
            for resource in skill.resources:
                parts.append(f"  <file>{resource}</file>")
            parts.append("</skill_resources>")

        parts.append("</skill_content>")
        return "\n".join(parts)

    def search(self, query: str) -> list[Skill]:
        """Search skills by name or description keywords."""
        query_lower = query.lower()
        results = []
        for skill in self._skills.values():
            if (
                query_lower in skill.name.lower()
                or query_lower in skill.description.lower()
            ):
                results.append(skill)
        return results
