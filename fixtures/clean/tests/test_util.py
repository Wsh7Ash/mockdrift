from unittest.mock import patch

from app.util import total


@patch("app.util.total")
def test_total_ok(mock_total):
    total([1, 2], tax=5)
    mock_total.assert_called_once_with([1, 2], tax=5)
