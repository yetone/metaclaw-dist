"""Skill-first system for MetaClaw self-improvement."""

from metaclaw.skills.parser import Skill, parse_skill
from metaclaw.skills.registry import SkillRegistry
from metaclaw.skills.discovery import discover_skills

__all__ = ["Skill", "parse_skill", "SkillRegistry", "discover_skills"]
