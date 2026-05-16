# Changelog

## [0.1.0] - 2026-05-16

### Added
- Initial release
- npm lockfile parser (v1, v2, v3 format support)
- pnpm-lock.yaml parser
- yarn.lock v1 parser
- 8 security rules:
  - malicious-package (CVE-2026-45321 + typosquats database)
  - untrusted-registry
  - missing-integrity
  - suspicious-url
  - git-dependency
  - http-registry
  - mixed-registries
  - empty-version
- CLI with --json, --strict, --rules flags
- Exit code 2 for critical issues, 1 for warnings in strict mode
