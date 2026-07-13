import argparse
import sys
from decimal import Decimal
from slippage_guard.engine import simulate_execution
from slippage_guard.fetcher import fetch_order_book
from slippage_guard.types import SlippageError

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="slippage-guard",
        description="Check simulated execution slippage against live books."
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["buy", "sell", "BUY", "SELL"])
    parser.add_argument("--amount", required=True, type=str, help="Order size in base currency")
    parser.add_argument("--max-bps", type=str, default="15.0", help="Max allowed slippage in basis points")
    parser.add_argument("--exchange", default="binance", help="Exchange to pull L2 book from")
    return parser

def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    amount = Decimal(args.amount)
    max_bps = Decimal(args.max_bps)
    side = args.side.lower()

    try:
        book = fetch_order_book(args.symbol, exchange=args.exchange)
        result = simulate_execution(book, side, amount, max_bps=max_bps)
    except SlippageError as err:
        print(f"GUARD ABORT: {err}", file=sys.stderr)
        return 2
    except Exception as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return 1

    print(f"OK: {args.symbol} {side} {amount} | VWAP: {result.vwap:.4f} | Slippage: {result.slippage_bps:.2f} bps")
    return 0

if __name__ == "__main__":
    sys.exit(main())
