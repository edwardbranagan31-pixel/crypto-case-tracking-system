from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List
from urllib.parse import quote

import requests


_BITCOIN_BASE58 = re.compile(r"^[13][1-9A-HJ-NP-Za-km-z]{25,34}$")
_BITCOIN_BECH32 = re.compile(r"^bc1[023456789ac-hj-np-z]{11,87}$", re.IGNORECASE)
_ETHEREUM_ADDRESS = re.compile(r"^0x[a-fA-F0-9]{40}$")
_REQUEST_TIMEOUT = 8
_RECENT_TRANSACTION_LIMIT = 10


def detect_address_network(address: str) -> str | None:
    """Identify supported Bitcoin mainnet and Ethereum addresses."""
    if _BITCOIN_BASE58.fullmatch(address) or _BITCOIN_BECH32.fullmatch(address):
        return "Bitcoin"
    if _ETHEREUM_ADDRESS.fullmatch(address):
        return "Ethereum"
    return None


def _get_json(url: str) -> Any:
    response = requests.get(url, timeout=_REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _format_amount(atomic_units: int, units_per_coin: int, symbol: str) -> str:
    amount = Decimal(atomic_units) / Decimal(units_per_coin)
    return f"{amount:.8f} {symbol}"


def _bitcoin_check(address: str) -> Dict[str, Any]:
    encoded_address = quote(address, safe="")
    details = _get_json(f"https://mempool.space/api/address/{encoded_address}")
    stats = details.get("chain_stats", {})
    funded = int(stats.get("funded_txo_sum", 0))
    spent = int(stats.get("spent_txo_sum", 0))
    transactions = _get_json(
        f"https://mempool.space/api/address/{encoded_address}/txs"
    )

    recent_transactions = []
    for transaction in transactions[:_RECENT_TRANSACTION_LIMIT]:
        inputs = sum(
            int(item.get("prevout", {}).get("value", 0))
            for item in transaction.get("vin", [])
            if item.get("prevout", {}).get("scriptpubkey_address") == address
        )
        outputs = sum(
            int(item.get("value", 0))
            for item in transaction.get("vout", [])
            if item.get("scriptpubkey_address") == address
        )
        net_satoshis = outputs - inputs
        status = transaction.get("status", {})
        block_time = status.get("block_time")
        recent_transactions.append(
            {
                "transaction": transaction.get("txid", ""),
                "time": (
                    datetime.fromtimestamp(block_time, tz=timezone.utc).isoformat()
                    if block_time
                    else "Pending"
                ),
                "direction": (
                    "Incoming"
                    if net_satoshis > 0
                    else "Outgoing" if net_satoshis < 0 else "Self/Unknown"
                ),
                "amount": _format_amount(abs(net_satoshis), 100_000_000, "BTC"),
            }
        )

    return {
        "network": "Bitcoin",
        "balance": _format_amount(funded - spent, 100_000_000, "BTC"),
        "transaction_count": int(stats.get("tx_count", 0)),
        "transactions": recent_transactions,
        "explorer": f"https://mempool.space/address/{encoded_address}",
        "status": "ok",
    }


def _ethereum_check(address: str) -> Dict[str, Any]:
    encoded_address = quote(address, safe="")
    base_url = f"https://eth.blockscout.com/api/v2/addresses/{encoded_address}"
    details = _get_json(base_url)
    transaction_data = _get_json(f"{base_url}/transactions")
    transactions = transaction_data.get("items", [])

    recent_transactions = []
    for transaction in transactions[:_RECENT_TRANSACTION_LIMIT]:
        amount_wei = int(transaction.get("value", "0") or 0)
        recent_transactions.append(
            {
                "transaction": transaction.get("hash", ""),
                "time": transaction.get("timestamp", "Unknown"),
                "direction": (
                    "Outgoing"
                    if str((transaction.get("from") or {}).get("hash", "")).lower()
                    == address.lower()
                    else "Incoming"
                ),
                "amount": _format_amount(amount_wei, 10**18, "ETH"),
            }
        )

    return {
        "network": "Ethereum",
        "balance": _format_amount(
            int(details.get("coin_balance") or 0), 10**18, "ETH"
        ),
        "transaction_count": int(details.get("transactions_count") or 0),
        "transactions": recent_transactions,
        "explorer": f"https://eth.blockscout.com/address/{encoded_address}",
        "status": "ok",
    }


def check_address_activity(address: str) -> Dict[str, Any]:
    """Fetch the current native-coin balance and recent transactions for an address."""
    network = detect_address_network(address)
    if network is None:
        return {
            "address": address,
            "network": "Unsupported",
            "status": "unsupported",
            "error": "Only Bitcoin mainnet and Ethereum addresses are supported.",
            "transactions": [],
        }

    try:
        result = _bitcoin_check(address) if network == "Bitcoin" else _ethereum_check(address)
        result["address"] = address
        return result
    except (requests.RequestException, ValueError, TypeError, AttributeError) as error:
        return {
            "address": address,
            "network": network,
            "status": "error",
            "error": f"Explorer request failed: {error}",
            "transactions": [],
        }


def check_case_addresses(
    wallets: Dict[str, Any], cex_endpoints: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Check all unique wallet and exchange endpoint addresses in a case."""
    addresses = []
    seen = set()
    for label, address in (wallets or {}).items():
        if isinstance(address, str) and address.strip():
            normalized_address = address.strip()
            network = detect_address_network(normalized_address)
            key = (
                network,
                normalized_address.lower() if network == "Ethereum" else normalized_address,
            )
            if key not in seen:
                addresses.append((label, normalized_address))
                seen.add(key)

    for endpoint in cex_endpoints or []:
        if not isinstance(endpoint, dict):
            continue
        address = endpoint.get("address")
        if isinstance(address, str) and address.strip():
            normalized_address = address.strip()
            network = detect_address_network(normalized_address)
            key = (
                network,
                normalized_address.lower() if network == "Ethereum" else normalized_address,
            )
            if key not in seen:
                label = endpoint.get("exchange", "CEX endpoint")
                addresses.append((label, normalized_address))
                seen.add(key)

    def check_labeled_address(item: tuple[str, str]) -> Dict[str, Any]:
        label, address = item
        result = check_address_activity(address)
        result["label"] = label
        return result

    if not addresses:
        return []
    with ThreadPoolExecutor(max_workers=min(5, len(addresses))) as executor:
        return list(executor.map(check_labeled_address, addresses))
