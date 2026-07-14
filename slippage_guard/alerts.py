import json
import urllib.request
from typing import Optional
from slippage_guard.types import SimReport


def _build_discord_payload(report: SimReport) -> dict:
    return {
        "username": "Slippage Guard",
        "embeds": [{
            "title": f"BREACH: {report.symbol} on {report.exchange.upper()}",
            "color": 15158332, # red
            "fields": [
                {"name": "Side", "value": report.side.value.upper(), "inline": True},
                {"name": "Requested Notional", "value": f"${report.notional_usd:,.2f}", "inline": True},
                {"name": "Mid Price", "value": f"{report.mid_price:.4f}", "inline": True},
                {"name": "Simulated VWAP", "value": f"{report.vwap:.4f}", "inline": True},
                {"name": "Slippage", "value": f"{report.slippage_bps:.1f} bps (max: {report.max_slippage_bps:.1f} bps)", "inline": False},
            ],
            "footer": {"text": "Automated rebalance aborted."}
        }]
    }


