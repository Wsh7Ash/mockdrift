from collections import Counter

from mockdrift.analyze import analyze
from conftest import FIXTURES, line_of

FIXTURE_TESTS = FIXTURES / "app" / "tests" / "test_billing.py"


def test_fixture_finding_counts() -> None:
    report = analyze(FIXTURES / "app")
    counter = Counter(finding.code for finding in report.findings)
    assert counter["unknown-keyword"] == 2
    assert counter["too-many-arguments"] == 1
    assert counter["missing-required-argument"] == 2
    assert counter["stale-target"] == 1
    assert len(report.findings) == 6


def test_unknown_keyword_points_at_the_call_line() -> None:
    report = analyze(FIXTURES / "app")
    line = line_of(FIXTURE_TESTS, "DRIFT-UNKNOWN-KEYWORD")
    finding = next(item for item in report.findings if item.line == line)
    assert finding.code == "unknown-keyword"
    assert "timeout" in finding.message
    assert "charge(customer_id, amount_cents" in finding.message


def test_too_many_positional_arguments() -> None:
    report = analyze(FIXTURES / "app")
    line = line_of(FIXTURE_TESTS, "DRIFT-TOO-MANY")
    finding = next(item for item in report.findings if item.line == line)
    assert finding.code == "too-many-arguments"
    assert "3 positional argument(s)" in finding.message


def test_stale_target_is_an_error_on_the_decorator_line() -> None:
    report = analyze(FIXTURES / "app")
    line = line_of(FIXTURE_TESTS, "DRIFT-STALE")
    finding = next(item for item in report.findings if item.code == "stale-target")
    assert finding.line == line
    assert finding.severity == "error"
    assert "app.billing" in finding.message
    assert "charge" in finding.message


def test_missing_required_positional_is_a_warning() -> None:
    report = analyze(FIXTURES / "app")
    line = line_of(FIXTURE_TESTS, "DRIFT-MISSING")
    finding = next(item for item in report.findings if item.line == line)
    assert finding.code == "missing-required-argument"
    assert finding.severity == "warn"
    assert "amount_cents" in finding.message


def test_patch_object_checks_the_method_signature() -> None:
    report = analyze(FIXTURES / "app")
    line = line_of(FIXTURE_TESTS, "DRIFT-METHOD")
    finding = next(item for item in report.findings if item.line == line)
    assert finding.code == "unknown-keyword"
    assert "approve" in finding.message
    assert finding.target == "app.billing.InvoiceGateway.send"


def test_missing_required_keyword_only_is_reported() -> None:
    report = analyze(FIXTURES / "app")
    line = line_of(FIXTURE_TESTS, "DRIFT-MISSING-KWONLY")
    finding = next(item for item in report.findings if item.line == line)
    assert finding.code == "missing-required-argument"
    assert "at" in finding.message


def test_varargs_do_not_produce_findings() -> None:
    report = analyze(FIXTURES / "app")
    line = line_of(FIXTURE_TESTS, "CLEAN-VARARGS")
    assert all(finding.line != line for finding in report.findings)


def test_external_targets_are_not_flagged() -> None:
    report = analyze(FIXTURES / "app")
    assert all("requests" not in finding.target for finding in report.findings)
    assert any("requests.get" in note for note in report.notes)


def test_clean_fixture_has_no_findings() -> None:
    report = analyze(FIXTURES / "clean")
    assert report.findings == []
    assert report.worst == "none"


def test_checked_call_count_covers_decorator_and_with_aliases() -> None:
    report = analyze(FIXTURES / "app")
    assert report.checked_calls >= 10


def test_sites_record_resolution_status() -> None:
    report = analyze(FIXTURES / "app")
    statuses = {site.target: site.status for site in report.sites}
    assert statuses["app.billing.charge"] == "found"
    assert statuses["app.billing.missing_symbol"] == "missing"
    assert statuses["requests.get"] == "external"
