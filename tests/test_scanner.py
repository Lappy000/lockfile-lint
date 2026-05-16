"""Tests for lockfile-lint scanner and rules."""

import json
import tempfile
from pathlib import Path

import pytest

from lockfile_lint.scanner import Scanner, ParsedLockfile
from lockfile_lint.rules import RuleEngine, KNOWN_MALICIOUS


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


def make_npm_lockfile(path: Path, packages: dict) -> Path:
    """Helper to create a package-lock.json."""
    lockfile = path / "package-lock.json"
    data = {
        "name": "test-project",
        "version": "1.0.0",
        "lockfileVersion": 3,
        "packages": packages,
    }
    lockfile.write_text(json.dumps(data))
    return lockfile


class TestScanner:
    def test_discover_npm_lockfile(self, tmp_project):
        (tmp_project / "package-lock.json").write_text("{}")
        scanner = Scanner(tmp_project)
        found = scanner.discover_lockfiles()
        assert len(found) == 1
        assert found[0].name == "package-lock.json"

    def test_discover_no_lockfiles(self, tmp_project):
        scanner = Scanner(tmp_project)
        assert scanner.discover_lockfiles() == []

    def test_parse_npm_v3(self, tmp_project):
        make_npm_lockfile(tmp_project, {
            "": {"name": "test", "version": "1.0.0"},
            "node_modules/lodash": {
                "version": "4.17.21",
                "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.17.21.tgz",
                "integrity": "sha512-v2kDE...",
            },
        })
        scanner = Scanner(tmp_project)
        lockfiles = scanner.discover_lockfiles()
        parsed = scanner.parse_lockfile(lockfiles[0])
        assert parsed is not None
        assert parsed.format == "npm"
        assert len(parsed.packages) == 1
        assert parsed.packages[0].name == "lodash"
        assert parsed.packages[0].version == "4.17.21"

    def test_parse_returns_none_on_invalid(self, tmp_project):
        (tmp_project / "package-lock.json").write_text("not json")
        scanner = Scanner(tmp_project)
        lockfiles = scanner.discover_lockfiles()
        result = scanner.parse_lockfile(lockfiles[0])
        assert result is None


class TestRules:
    def test_malicious_package_detected(self, tmp_project):
        make_npm_lockfile(tmp_project, {
            "": {"name": "test", "version": "1.0.0"},
            "node_modules/@tanstack/router": {
                "version": "1.120.2",
                "resolved": "https://registry.npmjs.org/@tanstack/router/-/router-1.120.2.tgz",
                "integrity": "sha512-fake...",
            },
        })
        scanner = Scanner(tmp_project)
        parsed = scanner.parse_lockfile(scanner.discover_lockfiles()[0])
        engine = RuleEngine(enabled_rules=["malicious-package"])
        findings = engine.run(parsed)
        assert len(findings) == 1
        assert findings[0]["severity"] == "critical"
        assert findings[0]["rule"] == "malicious-package"

    def test_clean_lockfile_passes(self, tmp_project):
        make_npm_lockfile(tmp_project, {
            "": {"name": "test", "version": "1.0.0"},
            "node_modules/express": {
                "version": "4.18.2",
                "resolved": "https://registry.npmjs.org/express/-/express-4.18.2.tgz",
                "integrity": "sha512-abc...",
            },
        })
        scanner = Scanner(tmp_project)
        parsed = scanner.parse_lockfile(scanner.discover_lockfiles()[0])
        engine = RuleEngine()
        findings = engine.run(parsed)
        assert len(findings) == 0

    def test_http_registry_flagged(self, tmp_project):
        make_npm_lockfile(tmp_project, {
            "": {"name": "test", "version": "1.0.0"},
            "node_modules/evil": {
                "version": "1.0.0",
                "resolved": "http://evil.com/evil-1.0.0.tgz",
                "integrity": "sha512-xyz...",
            },
        })
        scanner = Scanner(tmp_project)
        parsed = scanner.parse_lockfile(scanner.discover_lockfiles()[0])
        engine = RuleEngine(enabled_rules=["http-registry"])
        findings = engine.run(parsed)
        assert len(findings) == 1
        assert findings[0]["severity"] == "critical"

    def test_ignore_packages(self, tmp_project):
        make_npm_lockfile(tmp_project, {
            "": {"name": "test", "version": "1.0.0"},
            "node_modules/crossenv": {
                "version": "1.0.0",
                "resolved": "https://registry.npmjs.org/crossenv/-/crossenv-1.0.0.tgz",
                "integrity": "sha512-...",
            },
        })
        scanner = Scanner(tmp_project)
        parsed = scanner.parse_lockfile(scanner.discover_lockfiles()[0])
        engine = RuleEngine(ignore_packages={"crossenv"})
        findings = engine.run(parsed)
        assert len(findings) == 0

    def test_suspicious_ngrok_url(self, tmp_project):
        make_npm_lockfile(tmp_project, {
            "": {"name": "test", "version": "1.0.0"},
            "node_modules/backdoor": {
                "version": "1.0.0",
                "resolved": "https://abc123.ngrok.io/backdoor-1.0.0.tgz",
                "integrity": "",
            },
        })
        scanner = Scanner(tmp_project)
        parsed = scanner.parse_lockfile(scanner.discover_lockfiles()[0])
        engine = RuleEngine(enabled_rules=["suspicious-url"])
        findings = engine.run(parsed)
        assert len(findings) == 1
        assert findings[0]["severity"] == "critical"
