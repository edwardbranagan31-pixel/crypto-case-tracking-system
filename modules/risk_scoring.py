from __future__ import annotations

from typing import Any, Dict


def _to_float(value: Any, default: float = 0.0) -> float:
    """Convierte un valor arbitrario a float sin romper si llega un string no numérico."""
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = str(value).replace("$", "").replace(",", "").replace(" USD", "")
        return float(cleaned)
    except (TypeError, ValueError):
        return default


def compute_risk_score(case_data: Dict[str, Any]) -> float:
    """Calcula puntuación de riesgo del caso (0-100).
    
    Factores:
    - Monto de pérdida (hasta 35 puntos)
    - Cantidad de wallets (hasta 20 puntos)
    - Cantidad de exchanges (hasta 20 puntos)
    - Fondos trazados (10 puntos)
    - Wire bancario documentado (5 puntos)
    - Base mínima (15 puntos)
    """
    total_loss = _to_float(case_data.get("total_loss_usd", 0.0))
    traced = _to_float(case_data.get("traced_usd", 0.0))
    wallet_count = len(case_data.get("wallets", {}) or {})
    cex_count = len(case_data.get("cex_endpoints", []) or [])
    has_fiat_wire = case_data.get("fiat_wire", {}).get("amount") not in (None, "", "N/A")

    score = 15.0  # Base
    score += min(total_loss / 25000.0, 35.0)  # Monto
    score += min(wallet_count * 7.0, 20.0)  # Wallets
    score += min(cex_count * 8.0, 20.0)  # Exchanges
    score += 10.0 if traced > 0 else 0.0  # Trazabilidad
    score += 5.0 if has_fiat_wire else 0.0  # Wire documentado

    return round(min(score, 100.0), 1)


def get_risk_label(score: float) -> str:
    """Devuelve etiqueta y emoji de riesgo según puntuación."""
    if score >= 80:
        return "🔴 Crítico"
    if score >= 60:
        return "🟠 Alto"
    if score >= 35:
        return "🟡 Medio"
    return "🟢 Bajo"


def get_risk_color(score: float) -> str:
    """Devuelve color HTML para visualización."""
    if score >= 80:
        return "#ff0000"  # Rojo
    if score >= 60:
        return "#ff8800"  # Naranja
    if score >= 35:
        return "#ffdd00"  # Amarillo
    return "#00dd00"  # Verde


def compute_risk_for_cases(cases: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
    """Calcula riesgo para todos los casos."""
    return {case_id: compute_risk_score(case) for case_id, case in cases.items()}


def get_risk_summary(cases: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    """Devuelve resumen de casos por nivel de riesgo."""
    risks = compute_risk_for_cases(cases)
    summary = {"Crítico": 0, "Alto": 0, "Medio": 0, "Bajo": 0}

    for score in risks.values():
        if score >= 80:
            summary["Crítico"] += 1
        elif score >= 60:
            summary["Alto"] += 1
        elif score >= 35:
            summary["Medio"] += 1
        else:
            summary["Bajo"] += 1

    return summary
