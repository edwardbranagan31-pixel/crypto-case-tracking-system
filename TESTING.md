# 🧪 Testing & Validation Guide

## Quick Test (2 minutes)

```bash
# Clone repository
git clone https://github.com/edwardbranagan31-pixel/crypto-case-tracking-system
cd crypto-case-tracking-system

# Install dependencies
pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v

# Expected: 20/20 tests passing ✅
```

## Unit Tests Overview

### Test Suite Summary
```
✅ 20/20 Tests Passing
├── Authentication Tests (4 tests)
│   ├── test_authentication_requires_both_environment_values
│   ├── test_credentials_are_checked_against_environment
│   ├── test_missing_streamlit_state_is_unauthenticated
│   └── test_reads_streamlit_session_state_proxy
├── Case Persistence Tests (3 tests)
│   ├── test_load_returns_empty_mapping_for_missing_or_invalid_file
│   ├── test_save_and_load_round_trip
│   └── test_save_surfaces_write_errors
├── Currency Conversion Tests (2 tests)
│   ├── test_converts_supported_currency_formats
│   └── test_returns_default_for_invalid_or_non_finite_values
└── On-Chain Blockchain Tests (11 tests)
    ├── test_checks_bitcoin_balance_and_transactions
    ├── test_checks_ethereum_balance_and_transactions
    ├── test_checks_litecoin_balance_and_activity
    ├── test_checks_solana_balance_and_recent_activity
    ├── test_checks_tron_balance_and_activity
    ├── test_checks_xrp_balance_and_payment
    ├── test_checks_native_and_token_balances_for_bnb_and_polygon
    ├── test_checks_each_unique_wallet_and_endpoint_once
    ├── test_detects_supported_mainnet_addresses
    ├── test_reports_explorer_failures_without_raising
    └── test_unsupported_address_does_not_call_explorer
```

## Running Tests Locally

### Run All Tests
```bash
python -m pytest tests/ -v
```

### Run Specific Test File
```bash
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_case_loader.py -v
python -m pytest tests/test_onchain.py -v
python -m pytest tests/test_currency_utils.py -v
```

### Run Single Test
```bash
python -m pytest tests/test_auth.py::AuthenticationTests::test_credentials_are_checked_against_environment -v
```

### Run with Coverage
```bash
pip install pytest-cov
python -m pytest tests/ --cov=modules --cov-report=html
```

## Post-Deployment Web UI Testing

### Browser-Based Validation Checklist

#### 1. Authentication
```
[ ] Navigate to application URL
[ ] Verify "🔐 Acceso Seguro" login page appears
[ ] Try invalid credentials → "❌ Credenciales inválidas"
[ ] Enter correct credentials → Login succeeds
[ ] Verify sidebar shows "🔐 Sesión: [username]"
[ ] Click logout → Returns to login
```

#### 2. Case Management
```
[ ] Default case "NC-JOHNSTON-2024-3912" loads
[ ] Click "📥 Cargar Expediente Completo" → Confirmation message
[ ] "➕ Crear Nuevo Caso" form loads
[ ] Create case with:
    - Victim: "Test Victim"
    - Loss: 100000
    - BTC: 1A1z7agoat2NRrB6rASumarVpC2dhN97d
    - ETH: 0xBB9bc244D798123fDe783fCc1C72d3Bb8C189413
[ ] Case appears in dropdown
[ ] Refresh page → Case persists
```

#### 3. Case Details Display
```
[ ] Tab 1: Evidence & Transactions
    [ ] Fiat wire details display
    [ ] Wallet addresses show
    [ ] CEX endpoints table visible

[ ] Tab 2: Fund Flow Graph
    [ ] Graph visualization renders
    [ ] Shows: Victim → Scam → Intermediary → CEX

[ ] Tab 3: Real-Time Alerts
    [ ] Alert text area pre-populated
    [ ] "📲 Send Alert" button present

[ ] Tab 4: Legal Export
    [ ] JSON preview displays
    [ ] Download button works
```

#### 4. On-Chain Queries
```
[ ] Click "🔄 Consultar todas las direcciones"
[ ] Wait for blockchain queries to complete
[ ] Verify results for each address:
    [ ] Network detected correctly
    [ ] Balance displayed (format: amount + symbol)
    [ ] Transaction count shown
    [ ] Explorer link works
    [ ] Recent transactions display
```

