from __future__ import annotations

import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List
from urllib.parse import quote

import requests


_BITCOIN_BASE58 = re.compile(r"^[13][1-9A-HJ-NP-Za-km-z]{25,34}$")
_BITCOIN_BECH32 = re.compile(r"^bc1[023456789ac-hj-np-z]{11,87}$", re.IGNORECASE)
_LITECOIN_ADDRESS = re.compile(
    r"^(?:[LM][1-9A-HJ-NP-Za-km-z]{26,33}|ltc1[023456789ac-hj-np-z]{11,87})$",
    re.IGNORECASE,
)
_ETHEREUM_ADDRESS = re.compile(r"^0x[a-fA-F0-9]{40}$")
_SOLANA_ADDRESS = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
_XRP_ADDRESS = re.compile(r"^r[1-9A-HJ-NP-Za-km-z]{24,34}$")
_TRON_ADDRESS = re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$")
_REQUEST_TIMEOUT = 8
_RECENT_TRANSACTION_LIMIT = 10
_LAMPORTS_PER_SOL = 1_000_000_000
_DROPS_PER_XRP = 1_000_000
_SUN_PER_TRX = 1_000_000


def detect_address_network(address: str) -> str | None:
    """Identify supported mainnet address formats."""
    if _BITCOIN_BASE58.fullmatch(address) or _BITCOIN_BECH32.fullmatch(address):
        return "Bitcoin"
    if _LITECOIN_ADDRESS.fullmatch(address):
        return "Litecoin"
    if _ETHEREUM_ADDRESS.fullmatch(address):
        return "Ethereum"
    if _SOLANA_ADDRESS.fullmatch(address) and _is_solana_address(address):
        return "Solana"
    if _XRP_ADDRESS.fullmatch(address):
        return "XRP Ledger"
    if _TRON_ADDRESS.fullmatch(address):
        return "TRON"
    return None


def _is_solana_address(address: str) -> bool:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    value = 0
    for character in address:
        value = value * 58 + alphabet.index(character)
    decoded_length = (value.bit_length() + 7) // 8
    leading_zero_bytes = len(address) - len(address.lstrip("1"))
    return decoded_length + leading_zero_bytes == 32


def _tron_hex_address(address: str) -> str | None:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    value = 0
    for character in address:
        value = value * 58 + alphabet.index(character)
    decoded_length = (value.bit_length() + 7) // 8
    decoded = b"\x00" * (len(address) - len(address.lstrip("1"))) + value.to_bytes(
        decoded_length, "big"
    )
    if len(decoded) != 25:
        return None
    payload, checksum = decoded[:-4], decoded[-4:]
    expected = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    if checksum != expected or payload[:1] != b"\x41":
        return None
    return payload.hex()


