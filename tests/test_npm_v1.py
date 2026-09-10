"""Regression coverage for nested npm v1 dependency trees."""

import json

import pytest

from lockfile_lint.cli import main
from lockfile_lint.scanner import Scanner


@pytest.mark.parametrize("filename", ["package-lock.json", "npm-shrinkwrap.json"])
def test_nested_npm_v1_dependencies_reach_security_rules(tmp_path, capsys, filename):
    lockfile = tmp_path / filename
    lockfile.write_text(
        json.dumps(
            {
                "lockfileVersion": 1,
                "dependencies": {
                    "parent": {
                        "version": "1.0.0",
                        "dependencies": {
                            "middle": {
                                "version": "2.0.0",
                                "dependencies": {
                                    "@fixture/leaf": {
                                        "version": "3.0.0",
                                        "resolved": "http://registry.example/leaf-3.0.0.tgz",
                                        "integrity": "sha512-fixture",
                                    }
                                },
                            }
                        },
                    },
                    "@fixture/leaf": {"version": "4.0.0"},
                },
            }
        ),
        encoding="utf-8",
    )

    exit_code = main([str(tmp_path), "--json", "--rules", "http-registry"])
    output = capsys.readouterr()
    assert exit_code == 2
    assert output.err == ""
    report = json.loads(output.out)
    assert report["scanned"] == 1
    assert len(report["findings"]) == 1
    assert report["findings"][0]["rule"] == "http-registry"
    assert report["findings"][0]["package"] == "@fixture/leaf"
    assert report["findings"][0]["version"] == "3.0.0"

    parsed = Scanner(tmp_path).parse_lockfile(lockfile)
    assert parsed is not None
    assert [(pkg.name, pkg.version) for pkg in parsed.packages] == [
        ("parent", "1.0.0"),
        ("middle", "2.0.0"),
        ("@fixture/leaf", "3.0.0"),
        ("@fixture/leaf", "4.0.0"),
    ]
    nested = parsed.packages[2]
    assert nested.resolved == "http://registry.example/leaf-3.0.0.tgz"
    assert nested.registry == "registry.example"
    assert nested.integrity == "sha512-fixture"


@pytest.mark.parametrize("lockfile_version", [2, 3])
def test_npm_packages_table_is_not_duplicated_by_legacy_tree(tmp_path, lockfile_version):
    lockfile = tmp_path / "package-lock.json"
    lockfile.write_text(
        json.dumps(
            {
                "lockfileVersion": lockfile_version,
                "packages": {
                    "": {"name": "root", "version": "1.0.0"},
                    "node_modules/parent": {"version": "1.0.0"},
                    "node_modules/parent/node_modules/leaf": {"version": "2.0.0"},
                },
                "dependencies": {
                    "parent": {
                        "version": "1.0.0",
                        "dependencies": {"leaf": {"version": "2.0.0"}},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    parsed = Scanner(tmp_path).parse_lockfile(lockfile)

    assert parsed is not None
    assert [(pkg.name, pkg.version) for pkg in parsed.packages] == [
        ("parent", "1.0.0"),
        ("leaf", "2.0.0"),
    ]
