from pathlib import Path

from mockdrift.symbols import discover, resolve
from conftest import FIXTURES


def test_discovers_modules_without_the_init_suffix() -> None:
    modules, notes = discover(FIXTURES / "app")
    assert notes == []
    assert set(modules) == {"app", "app.billing", "app.mailer", "tests.test_billing"}


def test_function_symbol_keeps_the_signature() -> None:
    modules, _ = discover(FIXTURES / "app")
    status, symbol = resolve(modules, "app.billing.charge")
    assert status == "found"
    assert symbol is not None
    assert symbol.signature is not None
    assert symbol.signature.positional == ("customer_id", "amount_cents")
    assert symbol.signature.kwonly == ("currency", "idempotency_key")


def test_class_symbol_exposes_children() -> None:
    modules, _ = discover(FIXTURES / "app")
    status, symbol = resolve(modules, "app.billing.InvoiceGateway")
    assert status == "found"
    assert symbol is not None
    assert "send" in symbol.children


def test_method_signature_drops_self() -> None:
    modules, _ = discover(FIXTURES / "app")
    status, symbol = resolve(modules, "app.billing.InvoiceGateway.send")
    assert status == "found"
    assert symbol is not None
    assert symbol.signature is not None
    assert symbol.signature.positional == ("invoice_id",)
    assert symbol.signature.kwonly == ("dry_run",)


def test_missing_attribute_is_reported_as_internal() -> None:
    modules, _ = discover(FIXTURES / "app")
    status, symbol = resolve(modules, "app.billing.nope")
    assert status == "missing"
    assert symbol is not None
    assert "charge" in symbol.children


def test_third_party_target_is_external() -> None:
    modules, _ = discover(FIXTURES / "app")
    assert resolve(modules, "requests.get") == ("external", None)


def test_unparsable_file_is_noted_and_skipped(tmp_path: Path) -> None:
    (tmp_path / "broken.py").write_text("def (\n", encoding="utf-8")
    (tmp_path / "ok.py").write_text("def fine():\n    pass\n", encoding="utf-8")
    modules, notes = discover(tmp_path)
    assert "broken" not in modules
    assert "ok" in modules
    assert any("could not be parsed" in note for note in notes)


def test_missing_root_is_an_error(tmp_path: Path) -> None:
    import pytest

    from mockdrift.symbols import DiscoveryError

    with pytest.raises(DiscoveryError):
        discover(tmp_path / "nope")
