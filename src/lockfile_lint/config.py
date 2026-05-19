"""Configuration file support for lockfile-lint."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class LintConfig:
    """Configuration loaded from .lockfile-lint.json or pyproject.toml."""
    rules: list[str] | None = None
    ignore_packages: set[str] = field(default_factory=set)
    strict: bool = False
    trusted_registries: set[str] = field(default_factory=set)

    @classmethod
    def from_file(cls, path: Path) -> "LintConfig":
        """Load config from a JSON file."""
        data = json.loads(path.read_text())
        return cls(
            rules=data.get("rules"),
            ignore_packages=set(data.get("ignore_packages", [])),
            strict=data.get("strict", False),
            trusted_registries=set(data.get("trusted_registries", [])),
        )

    @classmethod
    def discover(cls, project_path: Path) -> "LintConfig | None":
        """Auto-discover config file in project."""
        candidates = [
            project_path / ".lockfile-lint.json",
            project_path / ".lockfile-lintrc",
        ]
        for c in candidates:
            if c.is_file():
                return cls.from_file(c)
        # Try pyproject.toml
        pyproject = project_path / "pyproject.toml"
        if pyproject.is_file():
            return cls._from_pyproject(pyproject)
        return None

    @classmethod
    def _from_pyproject(cls, path: Path) -> "LintConfig | None":
        """Extract config from [tool.lockfile-lint] in pyproject.toml."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return None
        data = tomllib.loads(path.read_text())
        section = data.get("tool", {}).get("lockfile-lint")
        if not section:
            return None
        return cls(
            rules=section.get("rules"),
            ignore_packages=set(section.get("ignore_packages", [])),
            strict=section.get("strict", False),
            trusted_registries=set(section.get("trusted_registries", [])),
        )
