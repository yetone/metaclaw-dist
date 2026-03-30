"""Skill creator - auto-create and template skills for self-improvement."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent


SKILL_TEMPLATE = """\
---
name: {name}
description: {description}
license: MIT
compatibility:
  - metaclaw
allowed-tools:
  - ReadFile
  - WriteFile
  - EditFile
  - Bash
metadata:
  version: "0.1.0"
  author: MetaClaw
---

# {title}

{description}

## Instructions

<!-- Add your skill instructions here -->
<!-- The agent will follow these instructions when this skill is activated -->

## Examples

<!-- Add example interactions or workflows here -->
"""


def create_skill_template(
    name: str,
    description: str = "",
    target_dir: str | None = None,
) -> str:
    """Create a new skill template directory with SKILL.md.

    Returns the path to the created skill directory.
    """
    if not description:
        description = f"A skill for {name}"

    if target_dir:
        base = Path(target_dir)
    else:
        # Default to project-level skills directory
        base = Path.cwd() / ".metaclaw" / "skills"

    skill_dir = base / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    title = name.replace("-", " ").replace("_", " ").title()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        SKILL_TEMPLATE.format(
            name=name,
            description=description,
            title=title,
        )
    )

    return str(skill_dir)


def create_skill_from_experience(
    name: str,
    description: str,
    instructions: str,
    examples: str = "",
) -> str:
    """Create a skill from agent experience (self-improvement).

    Called when the agent successfully completes a novel task
    and wants to capture the workflow as a reusable skill.
    """
    base = Path.home() / ".metaclaw" / "skills"
    skill_dir = base / name
    skill_dir.mkdir(parents=True, exist_ok=True)

    title = name.replace("-", " ").replace("_", " ").title()

    content = dedent(f"""\
    ---
    name: {name}
    description: {description}
    license: MIT
    compatibility:
      - metaclaw
    allowed-tools:
      - ReadFile
      - WriteFile
      - EditFile
      - Bash
    metadata:
      version: "0.1.0"
      author: MetaClaw (auto-generated)
      auto_created: true
    ---

    # {title}

    {description}

    ## Instructions

    {instructions}
    """)

    if examples:
        content += f"\n## Examples\n\n{examples}\n"

    (skill_dir / "SKILL.md").write_text(content)

    return str(skill_dir)
