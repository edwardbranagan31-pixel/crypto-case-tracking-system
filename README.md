# Crypto Case Tracking System

Streamlit application for organizing cryptocurrency fraud investigations, reviewing wallet activity, and preparing case evidence for follow-up. It supports local JSON case storage, optional Neo4j synchronization, and optional Telegram alerts.

## Features

- Case records for victims, police reports, estimated losses, fiat transfers, wallets, and exchange endpoints.
- Local persistence in `cases.json` (or the path configured by `CASES_FILE`); existing case IDs cannot be overwritten when creating a case.
- Address activity lookups for Bitcoin, Litecoin, Ethereum, BNB Smart Chain, Polygon, Solana, XRP Ledger, and TRON. EVM addresses are checked independently on Ethereum, BNB Smart Chain, and Polygon, including native and explorer-reported token balances.
- Case and wallet/exchange search, per-case risk scoring, fund-flow visualization, and JSON evidence export.
- Optional Neo4j case/wallet/exchange synchronization and Telegram notifications with in-session alert history.
- Optional environment-configured login.

Public blockchain explorers and RPC endpoints are queried without API keys. They may impose rate limits or return incomplete data; results are point-in-time leads, not proof of ownership or fraud. Address formats do not identify the blockchain, so supported EVM networks are checked separately.

## Requirements and local setup

Python 3.10 or later is required. Neo4j AuraDB and a Telegram bot are optional.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Open <http://localhost:8501>. The application seeds an example case on first run and saves newly created cases in `cases.json`. The file is ignored by Git. Set `CASES_FILE` to a durable mounted path when deploying to an environment with ephemeral filesystems.

## Link analysis (Maltego-style)

- `modules/entities.py`: typed entities (wallet, exchange, transaction, person, domain, url, email, phone, case) with normalized values, properties, source and timestamp. `case_to_graph` reads existing case records without changing `cases.json`.
- `modules/transforms.py`: transform registry. Each transform maps an entity to linked entities, with rate limiting and error handling; disable by name via `TRANSFORMS_DISABLED=name1,name2`. Built-ins: address to transactions, address to EVM tokens, address/exchange to cases, exchange to deposit addresses, domain to DNS/RDAP. Add new ones with the `@register` decorator.
- "Casos Vinculados" tab: cases sharing addresses.

Not yet implemented: interactive graph canvas, machines, graph analysis, Neo4j graph persistence, per-user audit and PDF/CSV export.

## Configuration

Set only the integrations you plan to use in `.env` or the deployment environment:

| Variable | Purpose |
| --- | --- |
| `AUTH_USERNAME`, `AUTH_PASSWORD` | Enable the built-in login when both are set. |
| `CASES_FILE` | Optional path for the case JSON file; defaults to `cases.json` in the application directory. |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Optional Neo4j connection and case synchronization. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Optional Telegram alerts. |

Copy `.env.example` for the variable names. Do not commit `.env` or real credentials. Authentication is disabled if either auth variable is absent, so configure both and a strong password before exposing the app.

## Deploying to Railway

The included `railway.json` starts Streamlit on port 8080. Connect the repository to a Railway service, configure the environment variables, and provide persistent storage for the path set in `CASES_FILE`; otherwise locally stored cases may be lost when the service is redeployed. Configure authentication before making the service publicly accessible. Neo4j and Telegram can be omitted if those integrations are not needed.

## Tests

Run the unit tests with:

```bash
python -m unittest discover -s tests -v
```

Tests cover authentication, case persistence and normalization, currency parsing, and on-chain address checking. Explorer requests are mocked, so the test suite does not require live network access.

## Project structure

```text
.
├── app.py
├── modules/
│   ├── __init__.py             # Authentication
│   ├── alert_history.py        # Session alert history
│   ├── case_loader.py          # JSON persistence and case payloads
│   ├── currency_utils.py       # Monetary value normalization
│   ├── graph_visualizer.py     # Fund-flow graphs
│   ├── neo4j_integration.py    # Optional graph database integration
│   ├── onchain.py              # Multi-chain address activity
│   ├── risk_scoring.py         # Case risk scoring
│   └── search_engine.py        # Case, wallet, and exchange search
├── .streamlit/
│   └── config.toml
├── tests/
│   ├── test_auth.py
│   ├── test_case_loader.py
│   ├── test_currency_utils.py
│   └── test_onchain.py
├── requirements.txt
├── DEPLOYMENT.md
├── TESTING.md
├── PROJECT_COMPLETION.md
├── railway.json
└── .env.example
```

The interface integrates search, risk scoring, fund-flow diagrams, session alert
history, and optional Neo4j synchronization. The diagram shows recorded wallets
and endpoints; it does not prove transaction flows. See [DEPLOYMENT.md](DEPLOYMENT.md)
for Railway setup and [TESTING.md](TESTING.md) for validation guidance.
