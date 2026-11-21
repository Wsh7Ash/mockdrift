from unittest.mock import patch

from app import billing
from app.mailer import send  # noqa: F401 - imported to exercise import resolution


@patch("app.billing.charge")
def test_charge_ok(mock_charge):
    billing.charge(1, 500)
    mock_charge.assert_called_once_with(1, 500)


@patch("app.billing.charge")
def test_charge_unknown_keyword(mock_charge):
    mock_charge(1, 500, currency="eur", timeout=3)  # DRIFT-UNKNOWN-KEYWORD


@patch("app.billing.charge")
def test_charge_too_many(mock_charge):
    mock_charge(1, 500, 9)  # DRIFT-TOO-MANY


@patch("app.billing.missing_symbol")  # DRIFT-STALE
def test_stale_target(mock_missing):
    mock_missing(1)


@patch("app.billing.charge")
def test_missing_required(mock_charge):
    mock_charge(1)  # DRIFT-MISSING


@patch.object(billing.InvoiceGateway, "send")
def test_gateway_unknown_keyword(mock_send):
    mock_send(7, approve=True)  # DRIFT-METHOD


@patch("app.billing.log_event")
def test_varargs_ok(mock_log):
    mock_log("start", 1, 2, extra=True)  # CLEAN-VARARGS


@patch("app.billing.schedule")
def test_missing_kwonly(mock_schedule):
    mock_schedule("backup")  # DRIFT-MISSING-KWONLY


@patch("app.mailer.send")
def test_with_alias_ok(mock_send):
    with patch("app.mailer.send", return_value=True) as send_mock:
        send_mock("a@b.example", "hi")
    mock_send.assert_called_with("a@b.example", "subject")


@patch("requests.get")
def test_external_target(mock_get):  # EXTERNAL-TARGET
    mock_get("https://example.invalid")
