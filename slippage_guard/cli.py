import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List

from slippage_guard.engine import simulate_batch, simulate_execution
from slippage_guard.fetcher import fetch_order_book
from slippage_guard.types import RebalanceLeg, SlippageError

def _parse_rebalance_file(filepath: Path) -> List[RebalanceLeg]:
    with open(filepath, "r", encoding="utf-8") as f:
        raw = json.load(f)
    
    legs = []
    items = raw if isinstance(raw, list) else raw.get("orders", raw.get("legs", []))
    for it in items:
        legs.append(RebalanceLeg(
            symbol=it["symbol"],
            side=it["side"].lower(),
            amount=Decimal(str(it["amount"])),
            quote_currency=it.get("quote_currency", False),
            max_slippage_bps=Decimal(str(it["max_slippage_bps"])) if "max_slippage_bps" in it else None,
        ))
    return legs

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="slippage-guard",
        description="L2 orderbook slippage pre-flight checker for rebalances."
    )
    # Single order mode or batch mode
    p.add_argument("--symbol", help="Trading pair (e.g. ETHUSDT)")
    p.add_argument("--side", choices=["buy", "sell", "BUY", "SELL"])
    p.add_argument("--amount", type=str, help="Order size")
    p.add_argument("--file", "-f", type=Path, help="Path to rebalance JSON plan")
    p.add_argument("--max-bps", type=str, default="20.0", help="Global max slippage in basis points")
    p.add_argument("--exchange", default="binance", help="Exchange adapter")
    p.add_argument("--json", action="store_true", help="Print output as JSON")
    p.add_argument("--quiet", "-q", action="store_true", help="Suppress non-error output")
    return p

def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    default_max_bps = Decimal(args.max_bps)

    if args.file:
        if not args.file.exists():
            print(f"File not found: {args.file}", file=sys.stderr)
            return 1
        try:
            legs = _parse_rebalance_file(args.file)
        except Exception as e:
            print(f"Failed to parse plan file: {e}", file=sys.stderr)
            return 1
        
        res = simulate_batch(legs, exchange=args.exchange, default_max_bps=default_max_bps)
        
        if args.json:
            out: Dict[str, Any] = {
                "passed": res.passed,
                "total_legs": res.total_legs,
                "aborted_legs": res.aborted_legs,
                "results": [
                    {
                        "symbol": r.symbol,
                        "side": r.side,
                        "requested": str(r.requested_size),
                        "filled": str(r.filled_size),
                        "vwap": str(r.vwap),
                        "mid": str(r.mid_price),
                        "slippage_bps": str(r.slippage_bps),
                        "aborted": r.is_aborted,
                    }
                    for r in res.results
                ]
            }
            print(json.dumps(out, indent=2))
        else:
            if not args.quiet:
                for r in res.results:
                    status = "[ABORT]" if r.is_aborted else "[OK]"
                    print(f"{status} {r.symbol} {r.side} {r.requested_size} -> slippage {r.slippage_bps:.2f} bps (vwap {r.vwap:.4f})")
            if not res.passed:
                print(f"REBALANCE ABORTED: {res.aborted_legs} leg(s) breached limits", file=sys.stderr)
        
        return 0 if res.passed else 2

    # Single order mode
    if not (args.symbol and args.side and args.amount):
        print("Must provide either --file or (--symbol, --side, --amount)", file=sys.stderr)
        return 1

    try:
        book = fetch_order_book(args.symbol, exchange=args.exchange)
        amt = Decimal(args.amount)
        r = simulate_execution(book, args.side.lower(), amt, max_bps=default_max_bps)
        
        if args.json:
            print(json.dumps({
                "symbol": r.symbol,
                "side": r.side,
                "amount": str(r.requested_size),
                "vwap": str(r.vwap),
                "mid": str(r.mid_price),
                "slippage_bps": str(r.slippage_bps),
                "worst_price": str(r.worst_price),
                "levels_consumed": r.levels_consumed,
                "passed": not r.is_aborted
            }, indent=2))
        elif not args.quiet:
            print(f"OK: {r.symbol} {r.side} {r.requested_size} | VWAP: {r.vwap:.4f} | Slippage: {r.slippage_bps:.2f} bps")
        return 0
    except SlippageError as err:
        if args.json:
            print(json.dumps({"error": "slippage_breached", "detail": str(err)}))
        else:
            print(f"GUARD ABORT: {err}", file=sys.stderr)
        return 2
    except Exception as err:
        if args.json:
            print(json.dumps({"error": "execution_failed", "detail": str(err)}))
        else:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
