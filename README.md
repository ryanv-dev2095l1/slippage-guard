# slippage-guard

I built this because our hourly rebalancer kept eating 40-70 bps of slippage on thin books whenever depth dropped right before execution. `slippage-guard` queries the live L2 book, simulates walking the depth for your exact order size, and exits with a non-zero code if expected slippage exceeds your threshold.

## Install

```bash
pip install .
```

## Quick run

```bash
# Check if selling 25,000 USDT worth of ARB slips more than 15 bps on Binance
slippage-guard --exchange binance --pair ARBUSDT --side sell --size 25000 --max-slippage-bps 15
```

## Automated pipeline integration

Drop it right before your order execution script in bash or cron:

```bash
#!/usr/bin/env bash
set -e

PAIR="SOLUSDT"
AMOUNT_USD="50000"

echo "Running pre-flight slippage check..."
slippage-guard --exchange binance --pair "$PAIR" --side buy --size "$AMOUNT_USD" --max-slippage-bps 20 \
  || { echo "Aborting rebalance: depth too shallow"; exit 0; }

# Safe to submit orders
python execute_rebalance.py --pair "$PAIR" --usd "$AMOUNT_USD"
```

## Exit codes

- `0`: Slippage is within tolerance.
- `2`: Guard tripped. Slippage exceeds `--max-slippage-bps` or available book depth cannot absorb order.
- `1`: Network failure, timeout, invalid symbol, or exchange rate limit.

<!-- generated: 2026-09-09 -->
