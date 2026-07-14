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


def _build_slack_payload(report: SimReport) -> dict:
    return {
        "text": f":warning: *Slippage Guard Alert* :warning:\nRebalance aborted for *{report.symbol}* on *{report.exchange}*.\nExpected slippage: *{report.slippage_bps:.1f} bps* exceeds limit of *{report.max_slippage_bps:.1f} bps*.\nVWAP: `{report.vwap:.4f}` | Mid: `{report.mid_price:.4f}` | Notional: `${report.notional_usd:,.2f}`"
    }


def send_alert(webhook_url: Optional[str], report: SimReport, is_discord: bool = False) -> bool:
    if not webhook_url:
        return False

    payload = _build_discord_payload(report) if is_discord else _build_slack_payload(report)
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "slippage-guard/0.1"}
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status in (200, 204)
    except Exception:
        return False
