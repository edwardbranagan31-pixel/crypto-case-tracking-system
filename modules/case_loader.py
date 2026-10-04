from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_cases_from_json(file_path: str | Path) -> Dict[str, Dict[str, Any]]:
    """Carga múltiples casos desde archivo JSON."""
    path = Path(file_path)
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_cases_to_json(file_path: str | Path, cases: Dict[str, Dict[str, Any]]) -> None:
    """Guarda casos en archivo JSON."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with path.open("w", encoding="utf-8") as handle:
            json.dump(cases, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _to_float(value: Any, default: float = 0.0) -> float:
    """Convierte un valor de dinero a float sin romper con cadenas formateadas."""
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = str(value).replace("$", "").replace(",", "").replace(" USD", "")
        return float(cleaned)
    except (TypeError, ValueError):
        return default


def get_case_payload(case_id: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Prepara payload normalizado de caso para API o Neo4j."""
    return {
        "case_id": case_id,
        "title": case_data.get("title", case_id),
        "victim": case_data.get("victim", "Unknown"),
        "police_report": case_data.get("police_report", case_id),
        "total_loss_usd": _to_float(case_data.get("total_loss_usd", 0.0)),
        "traced_usd": _to_float(case_data.get("traced_usd", 0.0)),
        "wallets": case_data.get("wallets", {}),
        "cex_endpoints": case_data.get("cex_endpoints", []),
        "fiat_wire": case_data.get("fiat_wire", {}),
    }


def batch_load_cases(cases_list: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Carga un lote de casos desde lista de diccionarios."""
    result = {}
    for case in cases_list:
        case_id = case.get("case_id", "")
        if case_id:
            result[case_id] = case
    return result
