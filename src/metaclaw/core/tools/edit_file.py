"""EditFile tool - Edit files with exact match and fuzzy match fallback."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from metaclaw.core.tools.base import BaseTool


class EditFileTool(BaseTool):
    """Edit a file by replacing old_string with new_string.

    Supports exact match first, then falls back to fuzzy matching
    using diff-match-patch when exact match fails.
    """

    def __init__(self, fuzzy_threshold: float = 0.6):
        self._fuzzy_threshold = fuzzy_threshold

    @property
    def name(self) -> str:
        return "EditFile"

    @property
    def description(self) -> str:
        return (
            "Edit a file by replacing old_string with new_string. "
            "Attempts exact match first. If exact match fails, falls back to "
            "fuzzy matching to handle minor differences (whitespace, typos). "
            "The old_string must be unique in the file."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit.",
                },
                "old_string": {
                    "type": "string",
                    "description": "The text to find and replace. Must be unique in the file.",
                },
                "new_string": {
                    "type": "string",
                    "description": "The replacement text.",
                },
            },
            "required": ["file_path", "old_string", "new_string"],
        }

    async def execute(self, **kwargs: Any) -> str:
        file_path = kwargs["file_path"]
        old_string = kwargs["old_string"]
        new_string = kwargs["new_string"]

        path = Path(file_path).expanduser()

        if not path.exists():
            return f"Error: File not found: {file_path}"
        if not path.is_file():
            return f"Error: Not a file: {file_path}"

        try:
            original = path.read_text(encoding="utf-8")
        except (PermissionError, UnicodeDecodeError) as e:
            return f"Error reading file: {e}"

        if old_string == new_string:
            return "Error: old_string and new_string are identical."

        # Try exact match first
        result = self._try_exact_match(original, old_string, new_string)
        if result is not None:
            return self._apply_edit(path, original, result, file_path)

        # Fall back to fuzzy match
        result = self._try_fuzzy_match(original, old_string, new_string)
        if result is not None:
            return self._apply_edit(
                path, original, result, file_path, fuzzy=True
            )

        # Fall back to diff-match-patch
        result = self._try_dmp_match(original, old_string, new_string)
        if result is not None:
            return self._apply_edit(
                path, original, result, file_path, fuzzy=True
            )

        # Nothing worked - show closest match to help the agent
        closest = self._find_closest_match(original, old_string)
        msg = f"Error: Could not find a match for old_string in {file_path}."
        if closest:
            msg += f"\n\nClosest match found:\n```\n{closest}\n```"
        return msg

    def _try_exact_match(
        self, content: str, old_string: str, new_string: str
    ) -> str | None:
        """Try exact string replacement. Returns new content or None."""
        count = content.count(old_string)
        if count == 0:
            return None
        if count > 1:
            # Still return None to let fuzzy match handle it with context
            # The fuzzy match will also check uniqueness
            return None
        return content.replace(old_string, new_string, 1)

    def _try_fuzzy_match(
        self, content: str, old_string: str, new_string: str
    ) -> str | None:
        """Try fuzzy matching using difflib SequenceMatcher.

        Splits the file into sliding windows of old_string's line count
        and finds the best match above threshold.
        """
        old_lines = old_string.splitlines(keepends=True)
        content_lines = content.splitlines(keepends=True)
        window_size = len(old_lines)

        if window_size == 0 or len(content_lines) == 0:
            return None

        best_ratio = 0.0
        best_start = -1
        matches: list[tuple[float, int]] = []

        for start in range(len(content_lines) - window_size + 1):
            window = content_lines[start : start + window_size]
            ratio = difflib.SequenceMatcher(
                None, old_lines, window
            ).ratio()

            if ratio > best_ratio:
                best_ratio = ratio
                best_start = start

            if ratio >= self._fuzzy_threshold:
                matches.append((ratio, start))

        if best_ratio < self._fuzzy_threshold:
            return None

        # Check for ambiguity - multiple good matches
        good_matches = [m for m in matches if m[0] >= self._fuzzy_threshold]
        if len(good_matches) > 1:
            # Check if there's a clear winner (>0.05 ratio difference)
            good_matches.sort(reverse=True)
            if good_matches[0][0] - good_matches[1][0] < 0.05:
                return None  # Ambiguous, let the agent provide more context

        # Replace the best matching window
        new_lines = new_string.splitlines(keepends=True)
        # Ensure trailing newline consistency
        if content_lines[best_start : best_start + window_size]:
            last_orig = content_lines[best_start + window_size - 1]
            if last_orig.endswith("\n") and new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] += "\n"

        result_lines = (
            content_lines[:best_start]
            + new_lines
            + content_lines[best_start + window_size :]
        )
        return "".join(result_lines)

    def _try_dmp_match(
        self, content: str, old_string: str, new_string: str
    ) -> str | None:
        """Try diff-match-patch for robust fuzzy matching."""
        try:
            from diff_match_patch import diff_match_patch

            dmp = diff_match_patch()
            dmp.Match_Threshold = self._fuzzy_threshold
            dmp.Match_Distance = 10000
            dmp.Patch_DeleteThreshold = 0.6

            # Create a diff between old and new
            diffs = dmp.diff_main(old_string, new_string)
            dmp.diff_cleanupSemantic(diffs)

            # Create patches from the diff
            patches = dmp.patch_make(old_string, diffs)
            if not patches:
                return None

            # Apply patches to the content
            result, success = dmp.patch_apply(patches, content)

            # Check that all patches succeeded
            if all(success):
                return result

            return None
        except ImportError:
            return None

    def _find_closest_match(self, content: str, old_string: str) -> str | None:
        """Find the closest matching section in the file for error reporting."""
        old_lines = old_string.splitlines(keepends=True)
        content_lines = content.splitlines(keepends=True)
        window_size = len(old_lines)

        if window_size == 0 or len(content_lines) == 0:
            return None

        best_ratio = 0.0
        best_window = None

        for start in range(len(content_lines) - window_size + 1):
            window = content_lines[start : start + window_size]
            ratio = difflib.SequenceMatcher(None, old_lines, window).ratio()

            if ratio > best_ratio:
                best_ratio = ratio
                best_window = window

        if best_window and best_ratio > 0.3:
            return "".join(best_window).rstrip()
        return None

    def _apply_edit(
        self,
        path: Path,
        original: str,
        new_content: str,
        file_path: str,
        fuzzy: bool = False,
    ) -> str:
        """Write the edited content and return a diff summary."""
        try:
            path.write_text(new_content, encoding="utf-8")
        except (PermissionError, OSError) as e:
            return f"Error writing file: {e}"

        # Generate unified diff for verification
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            n=3,
        )
        diff_text = "".join(diff)

        method = "fuzzy match" if fuzzy else "exact match"
        return f"Successfully edited {file_path} ({method}).\n\nDiff:\n```diff\n{diff_text}```"
