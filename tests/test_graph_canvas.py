from modules.entities import EntityGraph, case_to_graph
from modules.graph_canvas import (circular_positions, graph_to_canvas, layout_options, load_graph,
                                  parse_node_id, save_graph)

CASE = {"victim": "Ann", "wallets": {"a": "0xabc"}, "cex_endpoints": [{"exchange": "Binance", "address": "0xdef"}]}


def test_canvas_filter_and_colors():
    g = case_to_graph("C1", CASE)
    full = graph_to_canvas(g)
    assert len(full["nodes"]) == len(g.entities) and all(n["color"] for n in full["nodes"])
    only = graph_to_canvas(g, ["wallet"])
    assert {n["group"] for n in only["nodes"]} == {"wallet"} and only["edges"] == []


def test_node_id_roundtrip():
    assert parse_node_id("wallet:0xabc") == ("wallet", "0xabc")
    assert parse_node_id("bogus:x") is None and parse_node_id("") is None


def test_layouts():
    assert layout_options("hierarchical")["hierarchical"] and layout_options("x")["physics"]
    assert len(circular_positions([{"id": "a"}, {"id": "b"}])) == 2


def test_save_load(tmp_path):
    g = case_to_graph("C1", CASE)
    assert save_graph("../C1", g, tmp_path)
    assert list(tmp_path.iterdir())[0].parent == tmp_path
    loaded = load_graph("../C1", tmp_path)
    assert set(loaded.entities) == set(g.entities) and len(loaded.links) == len(g.links)
    assert load_graph("missing", tmp_path) is None
