"""Skill activator - loads skill content into agent context on demand."""

from __future__ import annotations

from metaclaw.core.context import Session
from metaclaw.skills.registry import SkillRegistry


class SkillActivator:
    """Manages skill activation within agent sessions.

    Skills are activated (their full SKILL.md body injected into context)
    when the agent determines they're relevant or the user explicitly invokes one.
    """

    def __init__(self, registry: SkillRegistry):
        self._registry = registry

    def activate(self, session: Session, skill_name: str) -> str | None:
        """Activate a skill in a session.

        Returns the skill content if newly activated, None if already active.
        """
        if skill_name in session.active_skills:
            return None

        content = self._registry.get_skill_content(skill_name)
        if content is None:
            return None

        session.active_skills.add(skill_name)
        return content

    def deactivate(self, session: Session, skill_name: str) -> bool:
        """Deactivate a skill from a session."""
        if skill_name in session.active_skills:
            session.active_skills.discard(skill_name)
            return True
        return False

    def get_active_content(self, session: Session) -> str:
        """Get combined content of all active skills."""
        parts = []
        for name in session.active_skills:
            content = self._registry.get_skill_content(name)
            if content:
                parts.append(content)
        return "\n\n".join(parts)

    def auto_activate(self, session: Session, user_message: str) -> list[str]:
        """Auto-activate skills based on user message content.

        Uses simple keyword matching against skill descriptions.
        Returns list of newly activated skill names.
        """
        activated: list[str] = []

        # Check for explicit /skill-name invocation
        if user_message.startswith("/"):
            skill_name = user_message.split()[0][1:]  # Remove /
            if self.activate(session, skill_name) is not None:
                activated.append(skill_name)
            return activated

        # Auto-detect based on keyword matching
        matching = self._registry.search(user_message)
        for skill in matching:
            if skill.name not in session.active_skills:
                if self.activate(session, skill.name) is not None:
                    activated.append(skill.name)

        return activated
