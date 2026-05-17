"""Shared test fixtures."""
import pytest
from pathlib import Path


@pytest.fixture
def sample_dir(tmp_path):
    """Provide a temp directory for test lockfiles."""
    return tmp_path


@pytest.fixture
def npm_lockfile(tmp_path):
    """Create a minimal valid npm lockfile."""
    import json
    data = {
        "name": "test",
        "version": "1.0.0",
        "lockfileVersion": 3,
        "packages": {}
    }
    p = tmp_path / "package-lock.json"
    p.write_text(json.dumps(data))
    return p
