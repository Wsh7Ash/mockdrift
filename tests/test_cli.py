import json

from conftest import run_cli


def test_drifted_fixture_fails_the_default_gate() -> None:
    result = run_cli("check", "fixtures/app")
    assert result.returncode == 1
    assert "unknown-keyword" in result.stdout
    assert "GATE     fail-on=error -> FAIL" in result.stdout


def test_clean_fixture_passes() -> None:
    result = run_cli("check", "fixtures/clean")
    assert result.returncode == 0
    assert "No drift" in result.stdout


def test_fail_on_none_exits_zero() -> None:
    result = run_cli("check", "fixtures/app", "--fail-on", "none")
    assert result.returncode == 0
    assert "GATE     fail-on=none -> pass" in result.stdout


def test_fail_on_warn_catches_warnings_too() -> None:
    result = run_cli("check", "fixtures/app", "--fail-on", "warn")
    assert result.returncode == 1
    assert "2 warn" in result.stdout


def test_json_output_is_valid() -> None:
    result = run_cli("check", "fixtures/app", "--json")
    payload = json.loads(result.stdout)
    assert payload["summary"]["gate"] == "fail"
    assert payload["summary"]["counts"]["error"] == 4
    codes = {finding["code"] for finding in payload["findings"]}
    assert {"stale-target", "unknown-keyword", "too-many-arguments"} <= codes
    assert any(site["target"] == "requests.get" for site in payload["sites"])


def test_show_ok_lists_sites() -> None:
    result = run_cli("check", "fixtures/app", "--show-ok", "--fail-on", "none")
    assert "PATCH SITES" in result.stdout
    assert "app.billing.charge [found]" in result.stdout


def test_missing_root_is_a_usage_error() -> None:
    result = run_cli("check", "fixtures/nope")
    assert result.returncode == 2
    assert "root directory not found" in result.stderr


def test_output_is_repeatable() -> None:
    first = run_cli("check", "fixtures/app", "--json")
    second = run_cli("check", "fixtures/app", "--json")
    assert first.stdout == second.stdout
