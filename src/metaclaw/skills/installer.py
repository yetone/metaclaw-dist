"""Skill installer - install skills from URLs, registry, or local paths."""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from metaclaw.skills.parser import Skill, parse_skill


@dataclass
class InstallResult:
    """Result of a skill installation attempt."""

    success: bool
    name: str = ""
    path: str = ""
    error: str = ""


def _get_install_dir() -> Path:
    """Get the user-level skill installation directory."""
    install_dir = Path.home() / ".metaclaw" / "skills"
    install_dir.mkdir(parents=True, exist_ok=True)
    return install_dir


def install_skill(source: str) -> InstallResult:
    """Install a skill from a URL, registry name, or local path.

    Supports:
    - Local path: /path/to/skill or ./my-skill
    - Git URL: https://github.com/user/repo/tree/main/my-skill
    - Registry name: skill-name (searches agentskills.io)
    """
    source_path = Path(source).expanduser()

    # Case 1: Local path
    if source_path.exists():
        return _install_from_local(source_path)

    # Case 2: URL
    if source.startswith("http://") or source.startswith("https://"):
        return _install_from_url(source)

    # Case 3: Registry name (TODO: implement registry search)
    return _install_from_registry(source)


def _install_from_local(source_path: Path) -> InstallResult:
    """Install a skill from a local directory."""
    skill_md = source_path / "SKILL.md"
    if not skill_md.exists():
        # Check if source is a SKILL.md file itself
        if source_path.name == "SKILL.md":
            skill_md = source_path
            source_path = source_path.parent
        else:
            return InstallResult(
                success=False,
                error=f"No SKILL.md found in {source_path}",
            )

    # Parse to get skill name
    skill = parse_skill(skill_md)
    if skill is None:
        return InstallResult(
            success=False,
            error=f"Failed to parse SKILL.md in {source_path}",
        )

    # Copy to install directory
    install_dir = _get_install_dir()
    target = install_dir / skill.name

    if target.exists():
        shutil.rmtree(target)

    shutil.copytree(source_path, target)

    return InstallResult(
        success=True,
        name=skill.name,
        path=str(target),
    )


def _install_from_url(url: str) -> InstallResult:
    """Install a skill from a git URL."""
    try:
        import httpx
    except ImportError:
        return InstallResult(
            success=False,
            error="httpx is required for URL installation",
        )

    # Handle GitHub URLs
    if "github.com" in url:
        return _install_from_github(url)

    return InstallResult(
        success=False,
        error=f"Unsupported URL format: {url}. Use a GitHub URL.",
    )


def _install_from_github(url: str) -> InstallResult:
    """Install a skill from a GitHub repository URL."""
    import subprocess
    import tempfile

    # Convert GitHub tree URL to raw content URL
    # https://github.com/user/repo/tree/main/path -> clone and extract
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Parse GitHub URL
            parts = url.replace("https://github.com/", "").split("/")
            if len(parts) < 2:
                return InstallResult(success=False, error=f"Invalid GitHub URL: {url}")

            user, repo = parts[0], parts[1]
            clone_url = f"https://github.com/{user}/{repo}.git"

            # Determine subdirectory if any
            subdir = ""
            if "tree" in parts:
                tree_idx = parts.index("tree")
                if tree_idx + 2 < len(parts):
                    subdir = "/".join(parts[tree_idx + 2 :])

            # Shallow clone
            clone_dir = Path(tmp_dir) / "repo"
            result = subprocess.run(
                ["git", "clone", "--depth", "1", clone_url, str(clone_dir)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                return InstallResult(
                    success=False,
                    error=f"Git clone failed: {result.stderr}",
                )

            source_dir = clone_dir / subdir if subdir else clone_dir
            return _install_from_local(source_dir)

    except subprocess.TimeoutExpired:
        return InstallResult(success=False, error="Git clone timed out")
    except Exception as e:
        return InstallResult(success=False, error=str(e))


def _install_from_registry(name: str) -> InstallResult:
    """Install a skill by name from the agentskills.io registry."""
    # TODO: Implement registry search when agentskills.io API is available
    return InstallResult(
        success=False,
        error=(
            f"Skill '{name}' not found locally. "
            "Registry search is not yet implemented. "
            "Please provide a URL or local path."
        ),
    )


def uninstall_skill(name: str) -> bool:
    """Uninstall a skill by name."""
    install_dir = _get_install_dir()
    target = install_dir / name
    if target.exists():
        shutil.rmtree(target)
        return True
    return False
