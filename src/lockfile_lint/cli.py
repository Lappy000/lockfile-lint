"""CLI entry point for lockfile-lint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lockfile_lint import __version__
from lockfile_lint.scanner import Scanner
from lockfile_lint.rules import RuleEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lockfile-lint",
        description="Fast lockfile security scanner for npm/pnpm/yarn projects",
    )
    parser.add_argument("path", nargs="?", default=".", help="Project directory to scan")
    parser.add_argument("--json", action="store_true", dest="json_output", help="JSON output")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument(
        "--rules",
        nargs="*",
        default=None,
        help="Specific rules to run (default: all)",
    )
    parser.add_argument(
        "--ignore-packages",
        nargs="*",
        default=[],
        help="Package names to ignore",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    project_path = Path(args.path).resolve()
    if not project_path.is_dir():
        print(f"error: {project_path} is not a directory", file=sys.stderr)
        return 1

    scanner = Scanner(project_path)
    lockfiles = scanner.discover_lockfiles()

    if not lockfiles:
        print(f"no lockfiles found in {project_path}", file=sys.stderr)
        return 0

    engine = RuleEngine(
        enabled_rules=args.rules,
        ignore_packages=set(args.ignore_packages),
    )

    all_findings: list[dict] = []
    for lockfile in lockfiles:
        parsed = scanner.parse_lockfile(lockfile)
        if parsed is None:
            continue
        findings = engine.run(parsed)
        all_findings.extend(findings)

    if args.json_output:
        print(json.dumps({"findings": all_findings, "scanned": len(lockfiles)}, indent=2))
    else:
        _print_findings(all_findings, lockfiles)

    has_critical = any(f["severity"] == "critical" for f in all_findings)
    has_warning = any(f["severity"] == "warning" for f in all_findings)

    if has_critical:
        return 2
    if has_warning and args.strict:
        return 1
    return 0


def _print_findings(findings: list[dict], lockfiles: list[Path]) -> None:
    print(f"scanned {len(lockfiles)} lockfile(s)\n")

    if not findings:
        print("\033[32m✓ no issues found\033[0m")
        return

    critical = [f for f in findings if f["severity"] == "critical"]
    warnings = [f for f in findings if f["severity"] == "warning"]
    info = [f for f in findings if f["severity"] == "info"]

    if critical:
        print(f"\033[31m✗ {len(critical)} critical issue(s)\033[0m")
        for f in critical:
            print(f"  [{f['rule']}] {f['message']}")
            if f.get("package"):
                print(f"    package: {f['package']}")
            if f.get("details"):
                print(f"    details: {f['details']}")
        print()

    if warnings:
        print(f"\033[33m! {len(warnings)} warning(s)\033[0m")
        for f in warnings:
            print(f"  [{f['rule']}] {f['message']}")
            if f.get("package"):
                print(f"    package: {f['package']}")
        print()

    if info:
        print(f"\033[36mi {len(info)} info\033[0m")
        for f in info:
            print(f"  [{f['rule']}] {f['message']}")
        print()


if __name__ == "__main__":
    sys.exit(main())
