from unittest import mock

from modules import transforms
from modules.analysis import (clusters, combined_risk, degree_centrality, find_hubs, find_mixer_candidates,
                              transaction_timeline)
from modules.entities import Entity, EntityGraph
from modules.machines import MACHINES, run_machine

CASES = {"C1": {"wallets": {"a": "0xaaa"}, "cex_endpoints": [{"exchange": "Binance", "address": "0xbbb"}]},
         "C2": {"wallets": {"b": "0xaaa"}}}


def fake_check(address):
    return [{"network": "Ethereum", "transactions": [
        {"transaction": f"0xt{i}", "direction": "Outgoing", "time": f"2024-01-0{i}T00:00:00Z"} for i in range(1, 6)],
        "tokens": []}]


def test_machine_runs_and_flags():
    g = EntityGraph()
    with mock.patch.object(transforms, "_check", side_effect=fake_check):
        res = run_machine("trace_wallet", Entity("wallet", "0xbbb"), g, {"cases": CASES})
    assert res["status"] == "ok" and res["added"] >= 6 and res["flagged"] == 1
    assert g.entities[("wallet", "0xbbb")].properties["flag"] == "exchange:Binance"


def test_machine_limits_and_unknown():
    g = EntityGraph()
    assert run_machine("nope", Entity("wallet", "0xaaa"), g)["status"] == "error"
    with mock.patch.object(transforms, "_check", side_effect=fake_check):
        res = run_machine(MACHINES["trace_wallet"], Entity("wallet", "0xaaa"), g, {"cases": CASES}, max_entities=3)
    assert len(g.entities) <= 8 and any("limit" in e for e in res["errors"])


def test_machine_error_is_collected():
    import requests
    g = EntityGraph()
    with mock.patch.object(transforms, "_check", side_effect=requests.RequestException("x")):
        res = run_machine("trace_wallet", Entity("wallet", "0xaaa"), g, {"cases": CASES})
    assert res["status"] == "ok" and res["errors"]


def build():
    g = EntityGraph()
    with mock.patch.object(transforms, "_check", side_effect=fake_check):
        run_machine("trace_wallet", Entity("wallet", "0xaaa"), g, {"cases": CASES})
    return g


def test_analysis():
    g = build()
    assert degree_centrality(g)[("wallet", "0xaaa")] > 0
    assert clusters(g)[0]
    assert find_hubs(g)[0]["value"] == "0xaaa"
    assert find_mixer_candidates(g)[0]["value"] == "0xaaa"
    risk = combined_risk(50, g)
    assert 50 < risk["score"] <= 100 and risk["findings"]
    tl = transaction_timeline(g)
    assert [r["transaction"] for r in tl][:2] == ["0xt1", "0xt2"]


def test_empty_graph():
    g = EntityGraph()
    assert degree_centrality(g) == {} and clusters(g) == [] and transaction_timeline(g) == []
    assert combined_risk(40, g) == {"score": 40.0, "points": 0.0, "findings": []}
