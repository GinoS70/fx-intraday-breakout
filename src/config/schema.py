"""
Configuration schema and loader.

This module defines dataclasses that mirror the expected structure of
the YAML configuration file (`config.yaml`).  A helper function
`load_config()` reads a YAML file from disk and returns an instance
of `Config` populated with reasonable defaults for any missing
fields.

Using dataclasses provides type hints and a clear contract for what
values are expected.  When extending the configuration, add new
fields to the appropriate dataclass and update `load_config()`
accordingly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import yaml


@dataclass
class SessionConfig:
    """Defines the trading session for each day.

    Attributes
    ----------
    start : str
        Start time in `HH:MM` 24‑hour format.  The time is interpreted in
        the timezone specified by the `data.timezone` configuration.
    end : str
        End time in `HH:MM` format.  The end is exclusive—no new
        positions are opened after this time.
    """

    start: str = "06:00"
    end: str = "20:00"


@dataclass
class CostsConfig:
    """Models trading costs.

    Attributes
    ----------
    spread : float
        Spread in price units.  For EURUSD a spread of `0.0002` equals 2 pips.
    slippage : float
        Additional price movement in the trader’s disfavor when orders are
        executed.  Also expressed in price units.
    commission_per_lot : float
        Commission charged per standard lot traded.  If your broker
        charges spread only, set this to zero.
    """

    spread: float = 0.0
    slippage: float = 0.0
    commission_per_lot: float = 0.0


@dataclass
class MT5Config:
    """Holds parameters required to connect to a MetaTrader 5 terminal.

    Attributes
    ----------
    login : int
        Account login number.  Use `0` when running offline backtests.
    password : str
        Password for the account.
    server : str
        Broker server name (e.g. ``Bidget-MT5-Live``).
    path : str
        File system path to the MetaTrader 5 terminal executable
        (`terminal64.exe`).  Required for paper/live trading.
    """

    login: int = 0
    password: str = ""
    server: str = ""
    path: str = ""


@dataclass
class DataConfig:
    """Data source configuration.

    Attributes
    ----------
    csv_dir : str
        Directory containing CSV files for each symbol when running
        backtests.
    timezone : str
        IANA timezone name used both for interpreting timestamps in
        historical data and for defining the trading session.
    """

    csv_dir: str = "data"
    timezone: str = "Europe/Brussels"


@dataclass
class Config:
    """Root configuration for the trading program.

    Attributes
    ----------
    symbols : List[str]
        List of instrument symbols (e.g. ``["EURUSD", "GBPUSD"]``).
    timeframe : str
        Bar timeframe (currently only ``H1`` is supported by the strategy).
    session : SessionConfig
        Trading session start and end times.
    sl_pct : float
        Stop‑loss expressed as a fraction of the entry price (e.g. 0.005 for
        0.5 %).
    tp_pct : float
        Take‑profit expressed as a fraction of the entry price.
    equity_pct_per_trade : float
        Fraction of account equity allocated to each trade (e.g. 0.02 = 2 %).
    costs : CostsConfig
        Trading costs configuration.
    mt5 : MT5Config
        MetaTrader 5 connection configuration.
    mode : str
        Operating mode: ``backtest``, ``paper`` or ``live``.
    data : DataConfig
        Data source configuration.
    """

    symbols: List[str] = field(default_factory=lambda: ["EURUSD"])
    timeframe: str = "H1"
    session: SessionConfig = field(default_factory=SessionConfig)
    sl_pct: float = 0.005
    tp_pct: float = 0.005
    equity_pct_per_trade: float = 0.02
    costs: CostsConfig = field(default_factory=CostsConfig)
    mt5: MT5Config = field(default_factory=MT5Config)
    mode: str = "backtest"
    data: DataConfig = field(default_factory=DataConfig)


def _merge_dict(defaults: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries.

    The values in `override` take precedence over those in `defaults`.
    This helper is used when loading YAML into nested dataclasses.
    """
    result: Dict[str, Any] = defaults.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str) -> Config:
    """Load a configuration file from the given YAML path.

    Parameters
    ----------
    path : str
        Path to the YAML file.

    Returns
    -------
    Config
        A populated configuration object.  Missing fields are filled with
        sensible defaults defined in the dataclasses.
    """
    with open(path, "r", encoding="utf-8") as fh:
        raw: Dict[str, Any] = yaml.safe_load(fh) or {}

    # Build nested dictionaries representing the default dataclasses
    defaults: Dict[str, Any] = {
        'symbols': ["EURUSD"],
        'timeframe': "H1",
        'session': {
            'start': "06:00",
            'end': "20:00",
        },
        'sl_pct': 0.005,
        'tp_pct': 0.005,
        'equity_pct_per_trade': 0.02,
        'costs': {
            'spread': 0.0,
            'slippage': 0.0,
            'commission_per_lot': 0.0,
        },
        'mt5': {
            'login': 0,
            'password': "",
            'server': "",
            'path': "",
        },
        'mode': 'backtest',
        'data': {
            'csv_dir': 'data',
            'timezone': 'Europe/Brussels',
        },
    }

    merged = _merge_dict(defaults, raw)

    # Construct dataclasses from the merged dictionary
    session_cfg = SessionConfig(**merged['session'])
    costs_cfg = CostsConfig(**merged['costs'])
    mt5_cfg = MT5Config(**merged['mt5'])
    data_cfg = DataConfig(**merged['data'])

    cfg = Config(
        symbols=list(merged.get('symbols', [])),
        timeframe=str(merged.get('timeframe', 'H1')),
        session=session_cfg,
        sl_pct=float(merged.get('sl_pct', 0.005)),
        tp_pct=float(merged.get('tp_pct', 0.005)),
        equity_pct_per_trade=float(merged.get('equity_pct_per_trade', 0.02)),
        costs=costs_cfg,
        mt5=mt5_cfg,
        mode=str(merged.get('mode', 'backtest')).lower(),
        data=data_cfg,
    )
    return cfg