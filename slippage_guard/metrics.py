import os
import tempfile
from pathlib import Path
from typing import Dict
from slippage_guard.types import SimReport


def _escape_label_value(val: str) -> str:
    return val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def format_labels(labels: Dict[str, str]) -> str:
    items = [f'{k}="{_escape_label_value(str(v))}"' for k, v in sorted(labels.items())]
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
        f"slippage_guard_expected_slippage_bps{lbl_str} {report.slippage_bps:.4f}",
        "# HELP slippage_guard_simulated_vwap Volume weighted average fill price",
        "# TYPE slippage_guard_simulated_vwap gauge",
        f"slippage_guard_simulated_vwap{lbl_str} {report.vwap:.8f}",
        "# HELP slippage_guard_mid_price Best bid/ask midpoint before fill",
        "# TYPE slippage_guard_mid_price gauge",
        f"slippage_guard_mid_price{lbl_str} {report.mid_price:.8f}",
        "# HELP slippage_guard_book_depth_exhausted_flag 1 if requested volume exceeded fetched book depth",
        "# TYPE slippage_guard_book_depth_exhausted_flag gauge",
        f"slippage_guard_book_depth_exhausted_flag{lbl_str} {1 if report.partial_fill else 0}",
        "# HELP slippage_guard_breach 1 if slippage exceeded tolerance threshold, 0 otherwise",
        "# TYPE slippage_guard_breach gauge",
        f"slippage_guard_breach{lbl_str} {1 if report.is_breach else 0}",
    ]
    return "\n".join(lines) + "\n"


def write_textfile(path: str, report: SimReport) -> None:
    out = Path(path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to a temp file in the same directory first so os.replace is atomic across mounts
    payload = format_metrics(report)
    with tempfile.NamedTemporaryFile(
        "w",
        dir=out.parent,
        prefix=f".{out.name}.tmp-",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(payload)
        tmp_path = tmp.name

    os.replace(tmp_path, out)