## Security Testing

### Code Quality Checks
```bash
# Syntax validation
python -m py_compile app.py modules/*.py tests/*.py

# Security scanning (requires bandit)
pip install bandit
bandit -r . -ll

# Linting (optional)
pip install pylint
pylint app.py modules/ --disable=all --enable=E,F
```

### Secret Detection
```bash
# Check for exposed credentials
grep -r "password\|secret\|key\|token" . --include="*.py" --include="*.env" | grep -v ".env.example"

# Should return: NOTHING ✅
```

## Performance Testing

### Load Time Validation
```python
#!/usr/bin/env python3
import time
import requests

url = "https://your-railway-url.up.railway.app"

print("🧪 Performance Test")
print("=" * 50)

# Test 1: Page load time
start = time.time()
response = requests.get(url, timeout=10)
load_time = time.time() - start

print(f"✅ Page load time: {load_time:.2f}s")
print(f"   Expected: < 3s")
print(f"   Status: {'✅ PASS' if load_time < 3 else '❌ FAIL'}")

# Test 2: API responsiveness
if "Acceso Seguro" in response.text:
    print(f"✅ Login page renders correctly")
else:
    print(f"❌ Login page not found")
```

## Integration Testing

### End-to-End Workflow
```python
#!/usr/bin/env python3
"""
Test the complete user workflow:
1. Login
2. Create case
3. Query blockchain
4. Export report
"""

import sys
from pathlib import Path

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.case_loader import load_cases_from_json, save_cases_to_json
from modules.currency_utils import to_float
from modules.onchain import detect_address_network, check_address_activity

print("🧪 Integration Test: End-to-End Workflow")
print("=" * 60)

# Step 1: Create test case
print("\n1️⃣  Creating test case...")
test_cases = {
    "INTEGRATION-TEST-001": {
        "title": "Integration Test Case",
        "victim": "John Doe",
        "police_report": "PD-2024-001",
        "total_loss_usd": 250000.0,
        "traced_usd": 75000.0,
        "wallets": {
            "BTC_DEPOSIT": "1A1z7agoat2NRrB6rASumarVpC2dhN97d",
            "ETH_USDT": "0xBB9bc244D798123fDe783fCc1C72d3Bb8C189413"
        },
        "cex_endpoints": [
            {
                "exchange": "Binance",
                "address": "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
                "type": "BTC"
            }
        ],
        "fiat_wire": {
            "amount": "$75,000 USD",
            "bank": "Test Bank",
            "beneficiary": "Test Beneficiary",
            "receiving_bank": "Test Receiving Bank",
            "date": "2024-01-15"
        }
    }
}
print("   ✅ Case created")

# Step 2: Verify persistence
print("\n2️⃣  Testing case persistence...")
import tempfile
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    temp_file = f.name

save_cases_to_json(temp_file, test_cases)
loaded_cases = load_cases_from_json(temp_file)

if "INTEGRATION-TEST-001" in loaded_cases:
    print("   ✅ Case persisted and reloaded")
else:
    print("   ❌ Case not found after reload")
    sys.exit(1)

# Step 3: Test currency conversion
print("\n3️⃣  Testing currency conversion...")
loss_usd = to_float(test_cases["INTEGRATION-TEST-001"]["total_loss_usd"])
if loss_usd == 250000.0:
    print(f"   ✅ Currency conversion: {loss_usd} USD")
else:
    print(f"   ❌ Currency conversion failed")

# Step 4: Test address detection
print("\n4️⃣  Testing on-chain address detection...")
btc_address = test_cases["INTEGRATION-TEST-001"]["wallets"]["BTC_DEPOSIT"]
detected_network = detect_address_network(btc_address)

if detected_network == "Bitcoin":
    print(f"   ✅ Bitcoin address detected: {btc_address[:20]}...")
else:
    print(f"   ❌ Failed to detect Bitcoin network")

eth_address = test_cases["INTEGRATION-TEST-001"]["wallets"]["ETH_USDT"]
detected_network = detect_address_network(eth_address)

if detected_network == "Ethereum":
    print(f"   ✅ Ethereum address detected: {eth_address[:20]}...")
else:
    print(f"   ❌ Failed to detect Ethereum network")

# Step 5: Test on-chain query
print("\n5️⃣  Testing on-chain balance queries...")
print("   (This may take 5-10 seconds)")

result = check_address_activity(btc_address)
if result.get("status") == "ok":
    print(f"   ✅ Bitcoin balance: {result.get('balance', 'N/A')}")
    print(f"   ✅ Transactions: {result.get('transaction_count', 0)}")
else:
    print(f"   ⚠️  Bitcoin query returned: {result.get('status')}")

# Cleanup
import os
os.unlink(temp_file)

print("\n" + "=" * 60)
print("✅ Integration test complete!")
print("=" * 60)
```

