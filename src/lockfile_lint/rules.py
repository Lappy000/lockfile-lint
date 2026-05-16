"""Security rules engine for lockfile analysis."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from lockfile_lint.scanner import PackageEntry, ParsedLockfile

# Known malicious packages and patterns (curated list)
KNOWN_MALICIOUS: dict[str, set[str]] = {
    # TanStack supply-chain attack (CVE-2026-45321)
    "@tanstack/config": {"0.15.1", "0.15.2"},
    "@tanstack/router": {"1.120.2", "1.120.3"},
    "@tanstack/react-router": {"1.120.2", "1.120.3"},
    "@tanstack/start": {"1.120.2", "1.120.3"},
    "@tanstack/react-start": {"1.120.2", "1.120.3"},
    "@tanstack/query-core": {"5.72.1", "5.72.2"},
    "@tanstack/react-query": {"5.72.1", "5.72.2"},
    "@tanstack/vue-query": {"5.72.1", "5.72.2"},
    "@tanstack/solid-query": {"5.72.1", "5.72.2"},
    "@tanstack/svelte-query": {"5.72.1", "5.72.2"},
    "@tanstack/angular-query": {"5.72.1", "5.72.2"},
    "@tanstack/form-core": {"1.3.1", "1.3.2"},
    "@tanstack/react-form": {"1.3.1", "1.3.2"},
    "@tanstack/table-core": {"8.22.1", "8.22.2"},
    "@tanstack/react-table": {"8.22.1", "8.22.2"},
    "@tanstack/vue-table": {"8.22.1", "8.22.2"},
    "@tanstack/virtual-core": {"3.12.1", "3.12.2"},
    "@tanstack/react-virtual": {"3.12.1", "3.12.2"},
    # Commonly typosquatted packages
    "crossenv": {"*"},
    "cross-env.js": {"*"},
    "d3.js": {"*"},
    "fabric-js": {"*"},
    "ffmepg": {"*"},
    "gruntcli": {"*"},
    "http-proxy.js": {"*"},
    "jquery.js": {"*"},
    "mariadb": {"*"},
    "mongose": {"*"},
    "mssql.js": {"*"},
    "mssql-node": {"*"},
    "mysqljs": {"*"},
    "node-hierarchicalsoftmax": {"*"},
    "nodecaffe": {"*"},
    "nodefabric": {"*"},
    "nodemailer-js": {"*"},
    "nodesass": {"*"},
    "nodesqlite": {"*"},
    "node-tkinter": {"*"},
    "opencv.js": {"*"},
    "openssl.js": {"*"},
    "proxy.js": {"*"},
    "shadowsock": {"*"},
    "smb": {"*"},
    "sqlite.js": {"*"},
    "sqlserver": {"*"},
    "tkinter": {"*"},
}

# Suspicious URL patterns in resolved fields
SUSPICIOUS_URL_PATTERNS: list[re.Pattern] = [
    re.compile(r"github\.com/[^/]+/[^/]+#[a-f0-9]{40}"),  # git dep pinned to hash
    re.compile(r"https?://[^/]*\.ngrok\.(io|app)"),
    re.compile(r"https?://[^/]*\.serveo\.net"),
    re.compile(r"https?://[^/]*\.loca\.lt"),
    re.compile(r"https?://localhost[:/]"),
    re.compile(r"https?://127\.0\.0\.1[:/]"),
    re.compile(r"https?://0\.0\.0\.0[:/]"),
    re.compile(r"file://"),
]

# Trusted registries
TRUSTED_REGISTRIES: set[str] = {
    "registry.npmjs.org",
    "registry.yarnpkg.com",
    "npm.pkg.github.com",
    "registry.npmmirror.com",
}

# Packages that should never have install scripts
SCRIPT_SUSPICIOUS_PREFIXES: list[str] = [
    "curl ",
    "wget ",
    "powershell ",
    "bash -c",
    "/bin/sh -c",
    "node -e",
    "python -c",
]


@dataclass
class Finding:
    rule: str
    severity: str  # critical, warning, info
    message: str
    package: str = ""
    version: str = ""
    details: str = ""

    def to_dict(self) -> dict:
        d = {"rule": self.rule, "severity": self.severity, "message": self.message}
        if self.package:
            d["package"] = self.package
        if self.version:
            d["version"] = self.version
        if self.details:
            d["details"] = self.details
        return d


class RuleEngine:
    """Runs security rules against parsed lockfile data."""

    def __init__(
        self,
        enabled_rules: list[str] | None = None,
        ignore_packages: set[str] | None = None,
    ):
        self.ignore_packages = ignore_packages or set()
        self._rules: list[tuple[str, Callable]] = [
            ("malicious-package", self._rule_malicious_package),
            ("untrusted-registry", self._rule_untrusted_registry),
            ("missing-integrity", self._rule_missing_integrity),
            ("suspicious-url", self._rule_suspicious_url),
            ("git-dependency", self._rule_git_dependency),
            ("http-registry", self._rule_http_registry),
            ("mixed-registries", self._rule_mixed_registries),
            ("empty-version", self._rule_empty_version),
        ]
        if enabled_rules:
            self._rules = [(n, fn) for n, fn in self._rules if n in enabled_rules]

    def run(self, lockfile: ParsedLockfile) -> list[dict]:
        findings: list[Finding] = []
        for rule_name, rule_fn in self._rules:
            results = rule_fn(lockfile)
            findings.extend(results)
        return [f.to_dict() for f in findings if f.package not in self.ignore_packages]

    def _rule_malicious_package(self, lockfile: ParsedLockfile) -> list[Finding]:
        """Detect known malicious packages and versions."""
        findings = []
        for pkg in lockfile.packages:
            if pkg.name in KNOWN_MALICIOUS:
                bad_versions = KNOWN_MALICIOUS[pkg.name]
                if "*" in bad_versions or pkg.version in bad_versions:
                    findings.append(Finding(
                        rule="malicious-package",
                        severity="critical",
                        message=f"known malicious package detected: {pkg.name}@{pkg.version}",
                        package=pkg.name,
                        version=pkg.version,
                        details="this package/version is in the known-malicious database",
                    ))
        return findings

    def _rule_untrusted_registry(self, lockfile: ParsedLockfile) -> list[Finding]:
        """Flag packages resolved from non-standard registries."""
        findings = []
        for pkg in lockfile.packages:
            if pkg.registry and pkg.registry not in TRUSTED_REGISTRIES:
                if not pkg.resolved.startswith("https://github.com"):
                    findings.append(Finding(
                        rule="untrusted-registry",
                        severity="warning",
                        message=f"resolved from untrusted registry: {pkg.registry}",
                        package=pkg.name,
                        version=pkg.version,
                        details=pkg.resolved,
                    ))
        return findings

    def _rule_missing_integrity(self, lockfile: ParsedLockfile) -> list[Finding]:
        """Detect packages without integrity hashes."""
        missing = [pkg for pkg in lockfile.packages if not pkg.integrity and pkg.resolved]
        if len(missing) > 10:
            return [Finding(
                rule="missing-integrity",
                severity="warning",
                message=f"{len(missing)} packages lack integrity hashes",
                details="run `npm audit fix` or regenerate lockfile",
            )]
        findings = []
        for pkg in missing:
            findings.append(Finding(
                rule="missing-integrity",
                severity="warning",
                message="missing integrity hash",
                package=pkg.name,
                version=pkg.version,
            ))
        return findings

    def _rule_suspicious_url(self, lockfile: ParsedLockfile) -> list[Finding]:
        """Detect suspicious URLs in resolved fields."""
        findings = []
        for pkg in lockfile.packages:
            for pattern in SUSPICIOUS_URL_PATTERNS:
                if pattern.search(pkg.resolved):
                    findings.append(Finding(
                        rule="suspicious-url",
                        severity="critical",
                        message=f"suspicious resolved URL pattern",
                        package=pkg.name,
                        version=pkg.version,
                        details=pkg.resolved,
                    ))
                    break
        return findings

    def _rule_git_dependency(self, lockfile: ParsedLockfile) -> list[Finding]:
        """Flag git:// dependencies (potential for hijacking)."""
        findings = []
        for pkg in lockfile.packages:
            if pkg.resolved.startswith("git://") or pkg.resolved.startswith("git+"):
                findings.append(Finding(
                    rule="git-dependency",
                    severity="warning",
                    message="git dependency — vulnerable to repo transfer attacks",
                    package=pkg.name,
                    version=pkg.version,
                    details=pkg.resolved,
                ))
        return findings

    def _rule_http_registry(self, lockfile: ParsedLockfile) -> list[Finding]:
        """Flag packages resolved over plain HTTP (MITM risk)."""
        findings = []
        for pkg in lockfile.packages:
            if pkg.resolved.startswith("http://"):
                findings.append(Finding(
                    rule="http-registry",
                    severity="critical",
                    message="resolved over plain HTTP — MITM risk",
                    package=pkg.name,
                    version=pkg.version,
                    details=pkg.resolved,
                ))
        return findings

    def _rule_mixed_registries(self, lockfile: ParsedLockfile) -> list[Finding]:
        """Detect if packages come from multiple different registries."""
        registries: set[str] = set()
        for pkg in lockfile.packages:
            if pkg.registry:
                registries.add(pkg.registry)

        trusted_found = registries & TRUSTED_REGISTRIES
        untrusted_found = registries - TRUSTED_REGISTRIES
        if trusted_found and untrusted_found:
            return [Finding(
                rule="mixed-registries",
                severity="info",
                message=f"packages from {len(registries)} different registries",
                details=f"registries: {', '.join(sorted(registries))}",
            )]
        return []

    def _rule_empty_version(self, lockfile: ParsedLockfile) -> list[Finding]:
        """Flag packages with empty versions (possible manipulation)."""
        findings = []
        for pkg in lockfile.packages:
            if not pkg.version and pkg.name:
                findings.append(Finding(
                    rule="empty-version",
                    severity="warning",
                    message="package has no version pinned",
                    package=pkg.name,
                ))
        return findings
