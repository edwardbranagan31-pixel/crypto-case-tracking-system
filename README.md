# crypto-case-tracking-system

Sistema de rastreo, monitoreo y análisis de casos crypto con:

- Streamlit para la interfaz web
- Neo4j AuraDB para modelado en grafo
- Telegram para alertas móviles instantáneas
- Despliegue listo para Railway

## Requisitos

- Python 3.10+
- Cuenta en Neo4j AuraDB
- Bot de Telegram con token
- Cuenta de Railway

## Variables de entorno

Crea un archivo `.env` con este formato:

```env
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=tu_password
TELEGRAM_BOT_TOKEN=123456789:ABCDEF...
TELEGRAM_CHAT_ID=123456789
AUTH_USERNAME=admin
AUTH_PASSWORD=replace_with_a_strong_password
```

La autenticación de la aplicación se activa cuando `AUTH_USERNAME` y
`AUTH_PASSWORD` están configurados. Usa una contraseña fuerte y no subas el
archivo `.env` al repositorio.

## Ejecutar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Abre en tu navegador:

```text
http://localhost:8501
```

## Despliegue en Railway

1. Sube este repositorio a GitHub.
2. Crea un proyecto en Railway.
3. Conecta el repositorio.
4. Agrega las variables de entorno anteriores.
5. Usa este comando de inicio:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8080
```

6. Genera tu dominio público en Railway.

## Funcionamiento

- Permite seleccionar un caso de investigación
- Muestra evidencias, wallets y endpoints de CEX
- Genera un grafo visual de flujo de fondos
- Permite enviar alertas a Telegram
- Exporta el expediente técnico en JSON
- Consulta balances nativos y transacciones recientes de direcciones Bitcoin y Ethereum

La consulta on-chain usa los exploradores públicos mempool.space y Blockscout, sin
requerir API keys. Está limitada a Bitcoin mainnet y Ethereum mainnet, puede estar
sujeta a límites de solicitudes y muestra datos del explorador en el momento de
la consulta; los tokens ERC-20 no se incluyen en el balance.

## Estructura del proyecto

```bash
.
├── app.py
├── requirements.txt
├── .streamlit/
│   └── config.toml
├── .env.example
├── README.md
└── railway.json
```
