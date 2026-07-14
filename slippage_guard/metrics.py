from pathlib import Path
from typing import Dict, Any
from slippage_guard.types import SimReport


def format_labels(labels: Dict[str, str]) -> str:
    items = [f'{k}="{v}"' for k, v in sorted(labels.items())]
    return f"{{{','.join(items)}}}" if items else ""


def format_metrics(report: SimReport) -> str:
    labels = {
        "symbol": report.symbol,
        "exchange": report.exchange,
        "side": report.side.value,
    }
    lbl_str = format_labels(labels)

    lines = [
        "# HELP slippage_guard_expected_slippage_bps Simulated slippage against book in basis points",
        "# TYPE slippage_guard_expected_slippage_bps gauge",
        f"slippage_guard_expected_slippage_bps{lbl_str} {report.slippage_bps:.2f}",
        "# HELP slippage_guard_simulated_vwap Volume weighted average fill price",
        "# TYPE slippage_guard_simulated_vwap gauge",
        f"slippage_guard_simulated_vwap{lbl_str} {report.vwap:.6f}",
        "# HELP slippage_guard_mid_price Best bid/ask midpoint before fill",
        "# TYPE slippage_guard_mid_price gauge",
        f"slippage_guard_mid_price{lbl_str} {report.mid_price:.6f}",
        "# HELP slippage_guard_breach Whether max tolerance was exceeded (1 or 0)",
        "# TYPE slippage_guard_breach gauge",
        f"slippage_guard_breach{lbl_str} {1 if report.is_breach else 0}",
    ]
    return "\n".join(lines) + "\n"


def write_textfile(path: str, report: SimReport) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(format_metrics(report), encoding="utf-8")
