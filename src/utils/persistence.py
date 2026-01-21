"""
State persistence utilities.

Paper and live trading sessions need to remember their state across
restarts: which positions are currently open and the timestamp of
the last processed bar.  This module provides simple JSON‑based
load/save functions for that purpose.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def load_state(path: str) -> Optional[Dict[str, Any]]:
    """Load a JSON state file.

    Parameters
    ----------
    path : str
        Path to the JSON file.

    Returns
    -------
    dict or None
        The state dictionary if the file exists, otherwise `None`.
    """
    file_path = Path(path)
    if not file_path.exists():
        return None
    with file_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def save_state(path: str, state: Dict[str, Any]) -> None:
    """Write a JSON state file to disk.

    Parameters
    ----------
    path : str
        Path to the output file.
    state : dict
        Arbitrary state dictionary.  Must be serialisable to JSON.
    """
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2, sort_keys=True)