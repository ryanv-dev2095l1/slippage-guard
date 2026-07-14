from unittest.mock import patch
from decimal import Decimal
from slippage_guard.cli import main
from slippage_guard.types import OrderBook, PriceLevel


def _mock_fetch(symbol, exchange, depth):
    return OrderBook(
        symbol=symbol,
        exchange=exchange,
        bids=[PriceLevel(price=Decimal("2000"), size=Decimal("10"))],
        asks=[PriceLevel(price=Decimal("2002"), size=Decimal("10"))],
        timestamp=1700000000.0,
    )


@patch("slippage_guard.cli.fetch_order_book", side_effect=_mock_fetch)
def test_cli_pass_within_tolerance(mock_f, capsys):
    # Mid is 2001, buy 1 ETH @ 2002 -> ~4.99 bps slippage. Limit is 15 bps -> exit 0
    code = main([
        "--symbol", "ETH/USDT",
        "--exchange", "binance",
        "--side", "buy",
        "--amount", "1.0",
        "--max-slippage-bps", "15",
    ])
    assert code == 0
    out = capsys.readouterr().out
    assert "PASS" in out
    assert "ETH/USDT" in out


@patch("slippage_guard.cli.fetch_order_book", side_effect=_mock_fetch)
def test_cli_breach_exits_2(mock_f, capsys):
    # Slippage is ~4.99 bps, limit is 1.0 bps -> exit 2
    code = main([
        "--symbol", "ETH/USDT",
        "--exchange", "binance",
        "--side", "buy",
        "--amount", "1.0",
        "--max-slippage-bps", "1.0",
    ])
    assert code == 2
    out = capsys.readouterr().out
    assert "BREACH" in out
