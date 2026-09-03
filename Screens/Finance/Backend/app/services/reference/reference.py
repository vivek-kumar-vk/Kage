from __future__ import annotations

import json
from pathlib import Path

_CACHE: dict[str, dict] = {}
_DIR = Path(__file__).resolve().parent


def load(name: str) -> dict:
    if name in _CACHE:
        return _CACHE[name]
    path = _DIR / f"{name}.json"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    _CACHE[name] = data
    return data