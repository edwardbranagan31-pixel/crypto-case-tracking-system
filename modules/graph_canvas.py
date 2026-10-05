from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from modules.entities import ENTITY_TYPES, Entity, EntityGraph

TYPE_COLORS = {
    "wallet": "#1f77b4", "exchange": "#ff7f0e", "transaction": "#7f7f7f", "person": "#d62728",
    "domain": "#2ca02c", "url": "#17becf", "email": "#9467bd", "phone": "#8c564b", "case": "#e377c2",
}
LAYOUTS = ("organic", "hierarchical", "circular")


def node_id(key: Tuple[str, str]) -> str:
    return f"{key[0]}:{key[1]}"


def parse_node_id(value: str) -> Tuple[str, str] | None:
    kind, _, rest = (value or "").partition(":")
    return (kind, rest) if kind in ENTITY_TYPES and rest else None


def _label(entity: Entity) -> str:
    text = str(entity.properties.get("label") or entity.properties.get("title") or entity.value)
    value = entity.value if len(entity.value) <= 14 else entity.value[:6] + "…" + entity.value[-4:]
    return f"{text}\n{value}" if text != entity.value else value


def graph_to_canvas(graph: EntityGraph, visible_types: Iterable[str] | None = None) -> Dict[str, List[Dict[str, Any]]]:
    """Plain-dict nodes/edges, coloured by entity type, optionally filtered by type."""
    allowed = set(visible_types) if visible_types is not None else set(ENTITY_TYPES)
    nodes = [
        {"id": node_id(e.key), "label": _label(e), "color": TYPE_COLORS.get(e.type, "#999999"),
         "title": f"{e.type}: {e.value}\nsource: {e.source}", "group": e.type}
        for e in graph.entities.values() if e.type in allowed
    ]
    ids = {n["id"] for n in nodes}
    edges = [
        {"source": node_id(l.source), "target": node_id(l.target), "label": l.label}
        for l in graph.links if node_id(l.source) in ids and node_id(l.target) in ids
    ]
    return {"nodes": nodes, "edges": edges}


def layout_options(layout: str) -> Dict[str, Any]:
    """Layout settings for the canvas: organic (physics), hierarchical or circular."""
    if layout not in LAYOUTS:
        layout = "organic"
    return {"hierarchical": layout == "hierarchical", "physics": layout == "organic",
            "circular": layout == "circular"}


def circular_positions(nodes: List[Dict[str, Any]], radius: float = 300.0) -> Dict[str, Tuple[float, float]]:
    import math
    count = max(len(nodes), 1)
    return {n["id"]: (radius * math.cos(2 * math.pi * i / count), radius * math.sin(2 * math.pi * i / count))
            for i, n in enumerate(nodes)}


def graphs_dir() -> Path:
    return Path(os.getenv("GRAPHS_DIR", Path(__file__).resolve().parent.parent / "graphs"))


def _graph_path(case_id: str, base: Path | None = None) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", case_id).lstrip(".") or "case"
    return (base or graphs_dir()) / f"{safe}.json"


def save_graph(case_id: str, graph: EntityGraph, base: Path | None = None) -> bool:
    path = _graph_path(case_id, base)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(graph.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        return False
    return True


def load_graph(case_id: str, base: Path | None = None) -> EntityGraph | None:
    path = _graph_path(case_id, base)
    try:
        return EntityGraph.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None
