import json
import sys
import time
import urllib.error
import urllib.request
from typing import Optional
from slippage_guard.types import SimReport


def _is_discord(url: str) -> bool:
    return "discord.com/api/webhooks" in url or "discordapp.com/api/webhooks" in url


def _build_discord_payload(report: SimReport) -> dict:
    fields = [
        {"name": "Side", "value": report.side.value.upper(), "inline": True},
        {"name": "Requested", "value": f"{report.amount:,.4f} (${report.notional_usd:,.2f})", "inline": True},
        {"name": "Mid Price", "value": f"{report.mid_price:,.4f}", "inline": True},
        {"name": "VWAP", "value": f"{report.vwap:,.4f}", "inline": True},
        {"name": "Slippage", "value": f"**{report.slippage_bps:.2f} bps** (max: {report.max_slippage_bps:.2f})", "inline": True},
    ]
    if report.partial_fill:
        fields.append({"name": "Warning", "value": "Order book depth exhausted before full fill!", "inline": False})

    return {
        "username": "Slippage Guard",
        "embeds": [{
            "title": f"REBALANCE ABORTED: {report.symbol} on {report.exchange}",
            "color": 14431525,  # orange-red
            "fields": fields,
            "footer": {"text": "Execution blocked by pre-trade tolerance check."}
        }]
    }


def _build_slack_payload(report: SimReport) -> dict:
    warning = "\n:rotating_light: *Book depth exhausted before full fill!*" if report.partial_fill else ""
    return {
        "text": (
            f":no_entry: *Rebalance Aborted* - *{report.symbol}* on *{report.exchange}*\n"
            f"> Slippage: *{report.slippage_bps:.2f} bps* (tolerance: {report.max_slippage_bps:.2f} bps)\n"
            f"> Fill VWAP: `{report.vwap:,.4f}` vs Mid: `{report.mid_price:,.4f}`\n"
            f"> Amount: `{report.amount:,.4f}` (~${report.notional_usd:,.2f}){warning}"
        )
    }


def send_alert(webhook_url: Optional[str], report: SimReport) -> bool:
    """Posts a formatted incident message to Slack or Discord webhook."""
    if not webhook_url:
        return False

    payload = _build_discord_payload(report) if _is_discord(webhook_url) else _build_slack_payload(report)
    data = json.dumps(payload).encode("utf-8")

    # one retry on transient timeout/5xx, fail silently otherwise to avoid blocking caller
    for attempt in range(2):
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "slippage-guard/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                return resp.status in (200, 204)
        except urllib.error.HTTPError as e:
            # print(f"alert failed with {e.code}")
            if e.code in (500, 502, 503, 504) and attempt == 0:
                time.sleep(0.5)
                continue
            sys.stderr.write(f"slippage-guard: alert webhook returned http {e.code}\n")
            return False
        except Exception as e:
            if attempt == 0:
                time.sleep(0.5)
                continue
            sys.stderr.write(f"slippage-guard: alert failed: {e}\n")
            return False
    return False
