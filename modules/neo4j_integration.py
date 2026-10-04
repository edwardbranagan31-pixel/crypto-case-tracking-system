from __future__ import annotations

from typing import Any, Dict, List, Optional


def get_neo4j_driver(uri: str, user: str, password: str):
    """Crea conexión a Neo4j AuraDB."""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        return driver
    except Exception:
        return None


def _to_float(value: Any, default: float = 0.0) -> float:
    """Convierte valores monetarios a float aceptando strings formateados."""
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        cleaned = str(value).replace("$", "").replace(",", "").replace(" USD", "")
        return float(cleaned)
    except (TypeError, ValueError):
        return default


def sync_case_to_neo4j(driver: Optional[Any], case_id: str, case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Sincroniza caso a Neo4j creando nodos Case, Wallet, Exchange y relaciones."""
    if driver is None:
        return {"status": "skipped", "reason": "No Neo4j driver available"}

    try:
        with driver.session() as session:
            # Crear nodo Case
            session.run(
                """
                MERGE (c:Case {case_id: $case_id})
                SET c.title = $title,
                    c.victim = $victim,
                    c.police_report = $police_report,
                    c.total_loss_usd = $total_loss_usd,
                    c.traced_usd = $traced_usd,
                    c.updated_at = timestamp()
                """,
                case_id=case_id,
                title=case_data.get("title", case_id),
                victim=case_data.get("victim", "Unknown"),
                police_report=case_data.get("police_report", case_id),
                total_loss_usd=_to_float(case_data.get("total_loss_usd", 0.0)),
                traced_usd=_to_float(case_data.get("traced_usd", 0.0)),
            )

            # Crear nodos Wallet y relaciones TRACKS
            for wallet_name, wallet_address in (case_data.get("wallets", {}) or {}).items():
                if not wallet_address:
                    continue
                session.run(
                    """
                    MERGE (w:Wallet {address: $address})
                    SET w.label = $wallet_name,
                        w.case_id = $case_id
                    MATCH (c:Case {case_id: $case_id})
                    MERGE (c)-[:TRACKS]->(w)
                    """,
                    address=wallet_address,
                    wallet_name=wallet_name,
                    case_id=case_id,
                )

            # Crear nodos Exchange y relaciones HAS_CEX_ENDPOINT
            for endpoint in case_data.get("cex_endpoints", []) or []:
                exchange_name = endpoint.get("exchange", "Unknown")
                address = endpoint.get("address")
                if not address:
                    continue
                session.run(
                    """
                    MERGE (e:Exchange {address: $address})
                    SET e.name = $exchange_name,
                        e.type = $exchange_type,
                        e.case_id = $case_id
                    MATCH (c:Case {case_id: $case_id})
                    MERGE (c)-[:HAS_CEX_ENDPOINT]->(e)
                    """,
                    address=address,
                    exchange_name=exchange_name,
                    exchange_type=endpoint.get("type", "Unknown"),
                    case_id=case_id,
                )

        return {"status": "ok", "case_id": case_id, "message": f"✅ Caso {case_id} sincronizado a Neo4j"}
    except Exception as e:
        return {"status": "error", "case_id": case_id, "message": f"❌ Error: {str(e)}"}


def search_neo4j(driver: Optional[Any], query: str) -> List[Dict[str, Any]]:
    """Busca en Neo4j por wallet, caso o dirección."""
    if driver is None or not query:
        return []

    q = query.strip()
    try:
        with driver.session() as session:
            # Buscar por case_id, victim o título
            results = session.run(
                """
                MATCH (c:Case)
                WHERE c.case_id CONTAINS $q OR c.victim CONTAINS $q OR c.title CONTAINS $q
                RETURN c.case_id AS case_id, c.title AS title, c.victim AS victim
                LIMIT 10
                """,
                q=q,
            )
            return [dict(record) for record in results]
    except Exception:
        return []


def search_wallet_in_neo4j(driver: Optional[Any], wallet_address: str) -> List[Dict[str, Any]]:
    """Busca una wallet en Neo4j y devuelve los casos asociados."""
    if driver is None or not wallet_address:
        return []

    try:
        with driver.session() as session:
            results = session.run(
                """
                MATCH (c:Case)-[:TRACKS]->(w:Wallet {address: $address})
                RETURN c.case_id AS case_id, c.title AS title, c.victim AS victim
                """,
                address=wallet_address,
            )
            return [dict(record) for record in results]
    except Exception:
        return []


def get_case_connections(driver: Optional[Any], case_id: str) -> Dict[str, Any]:
    """Obtiene todas las wallets y exchanges asociados a un caso en Neo4j."""
    if driver is None:
        return {"wallets": [], "exchanges": []}

    try:
        with driver.session() as session:
            wallets_result = session.run(
                "MATCH (c:Case {case_id: $case_id})-[:TRACKS]->(w:Wallet) RETURN w.address AS address, w.label AS label",
                case_id=case_id,
            )
            exchanges_result = session.run(
                "MATCH (c:Case {case_id: $case_id})-[:HAS_CEX_ENDPOINT]->(e:Exchange) RETURN e.address AS address, e.name AS name, e.type AS type",
                case_id=case_id,
            )
            return {
                "wallets": [dict(w) for w in wallets_result],
                "exchanges": [dict(e) for e in exchanges_result],
            }
    except Exception:
        return {"wallets": [], "exchanges": []}
