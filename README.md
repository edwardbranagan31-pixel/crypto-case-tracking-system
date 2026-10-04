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
CASES_FILE=cases.json
```

La autenticación de la aplicación se activa cuando `AUTH_USERNAME` y
`AUTH_PASSWORD` están configurados. Usa una contraseña fuerte y no subas el
archivo `.env` al repositorio.

Los casos nuevos se guardan localmente en `CASES_FILE` (por defecto,
`cases.json`). En Railway, el sistema de archivos puede ser efímero; configura
un volumen persistente o sincroniza los casos con Neo4j para conservarlos entre
despliegues.

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
- Consulta balances nativos y transacciones recientes de direcciones Bitcoin, Litecoin,
  Ethereum, BNB Smart Chain, Polygon, Solana, XRP Ledger y TRON; las redes EVM
  también muestran balances de tokens ERC-20/BEP-20

La consulta on-chain usa APIs públicas sin requerir claves. Solo consulta las redes
mainnet indicadas. Una dirección EVM se consulta de forma independiente en Ethereum,
BNB Smart Chain y Polygon, ya que el formato de dirección no identifica la red.
Las consultas EVM incluyen balances nativos y tokens que reporte el explorador;
las demás redes muestran solo la moneda nativa. Las APIs públicas pueden tener
límites de uso; los resultados reflejan los datos disponibles al momento de la consulta.

## Estructura del proyecto

```bash
.
├── app.py
├── requirements.txt
├── modules/
│   ├── __init__.py
│   ├── alert_history.py
│   ├── case_loader.py
│   ├── currency_utils.py
│   ├── graph_visualizer.py
│   ├── neo4j_integration.py
│   ├── onchain.py
│   ├── risk_scoring.py
│   └── search_engine.py
├── tests/
│   ├── test_auth.py
│   ├── test_case_loader.py
│   ├── test_currency_utils.py
│   └── test_onchain.py
├── .streamlit/
│   └── config.toml
├── .env.example
├── README.md
└── railway.json
```

La interfaz integra búsqueda, puntuación de riesgo, gráficos de wallets y
endpoints registrados, historial de alertas durante la sesión y sincronización
opcional de cada caso con Neo4j. El gráfico representa los datos registrados;
no demuestra por sí mismo un flujo de transacciones.
