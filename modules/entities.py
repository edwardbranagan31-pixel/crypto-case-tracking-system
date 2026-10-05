from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

ENTITY_TYPES = (
    "wallet", "exchange", "transaction", "person", "domain", "url", "email", "phone", "case",
)


def normalize_value(entity_type: str, value: str) -> str:
    text = str(value or "").strip()
    if entity_type in ("domain", "email", "exchange"):
        return text.lower()
    if entity_type == "wallet" and text.lower().startswith("0x"):
        return text.lower()
    if entity_type == "transaction" and text.lower().startswith("0x"):
        return text.lower()
    if entity_type == "phone":
        return "".join(ch for ch in text if ch.isdigit() or ch == "+")
    return text


@dataclass
class Entity:
    type: str
    value: str
    properties: Dict[str, Any] = field(default_factory=dict)
    source: str = "manual"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if self.type not in ENTITY_TYPES:
            raise ValueError(f"Unknown entity type: {self.type}")
        self.value = normalize_value(self.type, self.value)
        if not self.value:
            raise ValueError("Entity value cannot be empty")

    @property
    def key(self) -> Tuple[str, str]:
        return (self.type, self.value)

    def to_dict(self) -> Dict[str, Any]:
        return {"type": self.type, "value": self.value, "properties": self.properties,
                "source": self.source, "timestamp": self.timestamp}


@dataclass
class Link:
    source: Tuple[str, str]
    target: Tuple[str, str]
    label: str = ""


class EntityGraph:
    """Deduplicating collection of entities and links."""

    def __init__(self) -> None:
        self.entities: Dict[Tuple[str, str], Entity] = {}
        self.links: List[Link] = []

    def add(self, entity: Entity) -> Entity:
        return self.entities.setdefault(entity.key, entity)

    def link(self, a: Entity, b: Entity, label: str = "") -> None:
        a, b = self.add(a), self.add(b)
        if not any(l.source == a.key and l.target == b.key and l.label == label for l in self.links):
            self.links.append(Link(a.key, b.key, label))

    def neighbors(self, entity: Entity) -> List[Entity]:
        out = []
        for l in self.links:
            if l.source == entity.key and l.target in self.entities:
                out.append(self.entities[l.target])
            elif l.target == entity.key and l.source in self.entities:
                out.append(self.entities[l.source])
        return out

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities.values()],
            "links": [{"source": list(l.source), "target": list(l.target), "label": l.label} for l in self.links],
        }


def case_to_graph(case_id: str, case: Dict[str, Any]) -> EntityGraph:
    """Read-only migration of a case record into the entity model (cases.json is unchanged)."""
    graph = EntityGraph()
    case_entity = Entity("case", case_id, {"title": case.get("title", case_id),
                                           "total_loss_usd": case.get("total_loss_usd", 0)}, "case")
    graph.add(case_entity)
    if case.get("victim"):
        graph.link(case_entity, Entity("person", case["victim"], {"role": "victim"}, "case"), "victim")
    for label, addr in (case.get("wallets") or {}).items():
        if isinstance(addr, str) and addr.strip():
            graph.link(case_entity, Entity("wallet", addr, {"label": label}, "case"), "wallet")
    for endpoint in case.get("cex_endpoints") or []:
        exchange = str(endpoint.get("exchange", "")).strip()
        addr = str(endpoint.get("address", "")).strip()
        ex = Entity("exchange", exchange, {}, "case") if exchange else None
        if ex:
            graph.link(case_entity, ex, "exchange")
        if addr:
            wallet = Entity("wallet", addr, {"label": f"{exchange or 'CEX'} endpoint"}, "case")
            graph.link(ex or case_entity, wallet, "deposit address")
    return graph
