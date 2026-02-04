# fx-intraday-breakout

This repository contains a complete algorithmic trading system for foreign exchange (FX) pairs. It supports offline backtesting using CSV data, as well as paper trading and live trading via MetaTrader 5. The strategy implemented is an intraday breakout that enters long or short positions when hourly highs or lows exceed the running intraday extremes during a configurable session window. See `config.yaml` for configuration options and `src/` for the codebase.

## Requirements

- `requirements.txt` includes `MetaTrader5` only on Windows (conditional marker) because the package is distributed for Windows via pip and is not available on macOS/Linux. Use Windows if you plan to run paper/live trading with MT5.
