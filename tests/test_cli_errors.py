"""Parse failures must not be reported as successful, clean scans."""

import json

import pytest

from lockfile_lint.cli import main


@pytest.mark.parametrize("json_output", [False, True], ids=["text", "json"])
@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("package-lock.json", '{"packages":'),
        ("pnpm-lock.yaml", "packages: ["),
    ],
)
def test_unparseable_lockfile_is_reported_as_failed_scan(
    tmp_path, capsys, filename, content, json_output
):
    lockfile = tmp_path / filename
    lockfile.write_text(content, encoding="utf-8")
    args = [str(tmp_path)]
    if json_output:
        args.append("--json")

    exit_code = main(args)
    output = capsys.readouterr()

    assert exit_code == 1
    assert str(lockfile) in output.err
    assert "failed to parse lockfile" in output.err
    if json_output:
        report = json.loads(output.out)
        assert report == {
            "findings": [],
            "scanned": 0,
            "errors": [{"path": str(lockfile), "message": "failed to parse lockfile"}],
        }
    else:
        assert "scanned 0 lockfile(s)" in output.out
        assert "scan incomplete" in output.out
        assert "no issues found" not in output.out


@pytest.mark.parametrize("json_output", [False, True], ids=["text", "json"])
@pytest.mark.parametrize("critical", [False, True], ids=["clean", "critical"])
@pytest.mark.parametrize("failed_filename", ["package-lock.json", "pnpm-lock.yaml"])
def test_parse_failure_does_not_hide_other_lockfiles(
    tmp_path, capsys, failed_filename, critical, json_output
):
    failed = tmp_path / failed_filename
    failed.write_text("[", encoding="utf-8")
    resolved = (
        "http://registry.example/fixture.tgz"
        if critical
        else "https://registry.example/fixture.tgz"
    )
    (tmp_path / "npm-shrinkwrap.json").write_text(
        json.dumps(
            {
                "lockfileVersion": 3,
                "packages": {"node_modules/fixture": {"version": "1.0.0", "resolved": resolved}},
            }
        ),
        encoding="utf-8",
    )
    args = [str(tmp_path), "--rules", "http-registry"]
    if json_output:
        args.append("--json")

    exit_code = main(args)
    output = capsys.readouterr()

    assert exit_code == (2 if critical else 1)
    assert str(failed) in output.err
    if json_output:
        report = json.loads(output.out)
        assert report["scanned"] == 1
        assert report["errors"] == [{"path": str(failed), "message": "failed to parse lockfile"}]
        assert len(report["findings"]) == (1 if critical else 0)
        if critical:
            assert report["findings"][0]["package"] == "fixture"
            assert report["findings"][0]["severity"] == "critical"
    else:
        assert "scanned 1 lockfile(s)" in output.out
        assert "scan incomplete" in output.out
        assert "no issues found" not in output.out
        if critical:
            assert "[http-registry]" in output.out


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("severity", ["clean", "warning", "critical"])
def test_successful_scan_preserves_exit_code_contract(tmp_path, capsys, severity, strict):
    package = {
        "version": "1.0.0",
        "resolved": "https://registry.example/fixture.tgz",
    }
    if severity == "clean":
        package["integrity"] = "sha512-fixture"
    elif severity == "critical":
        package["resolved"] = "http://registry.example/fixture.tgz"
    (tmp_path / "package-lock.json").write_text(
        json.dumps({"lockfileVersion": 3, "packages": {"node_modules/fixture": package}}),
        encoding="utf-8",
    )
    args = [str(tmp_path), "--json", "--rules", "http-registry", "missing-integrity"]
    if strict:
        args.append("--strict")

    exit_code = main(args)
    output = capsys.readouterr()

    expected = 2 if severity == "critical" else int(strict and severity == "warning")
    assert exit_code == expected
    assert output.err == ""
    report = json.loads(output.out)
    assert report["scanned"] == 1
    assert report["errors"] == []
    assert bool(report["findings"]) == (severity != "clean")
