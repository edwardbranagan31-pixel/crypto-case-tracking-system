import os
import json
import requests
import pandas as pd
import streamlit as st
import graphviz
from neo4j import GraphDatabase
from dotenv import load_dotenv
from modules import auth_sidebar_status, is_auth_enabled, require_login
from modules.onchain import check_case_addresses

# -----------------------------------------------------------------------------
# CARGA DE VARIABLES DE ENTORNO
# -----------------------------------------------------------------------------
load_dotenv()

st.set_page_config(
    page_title="Sistema de Inteligencia & Rastreo Cripto",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

if is_auth_enabled():
    require_login()
    auth_sidebar_status()

# -----------------------------------------------------------------------------
# CONFIGURACIÓN
# -----------------------------------------------------------------------------
NEO4J_URI = os.getenv("NEO4J_URI", "")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# -----------------------------------------------------------------------------
# CONEXIÓN A NEO4J
# -----------------------------------------------------------------------------
def get_neo4j_driver():
    if NEO4J_URI and NEO4J_PASSWORD:
        try:
            driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            driver.verify_connectivity()
            return driver
        except Exception as e:
            st.sidebar.warning(f"Neo4j no conectado: {e}")
            return None
    return None


# -----------------------------------------------------------------------------
# TELEGRAM
# -----------------------------------------------------------------------------
def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False, "Faltan TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID."

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            return True, "Notificación enviada con éxito."
        return False, f"Error Telegram: {res.text}"
    except Exception as e:
        return False, f"Excepción de red: {str(e)}"


# -----------------------------------------------------------------------------
# CASOS PREDETERMINADOS
# -----------------------------------------------------------------------------
if "cases" not in st.session_state:
    st.session_state.cases = {
        "NC-JOHNSTON-2024-3912": {
            "title": "Caso #2024-3912 (Edward Branagan - CLF Coin)",
            "victim": "Edward Andres Branagan",
            "police_report": "Johnston County Sheriff's Office Case #2024-3912",
            "total_loss_usd": 800000.0,
            "traced_usd": 220000.0,
            "fiat_wire": {
                "amount": "$120,000.00 USD",
                "bank": "State Employees' Credit Union (SECU)",
                "beneficiary": "GOLD HARBOR GROUP CO., LIMITED",
                "receiving_bank": "Community FSB (NY, USA)",
                "date": "2024-08-15",
            },
            "wallets": {
                "BTC_DEPOSIT": "185MZoHdBjjwngvtQge9pBfdpbLXtWEjwo",
                "ETH_USDT_DEPOSIT": "0xB7C92987c942B1794Ee98e2065AD9a98A502C381",
            },
            "cex_endpoints": [
                {
                    "exchange": "Binance",
                    "address": "bc1qvef2q948lpcc4hrtxhsnz8e5760qhwdkqs5m2c",
                    "type": "BTC SegWit",
                },
                {
                    "exchange": "OKX",
                    "address": "3PBkkkxAxha38jC7DoBf7ysKrRY9VQengA",
                    "type": "BTC",
                },
                {
                    "exchange": "Coinbase",
                    "address": "0x43430a7db626ccd3b3101604791654f14f5db762",
                    "type": "ETH/USDT",
                },
            ],
        }
    }


# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
st.sidebar.title("🛡️ Ciberinteligencia & Forense")
st.sidebar.markdown("---")

case_options = list(st.session_state.cases.keys()) + ["+ Crear Nuevo Caso"]
selected_option = st.sidebar.selectbox("📂 Seleccionar Expediente:", case_options)

st.sidebar.markdown("### 📡 Estado del Sistema")
neo4j_driver = get_neo4j_driver()
neo4j_status = "🟢 Conectado" if neo4j_driver else "🟡 Modo Local / Sin Neo4j"
telegram_status = "🟢 Configurado" if (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID) else "🔴 Sin Credenciales"

st.sidebar.text(f"Base de Datos: {neo4j_status}")
st.sidebar.text(f"Bot Telegram: {telegram_status}")
st.sidebar.markdown("---")

# -----------------------------------------------------------------------------
# CREAR NUEVO CASO
# -----------------------------------------------------------------------------
if selected_option == "+ Crear Nuevo Caso":
    st.title("➕ Registrar Nuevo Caso de Robo Cripto")
    st.markdown("Ingresa los datos iniciales para iniciar el rastreo e integrar el expediente al sistema.")

    with st.form("new_case_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_case_id = st.text_input("Código de Caso / Reporte Policial", value="CASO-2026-002")
            new_victim = st.text_input("Nombre de la Víctima", value="Nombre Ejemplo")
            new_platform = st.text_input("Plataforma Estafadora", value="Ej. Fake Exchange / Mining Pool")

        with col2:
            new_loss = st.number_input("Pérdida Total Estimada ($ USD)", value=50000.0, step=1000.0)
            new_btc_wallet = st.text_input("Dirección de Depósito BTC", value="")
            new_eth_wallet = st.text_input("Dirección de Depósito ETH/USDT", value="")

        submit_case = st.form_submit_button("🚀 Registrar Caso en el Sistema")

    if submit_case:
        st.session_state.cases[new_case_id] = {
            "title": f"Caso {new_case_id} ({new_victim} - {new_platform})",
            "victim": new_victim,
            "police_report": new_case_id,
            "total_loss_usd": new_loss,
            "traced_usd": 0.0,
            "fiat_wire": {
                "amount": "$0.00",
                "bank": "N/A",
                "beneficiary": "N/A",
                "receiving_bank": "N/A",
                "date": "N/A",
            },
            "wallets": {
                "BTC_DEPOSIT": new_btc_wallet,
                "ETH_USDT_DEPOSIT": new_eth_wallet,
            },
            "cex_endpoints": [],
        }
        st.success(f"Caso {new_case_id} registrado exitosamente. Selecciónalo en la barra lateral.")
        st.rerun()

else:
    case_data = st.session_state.cases[selected_option]
    st.title(f"🔍 {case_data['title']}")
    st.caption(f"Víctima: {case_data['victim']} | Referencia Policial: {case_data['police_report']}")

    # Botones de acción
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("📥 Cargar Expediente Completo"):
            st.success(f"Expediente del caso {selected_option} cargado correctamente.")
    with col_btn2:
        if st.button("🧪 Probar Alerta Telegram"):
            message = (
                f"🚨 *ALERTA DE DETECCIÓN CEX - {selected_option}*\n\n"
                f"• *Víctima:* {case_data['victim']}\n"
                f"• *Monto Trazado:* ${case_data['traced_usd']:,.2f} USD\n"
                f"• *CEX Identificados:* {', '.join(endpoint['exchange'] for endpoint in case_data['cex_endpoints']) or 'Sin datos'}\n\n"
                f"📍 *Acción:* Revisar expediente en el panel."
            )
            success, msg = send_telegram_alert(message)
            if success:
                st.success(msg)
            else:
                st.error(msg)

    # Métricas
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Pérdida Principal Estimada", f"${case_data['total_loss_usd']:,.2f}")
    col_m2.metric("Fondos Trazados a CEX", f"${case_data['traced_usd']:,.2f}")
    col_m3.metric("Endpoints CEX Identificados", len(case_data['cex_endpoints']))
    col_m4.metric("Estado de Investigación", "Activo / Trazado")

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Evidencias & Transacciones",
        "🕸️ Grafo de Flujo On-Chain",
        "🔔 Alertas en Tiempo Real",
        "📄 Expediente para Autoridades",
    ])

    with tab1:
        st.subheader("📌 Registro de Evidencias Integradas")
        col_e1, col_e2 = st.columns(2)

        with col_e1:
            st.markdown("#### 🏦 Salida Bancaria Fiduciaria (Fiat Wire)")
            st.json(case_data["fiat_wire"])

        with col_e2:
            st.markdown("#### 🔑 Billeteras Semilla de Captación")
            st.json(case_data["wallets"])

        st.markdown("#### 🎯 Destinos Finales Identificados en Exchanges (CEX Endpoints)")
        if case_data["cex_endpoints"]:
            df_cex = pd.DataFrame(case_data["cex_endpoints"])
            st.dataframe(df_cex, use_container_width=True)
        else:
            st.info("Aún no se han registrado endpoints CEX para este caso.")

        st.markdown("---")
        st.subheader("⛓️ Consulta on-chain en vivo")
        st.caption(
            "Consulta balances nativos e historial reciente de Bitcoin y Ethereum. "
            "Requiere conexión a exploradores públicos."
        )
        addresses_fingerprint = (
            tuple(sorted((case_data.get("wallets") or {}).items())),
            tuple(
                sorted(
                    (
                        endpoint.get("exchange", ""),
                        endpoint.get("address", ""),
                    )
                    for endpoint in case_data.get("cex_endpoints", [])
                    if isinstance(endpoint, dict)
                )
            ),
        )
        saved_check = st.session_state.get("onchain_check", {})
        if st.button("🔄 Consultar todas las direcciones", key="check_onchain"):
            with st.spinner("Consultando exploradores de bloques..."):
                results = check_case_addresses(
                    case_data.get("wallets", {}),
                    case_data.get("cex_endpoints", []),
                )
            saved_check = {
                "case_id": selected_option,
                "fingerprint": addresses_fingerprint,
                "results": results,
            }
            st.session_state["onchain_check"] = saved_check

        if (
            saved_check.get("case_id") == selected_option
            and saved_check.get("fingerprint") == addresses_fingerprint
        ):
            for result in saved_check["results"]:
                heading = f"{result['label']} — {result['address']}"
                with st.expander(heading, expanded=True):
                    if result["status"] != "ok":
                        st.warning(result.get("error", "Address could not be checked."))
                        continue
                    st.metric(
                        f"Current balance ({result['network']})", result["balance"]
                    )
                    st.caption(
                        f"On-chain transactions: {result['transaction_count']} · "
                        f"[Open in explorer]({result['explorer']})"
                    )
                    if result["transactions"]:
                        st.dataframe(
                            pd.DataFrame(result["transactions"]),
                            use_container_width=True,
                            hide_index=True,
                        )
                    else:
                        st.info("No transactions returned by the explorer.")
                    if result.get("tokens"):
                        st.markdown("**Token balances**")
                        st.dataframe(
                            pd.DataFrame(result["tokens"]),
                            use_container_width=True,
                            hide_index=True,
                        )
        elif not case_data.get("wallets") and not case_data.get("cex_endpoints"):
            st.info("No wallet or CEX addresses are registered for this case.")

    with tab2:
        st.subheader("🕸️ Grafo de Dispersión y Agregación de Fondos")
        st.markdown("Visualización de la ruta seguida por los activos desde el origen hasta los exchanges regulados.")

        graph = graphviz.Digraph(format="svg")
        graph.attr(rankdir="LR", size="8,5")

        graph.node("V", f"Víctima:\n{case_data['victim']}", shape="ellipse", color="blue")
        graph.node("S", "Plataforma Scam\n(CLF Coin App)", shape="box", color="red")
        graph.node("I", "Billeteras Intermediarias\n(Layer 1)", shape="box", color="orange")
        graph.node("A", "Agregación Central\n(Commingling Wallet)", shape="box", color="purple")

        graph.edge("V", "S", label="Depósito")
        graph.edge("S", "I", label="Split / Peel Chain")
        graph.edge("I", "A", label="Consolidación")

        for idx, endpoint in enumerate(case_data["cex_endpoints"]):
            node_id = f"CEX_{idx}"
            graph.node(
                node_id,
                f"Exchange Destino:\n{endpoint['exchange']}\n({endpoint['address'][:8]}...)",
                shape="doubleoctagon",
                color="green",
            )
            graph.edge("A", node_id, label="Dispersión Final")

        st.graphviz_chart(graph)

    with tab3:
        st.subheader("🔔 Sistema Móvil de Alertas Vía Telegram")
        st.markdown("Envía notificaciones automatizadas a tu teléfono cuando se detecte un movimiento crítico.")

        alert_text = st.text_area(
            "Mensaje de Alerta a Enviar:",
            value=(
                f"🚨 *ALERTA DE DETECCIÓN CEX - {selected_option}*\n\n"
                f"• *Víctima:* {case_data['victim']}\n"
                f"• *Monto Trazado:* ${case_data['traced_usd']:,.2f} USD\n"
                f"• *CEX Identificados:* Binance, OKX, Coinbase\n"
                f"• *Estado:* Requerimiento de Preservación Listo.\n\n"
                f"📍 *Acción:* Revisar expediente en el panel."
            ),
        )

        if st.button("📲 Transmitir Alerta Instantánea al Celular"):
            success, msg = send_telegram_alert(alert_text)
            if success:
                st.success(msg)
            else:
                st.error(msg)

    with tab4:
        st.subheader("📄 Generador de Expediente Técnico Normalizado")
        st.markdown("Descarga el informe completo estructurado para la fiscalía o departamentos de Cumplimiento CEX.")

        export_data = {
            "case_header": {
                "case_id": selected_option,
                "victim_name": case_data["victim"],
                "police_report": case_data["police_report"],
                "total_loss_usd": case_data["total_loss_usd"],
                "traced_usd": case_data["traced_usd"],
            },
            "fiat_wire_evidence": case_data["fiat_wire"],
            "monitored_wallets": case_data["wallets"],
            "target_cex_accounts": case_data["cex_endpoints"],
            "legal_request": "SOLICITUD FORMAL DE CONGELAMIENTO PREVENTIVO Y REGISTROS KYC/IP",
        }

        json_str = json.dumps(export_data, indent=2)
        st.code(json_str, language="json")

        st.download_button(
            label="📥 Descargar Expediente Legal (JSON)",
            data=json_str,
            file_name=f"Expediente_{selected_option}.json",
            mime="application/json",
        )

# Footer
st.markdown("<hr>", unsafe_allow_html=True)
st.caption("Sistema de Ciberinteligencia & Rastreo Crypto · Modo Streamlit · Compatible con Railway")
