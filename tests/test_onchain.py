import unittest
from unittest.mock import Mock, patch

import requests

from modules.onchain import (
    check_address_activity,
    check_case_addresses,
    detect_address_network,
)


BITCOIN_ADDRESS = "185MZoHdBjjwngvtQge9pBfdpbLXtWEjwo"
ETHEREUM_ADDRESS = "0xB7C92987c942B1794Ee98e2065AD9a98A502C381"
SOLANA_ADDRESS = "So11111111111111111111111111111111111111112"
XRP_ADDRESS = "rHb9CJAWyB4rj91VRWn96DkukG4bwdtyTh"
TRON_ADDRESS = "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE"
LITECOIN_ADDRESS = "ltc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"


class OnchainTests(unittest.TestCase):
    def test_detects_supported_mainnet_addresses(self):
        self.assertEqual(detect_address_network(BITCOIN_ADDRESS), "Bitcoin")
        self.assertEqual(detect_address_network(LITECOIN_ADDRESS), "Litecoin")
        self.assertEqual(detect_address_network(ETHEREUM_ADDRESS), "Ethereum")
        self.assertEqual(detect_address_network(SOLANA_ADDRESS), "Solana")
        self.assertEqual(detect_address_network(XRP_ADDRESS), "XRP Ledger")
        self.assertEqual(detect_address_network(TRON_ADDRESS), "TRON")
        self.assertIsNone(detect_address_network("not-an-address"))

    def test_unsupported_address_does_not_call_explorer(self):
        with patch("modules.onchain.requests.get") as get:
            result = check_address_activity("not-an-address")

        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["address"], "not-an-address")
        get.assert_not_called()

    @patch(
        "modules.onchain.requests.get",
        side_effect=requests.Timeout("explorer timed out"),
    )
    def test_reports_explorer_failures_without_raising(self, get):
        result = check_address_activity(BITCOIN_ADDRESS)

        self.assertEqual(result["status"], "error")
        self.assertIn("explorer timed out", result["error"])
        get.assert_called_once()

    @patch("modules.onchain.requests.get")
    def test_checks_bitcoin_balance_and_transactions(self, get):
        details = Mock()
        details.json.return_value = {
            "chain_stats": {
                "funded_txo_sum": 250_000_000,
                "spent_txo_sum": 50_000_000,
                "tx_count": 3,
            }
        }
        details.raise_for_status.return_value = None
        transactions = Mock()
        transactions.json.return_value = [
            {
                "txid": "btc-tx",
                "status": {"confirmed": True, "block_time": 1234},
                "vin": [],
                "vout": [{"scriptpubkey_address": BITCOIN_ADDRESS, "value": 100_000_000}],
            }
        ]
        transactions.raise_for_status.return_value = None
        get.side_effect = [details, transactions]

        result = check_address_activity(BITCOIN_ADDRESS)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["balance"], "2.00000000 BTC")
        self.assertEqual(result["transactions"][0]["amount"], "1.00000000 BTC")
        self.assertEqual(result["transactions"][0]["direction"], "Incoming")
        self.assertEqual(get.call_count, 2)

    @patch("modules.onchain.requests.get")
    def test_checks_ethereum_balance_and_transactions(self, get):
        details = Mock()
        details.json.return_value = {
            "coin_balance": "2000000000000000000",
            "transactions_count": 4,
        }
        details.raise_for_status.return_value = None
        transactions = Mock()
        transactions.json.return_value = {
            "items": [
                {
                    "hash": "eth-tx",
                    "timestamp": "2026-10-04T00:00:00Z",
                    "from": {"hash": ETHEREUM_ADDRESS.lower()},
                    "value": "500000000000000000",
                }
            ]
        }
        transactions.raise_for_status.return_value = None
        get.side_effect = [details, transactions]

        result = check_address_activity(ETHEREUM_ADDRESS)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["balance"], "2.00000000 ETH")
        self.assertEqual(result["transactions"][0]["amount"], "0.50000000 ETH")
        self.assertEqual(result["transactions"][0]["direction"], "Outgoing")

    @patch("modules.onchain._post_json")
    def test_checks_solana_balance_and_recent_activity(self, post):
        post.side_effect = [
            {"result": {"value": 2_500_000_000}},
            {"result": [{"signature": "sol-tx", "blockTime": 1_700_000_000}]},
            {
                "result": {
                    "transaction": {
                        "message": {"accountKeys": [{"pubkey": SOLANA_ADDRESS}]}
                    },
                    "meta": {"preBalances": [1_000_000_000], "postBalances": [1_500_000_000]},
                }
            },
        ]

        result = check_address_activity(SOLANA_ADDRESS)

        self.assertEqual(result["network"], "Solana")
        self.assertEqual(result["balance"], "2.50000000 SOL")
        self.assertEqual(result["transactions"][0]["amount"], "0.50000000 SOL")

    @patch("modules.onchain._post_json")
    def test_checks_xrp_balance_and_payment(self, post):
        post.side_effect = [
            {"result": {"account_data": {"Balance": "2500000"}}},
            {
                "result": {
                    "transactions": [
                        {
                            "tx": {
                                "hash": "xrp-tx",
                                "Account": XRP_ADDRESS,
                                "Destination": "rDestination",
                                "Amount": "1000000",
                                "date": 800000000,
                            },
                            "meta": {"TransactionResult": "tesSUCCESS"},
                            "validated": True,
                        }
                    ],
                    "transactions_count": 1,
                }
            },
        ]

        result = check_address_activity(XRP_ADDRESS)

        self.assertEqual(result["balance"], "2.50000000 XRP")
        self.assertEqual(result["transactions"][0]["amount"], "1.00000000 XRP")
        self.assertEqual(result["transactions"][0]["direction"], "Outgoing")

    @patch("modules.onchain._get_json")
    def test_checks_tron_balance_and_activity(self, get):
        get.side_effect = [
            {"data": [{"balance": 3_000_000}]},
            {
                "data": [
                    {
                        "txID": "tron-tx",
                        "block_timestamp": 1_700_000_000_000,
                        "raw_data": {
                            "contract": [
                                {
                                    "parameter": {
                                        "value": {
                                            "owner_address": TRON_ADDRESS,
                                            "to_address": "TRecipient",
                                            "amount": 1_000_000,
                                        }
                                    }
                                }
                            ]
                        },
                    }
                ],
                "meta": {"total": 1},
            },
        ]

        result = check_address_activity(TRON_ADDRESS)

        self.assertEqual(result["balance"], "3.00000000 TRX")
        self.assertEqual(result["transactions"][0]["amount"], "1.00000000 TRX")
        self.assertEqual(result["transactions"][0]["direction"], "Outgoing")

    @patch("modules.onchain._get_json")
    def test_checks_litecoin_balance_and_activity(self, get):
        get.return_value = {
            "balance": 150_000_000,
            "n_tx": 2,
            "txs": [
                {
                    "hash": "ltc-tx",
                    "confirmed": "2026-10-04T00:00:00Z",
                    "inputs": [],
                    "outputs": [
                        {
                            "addresses": [LITECOIN_ADDRESS],
                            "value": 50_000_000,
                        }
                    ],
                }
            ],
        }

        result = check_address_activity(LITECOIN_ADDRESS)

        self.assertEqual(result["balance"], "1.50000000 LTC")
        self.assertEqual(result["transactions"][0]["amount"], "0.50000000 LTC")
        self.assertEqual(result["transactions"][0]["direction"], "Incoming")

    def test_checks_each_unique_wallet_and_endpoint_once(self):
        wallets = {"BTC": BITCOIN_ADDRESS, "duplicate": BITCOIN_ADDRESS}
        endpoints = [{"exchange": "CEX", "address": ETHEREUM_ADDRESS}]
        with patch(
            "modules.onchain.check_address_activity",
            side_effect=[
                {"status": "ok", "address": BITCOIN_ADDRESS},
                {"status": "ok", "address": ETHEREUM_ADDRESS},
            ],
        ) as check:
            results = check_case_addresses(wallets, endpoints)

        self.assertEqual(len(results), 2)
        self.assertEqual(check.call_count, 2)


if __name__ == "__main__":
    unittest.main()
