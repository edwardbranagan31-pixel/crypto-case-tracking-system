from __future__ import annotations

from typing import Any, Dict, List


def _entities(case: Dict[str, Any]) -> Dict[str, str]:
    """Map normalized entity key -> label (wallet addresses and CEX endpoints)."""
    found: Dict[str, str] = {}
    for label, addr in (case.get("wallets") or {}).items():
        if isinstance(addr, str) and addr.strip():
            found[addr.strip().lower()] = f"wallet:{label}"
    for endpoint in case.get("cex_endpoints") or []:
        addr = str(endpoint.get("address", "")).strip().lower()
        if addr:
            found[addr] = f"cex:{endpoint.get('exchange', 'Unknown')}"
    return found


def find_linked_cases(cases: Dict[str, Dict[str, Any]], case_id: str) -> List[Dict[str, Any]]:
    """Pivot on shared addresses: return other cases sharing entities with case_id."""
    if case_id not in cases:
        return []
    base = _entities(cases[case_id])
    links: List[Dict[str, Any]] = []
    for other_id, other in cases.items():
        if other_id == case_id:
            continue
        other_entities = _entities(other)
        shared = sorted(set(base) & set(other_entities))
        if shared:
            links.append({
                "case_id": other_id,
                "title": other.get("title", other_id),
                "shared_entities": [{"address": a, "label": other_entities[a]} for a in shared],
                "link_strength": len(shared),
            })
    return sorted(links, key=lambda item: (-item["link_strength"], item["case_id"]))


def build_link_graph(cases: Dict[str, Dict[str, Any]], case_id: str) -> str:
    """Graphviz DOT of the case, shared entities and linked cases."""
    def esc(value: str) -> str:
        return str(value).replace("\\", "\\\\").replace('"', '\\"')

    lines = ["digraph G {", "rankdir=LR;", f'"{esc(case_id)}" [shape=box,style=filled,fillcolor=lightblue];']
    for link in find_linked_cases(cases, case_id):
        lines.append(f'"{esc(link["case_id"])}" [shape=box];')
        for ent in link["shared_entities"]:
            short = ent["address"][:10] + "…"
            lines.append(f'"{esc(ent["address"])}" [label="{esc(ent["label"])}\\n{esc(short)}",shape=ellipse];')
            lines.append(f'"{esc(case_id)}" -> "{esc(ent["address"])}";')
            lines.append(f'"{esc(link["case_id"])}" -> "{esc(ent["address"])}";')
    lines.append("}")
    return "\n".join(lines)
