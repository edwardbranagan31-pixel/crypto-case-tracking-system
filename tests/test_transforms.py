from unittest import mock

import pytest

from modules import transforms
from modules.entities import Entity, EntityGraph, case_to_graph

CASE = {"title": "T", "victim": "Ann", "wallets": {"a": "0xAbC0000000000000000000000000000000000001"},
        "cex_endpoints": [{"exchange": "Binance", "address": "0xdef"}]}


def test_entity_validation_and_normalization():
    assert Entity("domain", " Example.COM ").value == "example.com"
    with pytest.raises(ValueError):
        Entity("bogus", "x")
    with pytest.raises(ValueError):
        Entity("wallet", " ")


def test_case_migration():
    g = case_to_graph("C1", CASE)
    types = {k[0] for k in g.entities}
    assert {"case", "person", "wallet", "exchange"} <= types
    assert CASE["wallets"]["a"] == "0xAbC0000000000000000000000000000000000001"


def test_transactions_transform_mocked():
    fake = [{"network": "Ethereum", "transactions": [{"transaction": "0x1", "direction": "Outgoing"}], "tokens": []}]
    g = EntityGraph()
    w = Entity("wallet", CASE["wallets"]["a"])
    with mock.patch.object(transforms, "_check", return_value=fake):
        res = transforms.run_transform("address_to_transactions", w, g)
    assert res == {"status": "ok", "added": 1}
    assert ("transaction", "0x1") in g.entities


def test_error_handling_and_toggle(monkeypatch):
    import requests
    g = EntityGraph()
    w = Entity("wallet", "abc")
    with mock.patch.object(transforms, "_check", side_effect=requests.RequestException("boom")):
        assert transforms.run_transform("address_to_tokens", w, g)["status"] in ("error", "ok")
    with mock.patch.object(transforms, "_check", side_effect=requests.RequestException("boom")):
        assert transforms.run_transform("address_to_transactions", w, g)["status"] == "error"
    monkeypatch.setenv("TRANSFORMS_DISABLED", "address_to_transactions")
    assert transforms.run_transform("address_to_transactions", w, g)["status"] == "disabled"
    assert transforms.run_transform("nope", w, g)["status"] == "error"
    assert transforms.run_transform("domain_to_dns", w, g)["status"] == "error"


def test_cases_and_exchange_transforms():
    ctx = {"cases": {"C1": CASE}}
    g = EntityGraph()
    assert transforms.run_transform("address_to_cases", Entity("wallet", "0xdef"), g, ctx)["added"] == 1
    g2 = EntityGraph()
    assert transforms.run_transform("exchange_to_addresses", Entity("exchange", "Binance"), g2, ctx)["added"] == 1


def test_available_transforms():
    names = {t.name for t in transforms.available_transforms(Entity("domain", "a.com"))}
    assert names == {"domain_to_dns", "domain_to_whois"}
