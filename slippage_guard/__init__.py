"""Slippage guard package."""

__version__ = "0.1.0"

from slippage_guard.types import ExecutionPlan, SlippageResult
from slippage_guard.engine import simulate_execution

__all__ = ["simulate_execution", "ExecutionPlan", "SlippageResult"]
