from __future__ import annotations

from typing import Any, Dict

import graphviz


def build_case_graph(case_data: Dict[str, Any]) -> graphviz.Digraph:
    """Construye grafo visual de flujo de fondos del caso."""
    graph = graphviz.Digraph(format="svg")
    graph.attr(rankdir="LR", size="10,6", overlap="false")
    graph.attr("node", fontname="Arial", fontsize="10")
    graph.attr("edge", fontname="Arial", fontsize="9")

    victim = case_data.get("victim", "Victim")
    wallets = case_data.get("wallets", {})
    endpoints = case_data.get("cex_endpoints", [])

    # Nodos principales
    graph.node(
        "V",
        f"VÍCTIMA\n{victim}",
        shape="ellipse",
        color="blue",
        style="filled",
        fillcolor="lightblue",
        penwidth="2",
    )
    graph.node(
        "S",
        "PLATAFORMA SCAM\n(Fraudulent App)",
        shape="box",
        color="red",
        style="filled",
        fillcolor="lightcoral",
        penwidth="2",
    )
    graph.node(
        "I",
        "WALLETS INTERMEDIARIAS\n(Layer 1 - Dispersión)",
        shape="box",
        color="orange",
        style="filled",
        fillcolor="lightyellow",
        penwidth="2",
    )
    graph.node(
        "A",
        "AGREGACIÓN CENTRAL\n(Commingling)",
        shape="box",
        color="purple",
        style="filled",
        fillcolor="plum",
        penwidth="2",
    )

    # Conexiones principales
    graph.edge("V", "S", label="Depósito Inicial", penwidth="2", color="red")
    graph.edge("S", "I", label="Split/Peel Chain", penwidth="2", color="orange")
    graph.edge("I", "A", label="Consolidación", penwidth="2", color="purple")

    # Nodos de wallets monitoreadas
    wallet_list = list((wallets or {}).items())
    for index, (wallet_name, wallet_address) in enumerate(wallet_list):
        if not wallet_address:
            continue
        node_id = f"W_{index}"
        label = f"{wallet_name}\n{wallet_address[:16]}..."
        graph.node(
            node_id,
            label,
            shape="box",
            color="darkorange",
            style="filled",
            fillcolor="wheat",
            penwidth="1.5",
        )
        graph.edge("A", node_id, label="Monitoreado", style="dashed", color="orange")

    # Nodos de CEX endpoints (destinos finales)
    endpoint_list = endpoints or []
    for idx, endpoint in enumerate(endpoint_list):
        node_id = f"CEX_{idx}"
        exchange_name = endpoint.get("exchange", "Exchange")
        address = endpoint.get("address", "")
        exchange_type = endpoint.get("type", "")

        if not address:
            continue

        label = f"{exchange_name}\n({exchange_type})\n{address[:16]}..."
        graph.node(
            node_id,
            label,
            shape="doubleoctagon",
            color="green",
            style="filled",
            fillcolor="lightgreen",
            penwidth="2",
        )
        graph.edge("A", node_id, label="Destino CEX", penwidth="2", color="green")

    return graph


def build_multi_case_graph(cases: Dict[str, Dict[str, Any]]) -> graphviz.Digraph:
    """Construye grafo de conexiones entre múltiples casos."""
    graph = graphviz.Digraph(format="svg")
    graph.attr(rankdir="TB", size="12,8")

    for case_id, case_data in cases.items():
        victim = case_data.get("victim", "Unknown")
        graph.node(
            case_id,
            f"{case_id}\n{victim}",
            shape="box",
            color="blue",
            style="filled",
            fillcolor="lightblue",
        )

    return graph
