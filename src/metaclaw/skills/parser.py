"""SKILL.md parser following the Agent Skills specification from agentskills.io."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Skill:
    """Parsed representation of a SKILL.md file."""

    name: str
    description: str
    body: str  # The markdown body (instructions)
    source: str = ""  # Where this skill was found (path or URL)
    license: str = ""
    compatibility: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    resources: list[str] = field(default_factory=list)  # Associated files

    @property
    def catalog_entry(self) -> str:
        """One-line catalog entry for inclusion in system prompt."""
        return f"- {self.name}: {self.description}"


def parse_skill(path: Path) -> Skill | None:
    """Parse a SKILL.md file into a Skill object.

    Follows lenient validation: warns on issues but loads anyway
    unless description is missing or YAML is completely unparseable.
    """
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8")

    # Extract YAML frontmatter
    frontmatter: dict[str, Any] = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
            except yaml.YAMLError:
                # Lenient: try to load without frontmatter
                pass
            body = parts[2].strip()

    name = frontmatter.get("name", path.parent.name)
    description = frontmatter.get("description", "")

    if not description:
        # Try to extract from first paragraph of body
        for line in body.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                description = line[:200]
                break

    if not description:
        return None  # Cannot load without a description

    # Discover associated resource files
    resources: list[str] = []
    skill_dir = path.parent
    for ext in ("*.py", "*.sh", "*.js", "*.ts", "*.json", "*.yaml", "*.yml"):
        resources.extend(str(f) for f in skill_dir.glob(ext))

    return Skill(
        name=name,
        description=description,
        body=body,
        source=str(path),
        license=frontmatter.get("license", ""),
        compatibility=frontmatter.get("compatibility", []),
        allowed_tools=frontmatter.get("allowed-tools", []),
        metadata=frontmatter.get("metadata", {}),
        resources=resources,
    )
