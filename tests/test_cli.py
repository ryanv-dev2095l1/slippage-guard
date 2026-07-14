import json
from unittest.mock import patch
from decimal import Decimal
from slippage_guard.cli import main
from slippage_guard.types import OrderBook, PriceLevel


def _mock_fetch(symbol, exchange, depth):
    return OrderBook(
        symbol=symbol,
        exchange=exchange,
        bids=[PriceLevel(price=Decimal("100"), size=Decimal("5"))],
        asks=[PriceLevel(price=Decimal("102"), size=Decimal("5"))],
        timestamp=1700000000.0,
    )


@patch("slippage_guard.cli.fetch_order_book", side_effect=_mock_fetch)
def test_cli_json_output(mock_f, capsys):
    code = main([
        "--symbol", "SOL/USDT",
        "--exchange", "bybit",
        "--side", "buy",
        "--amount", "1.0",
        "--max-slippage-bps", "200",
        "--json",
    ])
    assert code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["symbol"] == "SOL/USDT"
    assert payload["is_breach"] is False
    assert payload["filled_amount"] == "1.0"
    assert "slippage_bps" in payload


@patch("slippage_guard.cli.fetch_order_book", side_effect=_mock_fetch)
def test_cli_metrics_file_output(mock_f, tmp_path):
    prom_file = tmp_path / "metrics.prom"
    code = main([
        "--symbol", "SOL/USDT",
        "--exchange", "bybit",
        "--side", "buy",
        "--amount", "1.0",
        "--max-slippage-bps", "5",
        "--prom-file", str(prom_file),
    ])
    assert code == 2  # breached (slippage is ~99 bps vs 5)
    assert prom_file.exists()
    content = prom_file.read_text(encoding="utf-8")
    assert "slippage_guard_breach" in content
    assert 'exchange="bybit"' in content


@patch("slippage_guard.cli.fetch_order_book", side_effect=Exception("connection refused"))
def test_cli_fetch_failure_exits_1(mock_f, capsys):
    code = main([
        "--symbol", "BTC/USDT",
        "--exchange", "coinbase",
        "--side", "buy",
        "--amount", "1.0",
        "--max-slippage-bps", "10",
    ])
    assert code == 1
    err = capsys.readouterr().err
    assert "error:" in err.lower()
