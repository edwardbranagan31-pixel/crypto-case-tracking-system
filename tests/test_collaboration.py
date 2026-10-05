from unittest import mock

from modules.collaboration import (can_access_case, graph_to_csv, graph_to_json, graph_to_pdf, read_audit,
                                   record_audit, sync_graph_to_neo4j)
from modules.entities import Entity, EntityGraph


def make_graph():
    g = EntityGraph()
    g.link(Entity("case", "C1"), Entity("wallet", "=cmd(1)"), "wallet")
    return g


def test_audit_roundtrip(tmp_path):
    p = tmp_path / "a.jsonl"
    assert record_audit("ann", "transform", "C1", "x", p) and record_audit("bob", "save", "C2", path=p)
    assert [e["user"] for e in read_audit("C1", p)] == ["ann"]
    assert len(read_audit(path=p)) == 2 and read_audit(path=tmp_path / "none") == []


def test_access():
    assert can_access_case("x", {}, True)
    assert can_access_case("ann", {"allowed_users": ["ann"]}, True)
    assert not can_access_case("bob", {"allowed_users": ["ann"]}, True)
    assert can_access_case("bob", {"allowed_users": ["ann"]}, False)


def test_exports():
    g = make_graph()
    assert "'=cmd(1)" in graph_to_csv(g) and '"entities"' in graph_to_json(g)
    pdf = graph_to_pdf("C1", g)
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")


def test_neo4j_sync():
    assert sync_graph_to_neo4j(None, "C1", make_graph())["status"] == "skipped"
    driver = mock.MagicMock()
    res = sync_graph_to_neo4j(driver, "C1", make_graph())
    assert res == {"status": "success", "entities": 2, "links": 1}
