from __future__ import annotations

import math
from typing import Any


def _to_float(value: Any, default: float = 0.0) -> float:
    """Convierte un valor monetario a float sin romper con cadenas formateadas."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        converted = float(value)
        return converted if math.isfinite(converted) else default
    try:
        cleaned = str(value).strip().replace("$", "").replace(",", "").strip()
        if cleaned[:3].upper() == "USD":
            cleaned = cleaned[3:].strip()
        if cleaned[-3:].upper() == "USD":
            cleaned = cleaned[:-3].strip()
        converted = float(cleaned)
        return converted if math.isfinite(converted) else default
    except (TypeError, ValueError):
        return default
