from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from modules.entities import Entity, EntityGraph
from modules.transforms import run_transform, _REGISTRY

MAX_ENTITIES = 500


@dataclass(frozen=True)
class Machine:
    name: str
    description: str
    transforms: Tuple[str, ...]
    hops: int = 1


MACHINES: Dict[str, Machine] = {
    "trace_wallet": Machine("trace_wallet", "Trace a wallet 3 hops (transactions, tokens, shared cases) and flag exchanges",
                            ("address_to_transactions", "address_to_tokens", "address_to_cases"), 3),
    "case_footprint": Machine("case_footprint", "Find other cases and deposit addresses related to an entity",
                              ("address_to_cases", "exchange_to_addresses"), 2),
    "domain_recon": Machine("domain_recon", "Resolve a domain and collect registrant contacts",
                            ("domain_to_dns", "domain_to_whois"), 1),
}


def flag_exchanges(graph: EntityGraph, cases: Dict[str, Dict[str, Any]]) -> int:
    """Mark wallets that match a known CEX endpoint address with properties['flag']='exchange:<name>'."""
    known = {}
    for case in (cases or {}).values():
        for endpoint in case.get("cex_endpoints", []) or []:
            addr = str(endpoint.get("address", "")).strip().lower()
            if addr:
                known[addr] = str(endpoint.get("exchange", "Unknown"))
    flagged = 0
    for entity in graph.entities.values():
        if entity.type == "wallet" and entity.value.lower() in known:
            entity.properties["flag"] = f"exchange:{known[entity.value.lower()]}"
            flagged += 1
    return flagged


def run_machine(machine: Machine | str, start: Entity, graph: EntityGraph,
                context: Dict[str, Any] | None = None, max_entities: int = MAX_ENTITIES) -> Dict[str, Any]:
    """Breadth-first chain of transforms from `start`, up to machine.hops; never raises."""
    if isinstance(machine, str):
        if machine not in MACHINES:
            return {"status": "error", "error": f"Unknown machine: {machine}", "added": 0, "errors": [], "steps": 0}
        machine = MACHINES[machine]
    context = context or {}
    graph.add(start)
    initial = len(graph.entities)
    frontier: List[Entity] = [graph.entities[start.key]]
    visited = {start.key}
    errors: List[str] = []
    steps = 0
    for _ in range(machine.hops):
        next_frontier: List[Entity] = []
        for entity in frontier:
            for name in machine.transforms:
                transform = _REGISTRY.get(name)
                if transform is None or entity.type not in transform.input_types:
                    continue
                if len(graph.entities) >= max_entities:
                    errors.append(f"Entity limit {max_entities} reached")
                    break
                steps += 1
                res = run_transform(name, entity, graph, context)
                if res["status"] != "ok":
                    errors.append(res["error"])
            for neighbor in graph.neighbors(entity):
                if neighbor.key not in visited:
                    visited.add(neighbor.key)
                    next_frontier.append(neighbor)
        frontier = next_frontier
        if not frontier or len(graph.entities) >= max_entities:
            break
    flagged = flag_exchanges(graph, context.get("cases") or {})
    return {"status": "ok", "added": len(graph.entities) - initial, "flagged": flagged,
            "errors": sorted(set(errors)), "steps": steps}
