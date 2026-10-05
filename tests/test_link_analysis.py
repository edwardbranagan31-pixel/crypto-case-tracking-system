from modules.link_analysis import build_link_graph, find_linked_cases

CASES = {
    "A": {"wallets": {"w": "0xABC"}, "cex_endpoints": [{"exchange": "X", "address": "0xdef"}]},
    "B": {"wallets": {"w2": "0xabc"}, "cex_endpoints": []},
    "C": {"wallets": {"w3": "0x999"}},
}


def test_links_shared_wallet_case_insensitive():
    links = find_linked_cases(CASES, "A")
    assert [l["case_id"] for l in links] == ["B"]
    assert links[0]["link_strength"] == 1


def test_unknown_and_unlinked():
    assert find_linked_cases(CASES, "Z") == []
    assert find_linked_cases(CASES, "C") == []


def test_graph_contains_cases():
    assert '"B"' in build_link_graph(CASES, "A")
