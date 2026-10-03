from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


def add_alert_history(case_id: str, message: str) -> List[Dict[str, Any]]:
    """Registra alerta en historial persistente."""
    import streamlit as st

    history = st.session_state.setdefault("alert_history", [])
    alert_record = {
        "case_id": case_id,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "message": message,
        "id": len(history),
    }
    history.insert(0, alert_record)
    # Mantener últimas 50 alertas
    st.session_state.alert_history = history[:50]
    return st.session_state.alert_history


def get_alert_history() -> List[Dict[str, Any]]:
    """Obtiene historial completo de alertas."""
    import streamlit as st

    return st.session_state.get("alert_history", [])


def get_case_alerts(case_id: str) -> List[Dict[str, Any]]:
    """Obtiene alertas de un caso específico."""
    import streamlit as st

    history = st.session_state.get("alert_history", [])
    return [alert for alert in history if alert.get("case_id") == case_id]


def get_alerts_by_timeframe(hours: int = 24) -> List[Dict[str, Any]]:
    """Obtiene alertas de las últimas N horas."""
    import streamlit as st
    from datetime import datetime, timedelta

    history = st.session_state.get("alert_history", [])
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    result = []
    for alert in history:
        try:
            alert_time = datetime.strptime(alert.get("timestamp", ""), "%Y-%m-%d %H:%M:%S UTC")
            if alert_time >= cutoff:
                result.append(alert)
        except Exception:
            pass

    return result


def get_alert_stats() -> Dict[str, Any]:
    """Obtiene estadísticas de alertas."""
    import streamlit as st

    history = st.session_state.get("alert_history", [])
    case_counts = {}

    for alert in history:
        case_id = alert.get("case_id", "Unknown")
        case_counts[case_id] = case_counts.get(case_id, 0) + 1

    return {
        "total_alerts": len(history),
        "unique_cases": len(case_counts),
        "by_case": case_counts,
    }
