from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Tuple

from modules.entities import EntityGraph

Key = Tuple[str, str]


def _adjacency(graph: EntityGraph) -> Dict[Key, set]:
    adj: Dict[Key, set] = {k: set() for k in graph.entities}
    for l in graph.links:
        if l.source in adj and l.target in adj and l.source != l.target:
            adj[l.source].add(l.target)
            adj[l.target].add(l.source)
    return adj


def degree_centrality(graph: EntityGraph) -> Dict[Key, float]:
    adj = _adjacency(graph)
    n = len(adj)
    if n < 2:
        return {k: 0.0 for k in adj}
    return {k: len(v) / (n - 1) for k, v in adj.items()}


def clusters(graph: EntityGraph) -> List[List[Key]]:
    """Connected components, largest first."""
    adj = _adjacency(graph)
    seen: set = set()
    out: List[List[Key]] = []
    for start in sorted(adj):
        if start in seen:
            continue
        stack, comp = [start], []
        seen.add(start)
        while stack:
            node = stack.pop()
            comp.append(node)
            for nxt in adj[node]:
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        out.append(sorted(comp))
    return sorted(out, key=lambda c: (-len(c), c))


def find_hubs(graph: EntityGraph, min_degree: int = 4) -> List[Dict[str, Any]]:
    """Entities with many connections (potential aggregation points)."""
    adj = _adjacency(graph)
    hubs = [{"type": k[0], "value": k[1], "degree": len(v), "centrality": round(degree_centrality(graph)[k], 3)}
            for k, v in adj.items() if len(v) >= min_degree and k[0] != "case"]
    return sorted(hubs, key=lambda h: (-h["degree"], h["value"]))


def find_mixer_candidates(graph: EntityGraph, min_transactions: int = 5, min_cases: int = 2) -> List[Dict[str, Any]]:
    """Heuristic leads: wallets touching many transactions, or shared by several cases. Not proof of mixing."""
    adj = _adjacency(graph)
    out = []
    for key, neighbors in adj.items():
        if key[0] != "wallet":
            continue
        tx = sum(1 for n in neighbors if n[0] == "transaction")
        cases = sum(1 for n in neighbors if n[0] == "case")
        reasons = []
        if tx >= min_transactions:
            reasons.append(f"{tx} linked transactions")
        if cases >= min_cases:
            reasons.append(f"shared by {cases} cases")
        if reasons:
            out.append({"value": key[1], "reasons": reasons, "score": tx + 3 * cases})
    return sorted(out, key=lambda r: (-r["score"], r["value"]))


def graph_risk_findings(graph: EntityGraph) -> Dict[str, Any]:
    """Points to add on top of the case risk score (max 15) with explanations."""
    findings: List[str] = []
    points = 0.0
    flagged = [e for e in graph.entities.values() if str(e.properties.get("flag", "")).startswith("exchange:")]
    if flagged:
        points += min(len(flagged) * 3.0, 6.0)
        findings.append(f"{len(flagged)} wallet(s) match known exchange endpoints")
    mixers = find_mixer_candidates(graph)
    if mixers:
        points += min(len(mixers) * 3.0, 6.0)
        findings.append(f"{len(mixers)} possible mixer/aggregation wallet(s)")
    other_cases = sum(1 for e in graph.entities.values() if e.type == "case") - 1
    if other_cases > 0:
        points += min(other_cases * 1.5, 3.0)
        findings.append(f"linked to {other_cases} other case(s)")
    return {"points": round(points, 1), "findings": findings}


def combined_risk(base_score: float, graph: EntityGraph) -> Dict[str, Any]:
    extra = graph_risk_findings(graph)
    return {"score": round(min(base_score + extra["points"], 100.0), 1), **extra}


def _parse_time(value: Any):
    text = str(value or "").replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def transaction_timeline(graph: EntityGraph) -> List[Dict[str, Any]]:
    """Transactions with a parseable time, oldest first (undated ones are excluded)."""
    rows = []
    for e in graph.entities.values():
        if e.type != "transaction":
            continue
        when = _parse_time(e.properties.get("time"))
        if when is None:
            continue
        rows.append({"time": when.isoformat(), "transaction": e.value, "network": e.properties.get("network"),
                     "amount": e.properties.get("amount"), "_sort": when.replace(tzinfo=None) if when.tzinfo is None else when.astimezone().replace(tzinfo=None)})
    rows.sort(key=lambda r: (r["_sort"], r["transaction"]))
    for r in rows:
        r.pop("_sort")
    return rows
