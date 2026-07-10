# slippage-guard

I built this because our hourly rebalancer kept eating 40-70 bps of slippage on thin books whenever depth dropped right before execution. `slippage-guard` queries the live L2 book, simulates walking the depth for your exact order size, and exits with a non-zero code if expected slippage exceeds your threshold.

## Install

```bash
pip install .
```

## Quick check

```bash
# Check if selling 25,000 USDT worth of ARB slips more than 15 bps on Binance
slippage-guard --exchange binance --pair ARBUSDT --side sell --size 25000 --max-slippage-bps 15
```

Returns exit code `0` if safe to trade, `2` if slippage is too high, or `1` on exchange API errors.
