"""Módulos avanzados para inteligencia de casos crypto y rastreo multi-caso operativo."""

from .alert_history import (
    add_alert_history,
    get_alert_history,
    get_case_alerts,
    get_alerts_by_timeframe,
    get_alert_stats,
)
from .case_loader import (
    load_cases_from_json,
    save_cases_to_json,
    get_case_payload,
    batch_load_cases,
)
from .graph_visualizer import build_case_graph, build_multi_case_graph
from .neo4j_integration import (
    get_neo4j_driver,
    sync_case_to_neo4j,
    search_neo4j,
    search_wallet_in_neo4j,
    get_case_connections,
)
from .risk_scoring import (
    compute_risk_score,
    compute_risk_for_cases,
    get_risk_label,
    get_risk_color,
    get_risk_summary,
)
from .search_engine import search_cases, search_by_wallet_or_hash, search_all

__all__ = [
    # Alert History
    "add_alert_history",
    "get_alert_history",
    "get_case_alerts",
    "get_alerts_by_timeframe",
    "get_alert_stats",
    # Case Loader
    "load_cases_from_json",
    "save_cases_to_json",
    "get_case_payload",
    "batch_load_cases",
    # Graph Visualizer
    "build_case_graph",
    "build_multi_case_graph",
    # Neo4j Integration
    "get_neo4j_driver",
    "sync_case_to_neo4j",
    "search_neo4j",
    "search_wallet_in_neo4j",
    "get_case_connections",
    # Risk Scoring
    "compute_risk_score",
    "compute_risk_for_cases",
    "get_risk_label",
    "get_risk_color",
    "get_risk_summary",
    # Search Engine
    "search_cases",
    "search_by_wallet_or_hash",
    "search_all",
]
