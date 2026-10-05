from __future__ import annotations

import os
import socket
import threading
import time
from typing import Any, Callable, Dict, List, Tuple

import requests

from modules import onchain
from modules.entities import Entity, EntityGraph
from modules.link_analysis import find_linked_cases

# A transform returns (new_entity, link_label) pairs.
TransformFn = Callable[[Entity, Dict[str, Any]], List[Tuple[Entity, str]]]


class RateLimiter:
    def __init__(self, min_interval: float) -> None:
        self.min_interval = min_interval
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            delay = self._last + self.min_interval - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()


class Transform:
    def __init__(self, name: str, input_types: Tuple[str, ...], func: TransformFn,
                 description: str = "", min_interval: float = 0.0) -> None:
        self.name, self.input_types, self.func = name, input_types, func
        self.description = description
        self.limiter = RateLimiter(min_interval)

    @property
    def enabled(self) -> bool:
        """Disable with env TRANSFORMS_DISABLED=name1,name2."""
        disabled = {n.strip() for n in os.getenv("TRANSFORMS_DISABLED", "").split(",")}
        return self.name not in disabled


_REGISTRY: Dict[str, Transform] = {}


def register(name: str, input_types: Tuple[str, ...], description: str = "", min_interval: float = 0.0):
    def decorator(func: TransformFn) -> TransformFn:
        _REGISTRY[name] = Transform(name, input_types, func, description, min_interval)
        return func
    return decorator


def available_transforms(entity: Entity) -> List[Transform]:
    return [t for t in _REGISTRY.values() if entity.type in t.input_types and t.enabled]


def run_transform(name: str, entity: Entity, graph: EntityGraph,
                  context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Run a transform, merge results into graph. Never raises; errors are returned."""
    transform = _REGISTRY.get(name)
    if transform is None:
        return {"status": "error", "error": f"Unknown transform: {name}", "added": 0}
    if not transform.enabled:
        return {"status": "disabled", "error": f"Transform {name} is disabled", "added": 0}
    if entity.type not in transform.input_types:
        return {"status": "error", "error": f"{name} does not accept {entity.type}", "added": 0}
    transform.limiter.wait()
    try:
        results = transform.func(entity, context or {})
    except (requests.RequestException, ValueError, TypeError, AttributeError, KeyError, OSError) as error:
        return {"status": "error", "error": f"{name} failed: {error}", "added": 0}
    graph.add(entity)
    before = len(graph.entities)
    for new_entity, label in results:
        graph.link(entity, new_entity, label)
    return {"status": "ok", "added": len(graph.entities) - before}


def _check(address: str) -> List[Dict[str, Any]]:
    if onchain.detect_address_network(address) == "Ethereum":
        return [onchain._evm_check(address, n) for n in onchain._EVM_NETWORKS]
    return [onchain.check_address_activity(address)]


@register("address_to_transactions", ("wallet",),
          "Recent transactions of an address from public explorers", min_interval=0.5)
def address_to_transactions(entity: Entity, context: Dict[str, Any]):
    out = []
    for result in _check(entity.value):
        for tx in result.get("transactions", []) or []:
            tx_hash = tx.get("transaction")
            if tx_hash:
                out.append((Entity("transaction", tx_hash,
                                   {"network": result.get("network"), "time": tx.get("time"),
                                    "amount": tx.get("amount")}, "explorer"),
                            tx.get("direction", "tx")))
    return out


@register("address_to_tokens", ("wallet",),
          "Token balances across supported EVM chains", min_interval=0.5)
def address_to_tokens(entity: Entity, context: Dict[str, Any]):
    if onchain.detect_address_network(entity.value) != "Ethereum":
        return []
    out = []
    for result in _check(entity.value):
        for token in result.get("tokens", []) or []:
            if token.get("contract"):
                out.append((Entity("wallet", token["contract"],
                                   {"label": f"{token['symbol']} token contract",
                                    "network": result.get("network"), "balance": token["balance"]},
                                   "explorer"), f"holds {token['symbol']}"))
    return out


@register("address_to_cases", ("wallet", "exchange"), "Other cases sharing this entity")
def address_to_cases(entity: Entity, context: Dict[str, Any]):
    cases = context.get("cases") or {}
    out = []
    for case_id, case in cases.items():
        probe = {"wallets": {"x": entity.value}, "cex_endpoints": [{"address": entity.value}]}
        tmp = {"_probe": probe, case_id: case}
        if find_linked_cases(tmp, "_probe") or (
            entity.type == "exchange"
            and any(str(e.get("exchange", "")).lower() == entity.value for e in case.get("cex_endpoints", []))
        ):
            out.append((Entity("case", case_id, {"title": case.get("title", case_id)}, "cases"), "appears in"))
    return out


@register("exchange_to_addresses", ("exchange",), "Known deposit addresses of an exchange in loaded cases")
def exchange_to_addresses(entity: Entity, context: Dict[str, Any]):
    out = []
    for case in (context.get("cases") or {}).values():
        for endpoint in case.get("cex_endpoints", []) or []:
            if str(endpoint.get("exchange", "")).strip().lower() == entity.value and endpoint.get("address"):
                out.append((Entity("wallet", endpoint["address"], {"label": "deposit address"}, "cases"),
                            "deposit address"))
    return out


@register("domain_to_dns", ("domain",), "Resolve A/AAAA records", min_interval=0.2)
def domain_to_dns(entity: Entity, context: Dict[str, Any]):
    infos = socket.getaddrinfo(entity.value, None)
    ips = sorted({info[4][0] for info in infos})
    return [(Entity("url", f"ip:{ip}", {"ip": ip}, "dns"), "resolves to") for ip in ips]


@register("domain_to_whois", ("domain",), "RDAP registration data", min_interval=1.0)
def domain_to_whois(entity: Entity, context: Dict[str, Any]):
    response = requests.get(f"https://rdap.org/domain/{entity.value}", timeout=8)
    response.raise_for_status()
    data = response.json()
    out = []
    for ent in data.get("entities", []):
        for item in (ent.get("vcardArray") or [None, []])[1]:
            if item and item[0] == "email" and item[3]:
                out.append((Entity("email", str(item[3]), {"roles": ent.get("roles", [])}, "rdap"),
                            "registrant contact"))
    return out
