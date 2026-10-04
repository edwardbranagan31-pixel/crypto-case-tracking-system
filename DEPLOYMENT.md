# 🚀 Deployment Guide: Crypto Case Tracking System

## Quick Start (5 minutes)

### Prerequisites
- GitHub account with access to this repository
- Railway account (free tier available at https://railway.app)
- Basic terminal knowledge

### Deploy to Railway

```bash
# 1. Go to Railway Dashboard
# https://railway.app/dashboard

# 2. Create new project from GitHub
# Select: edwardbranagan31-pixel/crypto-case-tracking-system
# Click: "Deploy"

# 3. Configure Environment Variables
# In Railway Dashboard → [Project] → Variables, add:

CASES_FILE=/app/cases.json
AUTH_USERNAME=admin
AUTH_PASSWORD=your-strong-password-here

# Optional (for advanced features):
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password

TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-telegram-chat-id

# 4. Configure Persistent Volume
# In Railway Dashboard → [Project] → Settings → Volumes
# Mount: /app (size: 1GB)

# 5. Set Start Command
# In Railway Dashboard → [Project] → Settings → Deployment
# Start Command: streamlit run app.py --server.address 0.0.0.0 --server.port 8080

# 6. Deploy
# Click "Deploy" and wait 2-3 minutes

# 7. Get Public URL
# In Railway Dashboard → [Project] → Generate Domain
# Copy the URL and share with your team
```

## Features Deployed

✅ **Case Management**
- Create, load, and persist fraud investigation cases
- Automatic duplicate ID detection
- Local JSON storage with encryption support ready

✅ **On-Chain Analysis**
- Bitcoin, Ethereum, Solana, TRON, Litecoin, XRP, BNB, Polygon support
- Live balance and transaction queries
- Token balance tracking (ERC-20, BEP-20)

✅ **Investigation Tools**
- Case search and filtering
- Automated fraud risk scoring
- Fund flow visualization
- Telegram alert integration
- Legal document export (JSON)

✅ **Security**
- Role-based authentication
- Environment variable-based configuration
- Secret scanning in CI/CD
- 20/20 unit tests passing

## Configuration Reference

### Required Variables
```env
# Authentication
AUTH_USERNAME=admin                    # Username for login
AUTH_PASSWORD=YourStrongPassword123    # Use a strong password!

# Case Persistence
CASES_FILE=/app/cases.json            # Path to case storage
```

### Optional Variables
```env
# Neo4j Graph Database (for advanced features)
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password

# Telegram Alerts
TELEGRAM_BOT_TOKEN=123456789:ABCDEFGH
TELEGRAM_CHAT_ID=987654321

# Streamlit Configuration
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_PORT=8080
STREAMLIT_CLIENT_SHOWERRORDETAILS=false
```

## Post-Deployment Testing

### Test 1: Access Application
```bash
curl https://your-railway-url.up.railway.app
```

### Test 2: Verify Login
1. Visit your Railway URL
2. Enter AUTH_USERNAME and AUTH_PASSWORD
3. Confirm login succeeds

### Test 3: Create Test Case
1. Click "➕ Registrar Nuevo Caso"
2. Fill in victim name, loss amount, wallet addresses
3. Click "🚀 Registrar Caso en el Sistema"
4. Refresh page and verify case persists

### Test 4: On-Chain Query
1. Select your test case
2. Click "🔄 Consultar todas las direcciones"
3. Verify balances and transactions load

## Troubleshooting

### Cases not persisting
- Check: Mount path is `/app`
- Check: `CASES_FILE=/app/cases.json`
- Verify: Cases appear in Railway file explorer

### Authentication fails
- Verify: `AUTH_USERNAME` and `AUTH_PASSWORD` are set
- Check: No leading/trailing spaces in passwords

### On-chain queries timeout
- These use public APIs with rate limits
- Retry after a few moments
- Consider using Streamlit's caching

### Application won't start
- Check Railway logs: Dashboard → Logs
- Verify Python 3.10+ available
- Confirm requirements.txt installs correctly

## Architecture

```
┌─────────────────────────────────────────┐
│      Streamlit Web Interface            │
│  (Authentication, Case Dashboard, UI)   │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┴──────────┬──────────────┐
    │                     │              │
┌───▼────┐         ┌─────▼────┐   ┌─────▼────┐
│  Case  │         │ On-Chain │   │   Neo4j  │
│Loader  │         │  Queries │   │Database  │
│(JSON)  │         │ (Public) │   │(Optional)│
└────────┘         └──────────┘   └──────────┘
    │
    └──► /app/cases.json (Persistent Volume)
```

## Support

For issues or questions:
1. Check logs: Railway Dashboard → Deployments → Logs
2. Review README.md for feature details
3. Check .env.example for configuration examples

## Security Best Practices

✅ **Before deploying publicly:**
- [ ] Set strong AUTH_PASSWORD (20+ characters)
- [ ] Enable HTTPS (Railway provides this)
- [ ] Configure firewall rules if available
- [ ] Use Neo4j authentication in production
- [ ] Enable Telegram alerts for critical activities
- [ ] Regularly backup cases.json data
- [ ] Monitor Railway logs for suspicious activity

## Production Checklist

- [ ] PR #3 merged to main
- [ ] All tests passing locally
- [ ] Environment variables configured
- [ ] Persistent volume created
- [ ] Authentication credentials set
- [ ] Application deployed
- [ ] Public URL generated
- [ ] Test cases created and verified
- [ ] Team members notified
- [ ] Documentation shared
