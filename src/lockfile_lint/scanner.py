"""Lockfile discovery and parsing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class PackageEntry:
    name: str
    version: str
    resolved: str = ""
    integrity: str = ""
    registry: str = ""
    dependencies: dict[str, str] = field(default_factory=dict)
    optional_dependencies: dict[str, str] = field(default_factory=dict)
    scripts: dict[str, str] = field(default_factory=dict)


@dataclass
class ParsedLockfile:
    path: Path
    format: str  # "npm", "pnpm", "yarn"
    packages: list[PackageEntry] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


class Scanner:
    """Discovers and parses lockfiles in a project directory."""

    LOCKFILE_NAMES = [
        "package-lock.json",
        "npm-shrinkwrap.json",
        "pnpm-lock.yaml",
        "yarn.lock",
    ]

    def __init__(self, project_path: Path):
        self.project_path = project_path

    def discover_lockfiles(self) -> list[Path]:
        found = []
        for name in self.LOCKFILE_NAMES:
            candidate = self.project_path / name
            if candidate.is_file():
                found.append(candidate)
        return found

    def parse_lockfile(self, path: Path) -> ParsedLockfile | None:
        name = path.name
        try:
            if name in ("package-lock.json", "npm-shrinkwrap.json"):
                return self._parse_npm(path)
            elif name == "pnpm-lock.yaml":
                return self._parse_pnpm(path)
            elif name == "yarn.lock":
                return self._parse_yarn(path)
        except Exception:
            return None
        return None

    def _parse_npm(self, path: Path) -> ParsedLockfile:
        data = json.loads(path.read_text(encoding="utf-8"))
        packages: list[PackageEntry] = []

        # npm v2/v3 format: "packages" key with "" prefix paths
        pkgs = data.get("packages", {})
        for pkg_path, info in pkgs.items():
            if not pkg_path:  # root package
                continue
            name = info.get("name", pkg_path.split("node_modules/")[-1])
            entry = PackageEntry(
                name=name,
                version=info.get("version", ""),
                resolved=info.get("resolved", ""),
                integrity=info.get("integrity", ""),
                dependencies=info.get("dependencies", {}),
                optional_dependencies=info.get("optionalDependencies", {}),
            )
            if entry.resolved:
                entry.registry = self._extract_registry(entry.resolved)
            packages.append(entry)

        # npm v1 fallback: "dependencies" key
        if not packages:
            deps = data.get("dependencies", {})
            for name, info in deps.items():
                entry = PackageEntry(
                    name=name,
                    version=info.get("version", ""),
                    resolved=info.get("resolved", ""),
                    integrity=info.get("integrity", ""),
                )
                if entry.resolved:
                    entry.registry = self._extract_registry(entry.resolved)
                packages.append(entry)

        return ParsedLockfile(path=path, format="npm", packages=packages, raw=data)

    def _parse_pnpm(self, path: Path) -> ParsedLockfile:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        packages: list[PackageEntry] = []

        pkgs = data.get("packages", {})
        for pkg_id, info in pkgs.items():
            # pnpm format: /@scope/name@version or /name@version
            match = re.match(r"/?(@?[^@]+)@(.+)", pkg_id)
            if not match:
                continue
            name, version = match.groups()
            resolution = info.get("resolution", {})
            entry = PackageEntry(
                name=name,
                version=version,
                resolved=resolution.get("tarball", ""),
                integrity=resolution.get("integrity", ""),
                dependencies=info.get("dependencies", {}),
                optional_dependencies=info.get("optionalDependencies", {}),
            )
            if entry.resolved:
                entry.registry = self._extract_registry(entry.resolved)
            packages.append(entry)

        return ParsedLockfile(path=path, format="pnpm", packages=packages, raw=data)

    def _parse_yarn(self, path: Path) -> ParsedLockfile:
        content = path.read_text(encoding="utf-8")
        packages: list[PackageEntry] = []

        # Simple yarn.lock parser (v1 format)
        current_name = ""
        current_version = ""
        current_resolved = ""
        current_integrity = ""
        in_block = False

        for line in content.splitlines():
            if not line.startswith(" ") and line.strip() and not line.startswith("#"):
                # Flush previous
                if current_name:
                    entry = PackageEntry(
                        name=current_name,
                        version=current_version,
                        resolved=current_resolved,
                        integrity=current_integrity,
                    )
                    if entry.resolved:
                        entry.registry = self._extract_registry(entry.resolved)
                    packages.append(entry)

                # Parse new block header
                header = line.rstrip(":")
                # Extract package name from yarn header like "@scope/pkg@^1.0.0"
                match = re.match(r'"?(@?[^@"]+)@', header)
                if match:
                    current_name = match.group(1)
                else:
                    current_name = ""
                current_version = ""
                current_resolved = ""
                current_integrity = ""
                in_block = True
            elif in_block and line.startswith("  "):
                stripped = line.strip()
                if stripped.startswith("version "):
                    current_version = stripped.split('"')[1] if '"' in stripped else ""
                elif stripped.startswith("resolved "):
                    current_resolved = stripped.split('"')[1] if '"' in stripped else ""
                elif stripped.startswith("integrity "):
                    current_integrity = stripped.split(" ", 1)[1].strip().strip('"')

        # Flush last block
        if current_name:
            entry = PackageEntry(
                name=current_name,
                version=current_version,
                resolved=current_resolved,
                integrity=current_integrity,
            )
            if entry.resolved:
                entry.registry = self._extract_registry(entry.resolved)
            packages.append(entry)

        return ParsedLockfile(path=path, format="yarn", packages=packages, raw={})

    @staticmethod
    def _extract_registry(resolved_url: str) -> str:
        """Extract registry hostname from a resolved URL."""
        if not resolved_url:
            return ""
        match = re.match(r"https?://([^/]+)", resolved_url)
        return match.group(1) if match else ""
