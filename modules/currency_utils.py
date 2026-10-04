from __future__ import annotations

from typing import Any


def _to_float(value: Any, default: float = 0.0) -> float:
    """Convierte un valor monetario a float sin romper con cadenas formateadas."""
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = str(value).replace("$", "").replace(",", "").replace(" USD", "")
        return float(cleaned)
    except (TypeError, ValueError):
        return default