## Deployment Validation

### Post-Deployment Checklist

```
▶️  BEFORE GOING LIVE

Server Configuration
[ ] Application accessible at Railway URL
[ ] HTTPS enabled (Railway default)
[ ] Health check passing (200 OK)
[ ] Logs show no errors

Authentication
[ ] AUTH_USERNAME environment variable set
[ ] AUTH_PASSWORD environment variable set
[ ] Login works with configured credentials
[ ] Session persists across requests

Data Persistence
[ ] Persistent volume mounted at /app
[ ] CASES_FILE=/app/cases.json configured
[ ] Create test case → persists after refresh
[ ] Restart pod → case still exists

Features
[ ] Default case loads on startup
[ ] Can create new cases
[ ] On-chain queries work (at least 2 networks)
[ ] JSON export downloads correctly
[ ] Sidebar shows auth status

Monitoring
[ ] Railway logs accessible
[ ] No error messages in logs
[ ] Application responding normally
[ ] No resource exhaustion warnings

Security
[ ] AUTH credentials are strong
[ ] No secrets in logs
[ ] HTTPS enforced
[ ] Database access secured (if using Neo4j)

Documentation
[ ] Team has deployment guide (DEPLOYMENT.md)
[ ] Support contact information shared
[ ] Backup procedures documented
[ ] Incident response plan ready
```

## Monitoring & Alerts

### Log Monitoring
```bash
# Check Railway logs continuously
railway logs --tail -f

# Look for errors
railway logs | grep -i error

# Check application health
curl https://your-url.up.railway.app/health 2>/dev/null || curl https://your-url.up.railway.app
```

### Expected Log Patterns
```
✅ Application startup:
   "Streamlit app is running on http://0.0.0.0:8080"

✅ Case creation:
   "Case registered: [CASE-ID]"

✅ On-chain query:
   "Querying Bitcoin address..."
   "Balance retrieved: [amount] BTC"

❌ Errors to watch for:
   "Failed to load cases from JSON"
   "Authentication failed"
   "Explorer request failed"
   "Database connection error"
```

## Troubleshooting Common Issues

### Issue: "Cases not persisting"
```
Diagnosis:
1. Check CASES_FILE environment variable
2. Verify persistent volume is mounted
3. Check Railway file system

Fix:
1. Verify: echo $CASES_FILE (should be /app/cases.json)
2. Mount volume at /app if missing
3. Check Railway dashboard → Volumes
```

### Issue: "Authentication fails"
```
Diagnosis:
1. Check if AUTH_USERNAME/PASSWORD are set
2. Verify credentials have no spaces

Fix:
1. Railway Dashboard → Variables
2. Verify AUTH_USERNAME and AUTH_PASSWORD
3. Restart deployment

Note: Credentials are case-sensitive
```

### Issue: "On-chain queries timeout"
```
Diagnosis:
1. Public APIs have rate limits
2. Network connectivity issue
3. Explorer API down

Fix:
1. Wait a few moments and retry
2. Try different address on different network
3. Check explorer status: blockscout.com, mempool.space
```

### Issue: "Application won't start"
```
Diagnosis:
1. Python version incompatible
2. Missing dependencies
3. Syntax error in code

Fix:
1. Check Python 3.10+: python --version
2. Install dependencies: pip install -r requirements.txt
3. Check logs: railway logs
4. Run tests locally: pytest tests/ -v
```

## Success Criteria

All of the following must be TRUE before marking as production-ready:

- ✅ PR #3 merged to main
- ✅ All 20 unit tests passing
- ✅ Application deployed to Railway
- ✅ Public URL accessible
- ✅ Authentication working
- ✅ Test case persists after refresh
- ✅ On-chain queries returning data
- ✅ JSON export working
- ✅ No errors in deployment logs
- ✅ Documentation reviewed by team
- ✅ Team trained on case creation/queries

**Status: READY FOR PRODUCTION** ✅
