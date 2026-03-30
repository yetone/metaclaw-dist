"""Shared test fixtures for MetaClaw."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from metaclaw.config import MetaClawConfig, reset_config


@pytest.fixture(autouse=True)
def _reset_global_config():
    """Reset global config between tests."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory for test file operations."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def default_config():
    """Provide a default MetaClawConfig for testing."""
    return MetaClawConfig()
