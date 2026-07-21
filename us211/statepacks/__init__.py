"""State standard arrival packs — structured relocation + establishment guides."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import yaml


def _pack_path(state_code: str) -> Path:
    return Path(__file__).parent / f"{state_code.upper()}.yaml"


def exists(state_code: str) -> bool:
    return _pack_path(state_code).exists()


def load(state_code: str) -> dict[str, Any]:
    path = _pack_path(state_code)
    if not path.exists():
        raise FileNotFoundError(f"No standard pack for {state_code}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # YAML may parse YYYY-MM-DD as datetime.date; keep arrival packs JSON-friendly.
    if isinstance(data.get("last_verified"), date):
        data["last_verified"] = data["last_verified"].isoformat()
    return data


def list_states() -> list[str]:
    return sorted(p.stem for p in Path(__file__).parent.glob("*.yaml") if p.stem.isalpha())
