# lockfile-lint

[![PyPI](https://img.shields.io/pypi/v/lockfile-lint)](https://pypi.org/project/lockfile-lint/)
[![Python](https://img.shields.io/pypi/pyversions/lockfile-lint)](https://pypi.org/project/lockfile-lint/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Fast lockfile security scanner. Detects supply-chain attacks, malicious packages, and integrity violations in npm/pnpm/yarn lockfiles.

Built in response to the [TanStack supply-chain attack (CVE-2026-45321)](https://nvd.nist.gov/vuln/detail/CVE-2026-45321) and similar incidents.

## Install

```bash
pip install lockfile-lint
```

## Usage

```bash
# Scan current directory
lockfile-lint .

# Scan specific project
lockfile-lint /path/to/project

# JSON output for CI pipelines
lockfile-lint . --json

# Strict mode (warnings = exit code 1)
lockfile-lint . --strict

# Run specific rules only
lockfile-lint . --rules malicious-package untrusted-registry

# Ignore known-safe packages
lockfile-lint . --ignore-packages @company/internal-pkg
```

## Rules

| Rule | Severity | Description |
|------|----------|-------------|
| `malicious-package` | critical | Known malicious packages/versions (CVE-2026-45321, typosquats) |
| `untrusted-registry` | warning | Packages resolved from non-standard registries |
| `missing-integrity` | warning | Packages without integrity (SRI) hashes |
| `suspicious-url` | critical | Resolved URLs pointing to ngrok, localhost, file:// etc. |
| `git-dependency` | warning | Git dependencies vulnerable to repo transfer attacks |
| `http-registry` | critical | Plain HTTP resolution (MITM risk) |
| `mixed-registries` | info | Packages from multiple different registries |
| `empty-version` | warning | Packages without pinned versions |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Clean / warnings only (without `--strict`) |
| 1 | Warnings found (with `--strict`) |
| 2 | Critical issues found |

## CI Integration

```yaml
# GitHub Actions
- name: Lockfile security scan
  run: |
    pip install lockfile-lint
    lockfile-lint . --strict --json > lockfile-report.json
```

## Supported Lockfiles

- `package-lock.json` (npm v1, v2, v3)
- `npm-shrinkwrap.json`
- `pnpm-lock.yaml`
- `yarn.lock` (v1)

## Malicious Package Database

The scanner includes a curated database of known-malicious packages:

- **CVE-2026-45321** — TanStack npm supply-chain attack (42 packages, 84 versions)
- **Typosquatting** — ~30 commonly typosquatted package names
- Updates via `pip install --upgrade lockfile-lint`

## License

MIT