def _get_json(url: str) -> Any:
    response = requests.get(url, timeout=_REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _post_json(url: str, payload: Dict[str, Any]) -> Any:
    response = requests.post(url, json=payload, timeout=_REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if data.get("error"):
        raise ValueError(data["error"].get("message", data["error"]))
    return data


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


def _solana_check(address: str) -> Dict[str, Any]:
    rpc_url = "https://api.mainnet-beta.solana.com"

    def rpc(method: str, params: List[Any]) -> Any:
        response = _post_json(
            rpc_url,
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        )
        if response.get("error"):
            raise ValueError(response["error"].get("message", "Solana RPC error"))
        return response.get("result")

    balance = rpc("getBalance", [address, {"commitment": "confirmed"}])
    signatures = rpc(
        "getSignaturesForAddress",
        [address, {"limit": _RECENT_TRANSACTION_LIMIT, "commitment": "confirmed"}],
    ) or []
    transactions = []
    for signature in signatures:
        transaction = rpc(
            "getTransaction",
            [
                signature["signature"],
                {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0},
            ],
        )
        net_lamports = 0
        if transaction:
            keys = transaction.get("transaction", {}).get("message", {}).get("accountKeys", [])
            account_index = next(
                (
                    index
                    for index, key in enumerate(keys)
                    if (key.get("pubkey") if isinstance(key, dict) else key) == address
                ),
                None,
            )
            meta = transaction.get("meta") or {}
            if account_index is not None:
                pre_balances = meta.get("preBalances", [])
                post_balances = meta.get("postBalances", [])
                if account_index < len(pre_balances) and account_index < len(post_balances):
                    net_lamports = int(post_balances[account_index]) - int(
                        pre_balances[account_index]
                    )
        block_time = signature.get("blockTime")
        transactions.append(
            {
                "transaction": signature.get("signature", ""),
                "time": (
                    datetime.fromtimestamp(block_time, tz=timezone.utc).isoformat()
                    if block_time
                    else "Unknown"
                ),
                "direction": (
                    "Incoming"
                    if net_lamports > 0
                    else "Outgoing" if net_lamports < 0 else "Self/Unknown"
                ),
                "amount": _format_amount(abs(net_lamports), _LAMPORTS_PER_SOL, "SOL"),
                "status": "Failed" if signature.get("err") else "Confirmed",
            }
        )
    return {
        "network": "Solana",
        "balance": _format_amount(
            int((balance or {}).get("value", 0)), _LAMPORTS_PER_SOL, "SOL"
        ),
        "transaction_count": len(signatures),
        "transactions": transactions,
        "explorer": f"https://explorer.solana.com/address/{quote(address, safe='')}",
        "status": "ok",
    }


def _xrp_check(address: str) -> Dict[str, Any]:
    endpoint = "https://s1.ripple.com:51234/"
    info_response = _post_json(
        endpoint,
        {"method": "account_info", "params": [{"account": address, "ledger_index": "validated"}]},
    )
    account_info = info_response.get("result", {})
    if account_info.get("error") == "actNotFound":
        balance_drops = 0
        transaction_rows = []
        transaction_count = 0
    else:
        account_data = account_info.get("account_data", {})
        balance_drops = int(account_data.get("Balance", 0))
        history = _post_json(
            endpoint,
            {
                "method": "account_tx",
                "params": [
                    {
                        "account": address,
                        "ledger_index_min": -1,
                        "ledger_index_max": -1,
                        "limit": _RECENT_TRANSACTION_LIMIT,
                        "forward": False,
                    }
                ],
            },
        ).get("result", {})
        transaction_rows = history.get("transactions", [])
        transaction_count = int(history.get("transactions_count", len(transaction_rows)))

    transactions = []
    for row in transaction_rows[:_RECENT_TRANSACTION_LIMIT]:
        tx = row.get("tx", row.get("tx_json", {}))
        metadata = row.get("meta", row.get("metaData", {})) or {}
        raw_amount = tx.get("DeliverMax", tx.get("Amount", "0"))
        amount_drops = int(raw_amount) if isinstance(raw_amount, str) else 0
        account = tx.get("Account", "")
        direction = (
            "Outgoing"
            if account == address
            else "Incoming" if tx.get("Destination") == address else "Self/Unknown"
        )
        timestamp = tx.get("date")
        transactions.append(
            {
                "transaction": tx.get("hash", ""),
                "time": (
                    datetime.fromtimestamp(timestamp + 946684800, tz=timezone.utc).isoformat()
                    if timestamp
                    else "Unknown"
                ),
                "direction": direction,
                "amount": _format_amount(amount_drops, _DROPS_PER_XRP, "XRP"),
                "status": "Validated" if row.get("validated") else metadata.get("TransactionResult", "Unknown"),
            }
        )
    return {
        "network": "XRP Ledger",
        "balance": _format_amount(balance_drops, _DROPS_PER_XRP, "XRP"),
        "transaction_count": transaction_count,
        "transactions": transactions,
        "explorer": f"https://livenet.xrpl.org/accounts/{quote(address, safe='')}",
        "status": "ok",
    }


def _tron_check(address: str) -> Dict[str, Any]:
    encoded_address = quote(address, safe="")
    hex_address = _tron_hex_address(address)
    base_url = f"https://api.trongrid.io/v1/accounts/{encoded_address}"
    details = _get_json(base_url)
    transaction_data = _get_json(
        f"{base_url}/transactions?limit={_RECENT_TRANSACTION_LIMIT}&only_confirmed=true"
    )
    account = (details.get("data") or [{}])[0]
    rows = transaction_data.get("data", [])
    transactions = []
    for row in rows:
        contracts = (row.get("raw_data") or {}).get("contract") or []
        contract = (contracts[0].get("parameter") or {}).get("value") or {} if contracts else {}
        amount_sun = int(contract.get("amount", 0) or 0)
        owner_address = contract.get("owner_address", "")
        recipient = contract.get("to_address", "")
        direction = (
            "Outgoing"
            if owner_address.lower() in (address.lower(), hex_address)
            else "Incoming"
            if recipient.lower() in (address.lower(), hex_address)
            else "Self/Unknown"
        )
        timestamp = row.get("block_timestamp")
        transactions.append(
            {
                "transaction": row.get("txID", ""),
                "time": (
                    datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).isoformat()
                    if timestamp
                    else "Unknown"
                ),
                "direction": direction,
                "amount": _format_amount(abs(amount_sun), _SUN_PER_TRX, "TRX"),
                "status": "Confirmed",
            }
        )
    return {
        "network": "TRON",
        "balance": _format_amount(int(account.get("balance", 0)), _SUN_PER_TRX, "TRX"),
        "transaction_count": int(
            (transaction_data.get("meta") or {}).get("total", len(rows))
        ),
        "transactions": transactions[:_RECENT_TRANSACTION_LIMIT],
        "explorer": f"https://tronscan.org/#/address/{encoded_address}",
        "status": "ok",
    }


def _litecoin_check(address: str) -> Dict[str, Any]:
    encoded_address = quote(address, safe="")
    details = _get_json(
        f"https://api.blockcypher.com/v1/ltc/main/addrs/{encoded_address}/full"
        f"?limit={_RECENT_TRANSACTION_LIMIT}"
    )
    transactions = []
    for transaction in details.get("txs", [])[:_RECENT_TRANSACTION_LIMIT]:
        received = sum(
            int(output.get("value", 0))
            for output in transaction.get("outputs", [])
            if address in output.get("addresses", [])
        )
        spent = sum(
            int(tx_input.get("output_value", 0))
            for tx_input in transaction.get("inputs", [])
            if address in tx_input.get("addresses", [])
        )
        net_units = received - spent
        transactions.append(
            {
                "transaction": transaction.get("hash", ""),
                "time": transaction.get("confirmed") or "Unconfirmed",
                "direction": (
                    "Incoming"
                    if net_units > 0
                    else "Outgoing" if net_units < 0 else "Self/Unknown"
                ),
                "amount": _format_amount(abs(net_units), 100_000_000, "LTC"),
            }
        )
    return {
        "network": "Litecoin",
        "balance": _format_amount(int(details.get("balance", 0)), 100_000_000, "LTC"),
        "transaction_count": int(details.get("n_tx", 0)),
        "transactions": transactions,
        "explorer": f"https://blockchair.com/litecoin/address/{encoded_address}",
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
            "error": (
                "Supported networks: Bitcoin, Litecoin, Ethereum, Solana, "
                "XRP Ledger, and TRON mainnet."
            ),
            "transactions": [],
        }

    try:
        checkers = {
            "Bitcoin": _bitcoin_check,
            "Litecoin": _litecoin_check,
            "Ethereum": _ethereum_check,
            "Solana": _solana_check,
            "XRP Ledger": _xrp_check,
            "TRON": _tron_check,
        }
        result = checkers[network](address)
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
