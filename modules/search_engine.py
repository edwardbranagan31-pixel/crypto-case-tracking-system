from __future__ import annotations

from typing import Any, Dict, List


def search_cases(cases: Dict[str, Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """Busca casos por texto general (case_id, victim, title, police_report)."""
    text = (query or "").strip().lower()
    if not text:
        return []

    matches: List[Dict[str, Any]] = []
    for case_id, case in cases.items():
        haystack = " ".join(
            [
                case_id,
                case.get("title", ""),
                case.get("victim", ""),
                case.get("police_report", ""),
            ]
        ).lower()

        if text in haystack:
            matches.append({
                "case_id": case_id,
                "title": case.get("title", case_id),
                "victim": case.get("victim", ""),
                "match_type": "general",
            })

    return matches


def search_by_wallet_or_hash(cases: Dict[str, Dict[str, Any]], value: str) -> List[Dict[str, Any]]:
    """Busca casos por wallet, dirección, hash o exchange."""
    text = (value or "").strip().lower()
    if not text:
        return []

    results: List[Dict[str, Any]] = []
    found_cases = set()

    for case_id, case in cases.items():
        if case_id in found_cases:
            continue

        # Buscar en wallets
        wallet_values = [addr.lower() for addr in case.get("wallets", {}).values()]
        if any(text in w for w in wallet_values):
            results.append({
                "case_id": case_id,
                "title": case.get("title", case_id),
                "victim": case.get("victim", ""),
                "match_type": "wallet",
            })
            found_cases.add(case_id)
            continue

        # Buscar en CEX endpoints
        cex_values = [endpoint.get("address", "").lower() for endpoint in case.get("cex_endpoints", [])]
        if any(text in c for c in cex_values):
            results.append({
                "case_id": case_id,
                "title": case.get("title", case_id),
                "victim": case.get("victim", ""),
                "match_type": "cex_endpoint",
            })
            found_cases.add(case_id)
            continue

        # Buscar en exchanges
        exchanges = [endpoint.get("exchange", "").lower() for endpoint in case.get("cex_endpoints", [])]
        if any(text in ex for ex in exchanges):
            results.append({
                "case_id": case_id,
                "title": case.get("title", case_id),
                "victim": case.get("victim", ""),
                "match_type": "exchange",
            })
            found_cases.add(case_id)

    return results


def search_all(cases: Dict[str, Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """Búsqueda combinada: general + wallet."""
    general = search_cases(cases, query)
    wallet = search_by_wallet_or_hash(cases, query)

    # Combinar sin duplicados
    combined = {r["case_id"]: r for r in general + wallet}
    return list(combined.values())
