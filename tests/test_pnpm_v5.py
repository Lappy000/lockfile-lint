"""Regressions for legacy and current pnpm package identifiers."""

import json

import pytest
import yaml

from lockfile_lint.cli import main
from lockfile_lint.scanner import Scanner


@pytest.mark.parametrize(
    ("lockfile_version", "package_name", "package_id"),
    [
        (5.4, "fixture-dep", "/fixture-dep/1.2.3"),
        (5.4, "@fixture/dep", "/@fixture/dep/1.2.3"),
        (6.0, "fixture-dep", "/fixture-dep@1.2.3"),
        (6.0, "@fixture/dep", "/@fixture/dep@1.2.3"),
        ("9.0", "fixture-dep", "fixture-dep@1.2.3"),
        ("9.0", "@fixture/dep", "@fixture/dep@1.2.3"),
    ],
)
def test_pnpm_package_identifiers_are_scanned(
    tmp_path, capsys, lockfile_version, package_name, package_id
):
    lockfile = tmp_path / "pnpm-lock.yaml"
    lockfile.write_text(
        yaml.safe_dump(
            {
                "lockfileVersion": lockfile_version,
                "packages": {
                    package_id: {
                        "resolution": {
                            "tarball": "http://registry.example.invalid/package.tgz",
                            "integrity": "sha512-fixture",
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    parsed = Scanner(tmp_path).parse_lockfile(lockfile)
    assert parsed is not None
    assert [(entry.name, entry.version) for entry in parsed.packages] == [(package_name, "1.2.3")]
    assert main([str(tmp_path), "--json", "--rules", "http-registry"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["scanned"] == 1
    assert report["errors"] == []
    assert len(report["findings"]) == 1
    assert report["findings"][0]["package"] == package_name
    assert report["findings"][0]["rule"] == "http-registry"
