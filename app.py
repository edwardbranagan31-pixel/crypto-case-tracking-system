import os
import json
import requests
import pandas as pd
import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph
from dotenv import load_dotenv
from modules import auth_sidebar_status, is_auth_enabled, require_login
from modules.alert_history import add_alert_history, get_case_alerts
from modules.case_loader import (
    load_cases_from_json,
    save_cases_to_json,
    validate_case_id,
)
from modules.graph_visualizer import build_case_graph
from modules.neo4j_integration import (
    get_neo4j_driver as create_neo4j_driver,
    sync_case_to_neo4j,
)
from modules.entities import ENTITY_TYPES, case_to_graph
from modules.graph_canvas import LAYOUTS, graph_to_canvas, load_graph, parse_node_id, save_graph
from modules.transforms import available_transforms, run_transform
from modules.collaboration import (can_access_case, graph_to_csv, graph_to_json, graph_to_pdf,
                                   read_audit, record_audit, sync_graph_to_neo4j)
from modules.analysis import (clusters, combined_risk, find_hubs, find_mixer_candidates,
                              transaction_timeline)
from modules.machines import MACHINES, run_machine
from modules.link_analysis import build_link_graph, find_linked_cases
from modules.onchain import check_case_addresses
from modules.risk_scoring import compute_risk_score, get_risk_label
from modules.search_engine import search_all

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
CASES_FILE = os.getenv(
    "CASES_FILE", os.path.join(os.path.dirname(__file__), "cases.json")
)

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
    st.session_state.cases = load_cases_from_json(CASES_FILE) or {
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
search_query = st.sidebar.text_input("🔎 Buscar casos, wallets o exchanges")
if search_query.strip():
    matches = search_all(st.session_state.cases, search_query)
    if matches:
        st.sidebar.caption("Resultados")
        for match in matches:
            st.sidebar.write(
                f"**{match['case_id']}** · {match.get('title', '')} "
                f"({match['match_type']})"
            )
    else:
        st.sidebar.caption("No se encontraron coincidencias.")

st.sidebar.markdown("### 📡 Estado del Sistema")
neo4j_driver = None
if NEO4J_URI and NEO4J_PASSWORD:
    neo4j_driver = create_neo4j_driver(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    if neo4j_driver is None:
        st.sidebar.warning("Neo4j no conectado.")
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
            new_wallets_text = st.text_area(
                "Direcciones de wallets (una por línea; cualquier red soportada)",
                value="",
            )
            new_cex_exchange = st.text_input("Exchange CEX (opcional)", value="")
            new_cex_address = st.text_input("Dirección CEX (opcional)", value="")

        submit_case = st.form_submit_button("🚀 Registrar Caso en el Sistema")

    if submit_case:
        normalized_case_id = new_case_id.strip()
        case_id_error = validate_case_id(normalized_case_id, st.session_state.cases)
        if case_id_error:
            st.error(case_id_error)
        elif bool(new_cex_exchange.strip()) != bool(new_cex_address.strip()):
            st.error("Indica tanto el exchange como su dirección CEX.")
        else:
            wallets = {
                f"WALLET_{index}": address.strip()
                for index, address in enumerate(new_wallets_text.splitlines(), start=1)
                if address.strip()
            }
            cex_endpoints = []
            if new_cex_exchange.strip() and new_cex_address.strip():
                cex_endpoints.append(
                    {
                        "exchange": new_cex_exchange.strip(),
                        "address": new_cex_address.strip(),
                        "type": "Address",
                    }
                )
            new_case = {
                "title": f"Caso {normalized_case_id} ({new_victim} - {new_platform})",
                "victim": new_victim,
                "police_report": normalized_case_id,
                "total_loss_usd": new_loss,
                "traced_usd": 0.0,
                "fiat_wire": {
                    "amount": "$0.00",
                    "bank": "N/A",
                    "beneficiary": "N/A",
                    "receiving_bank": "N/A",
                    "date": "N/A",
                },
                "wallets": wallets,
                "cex_endpoints": cex_endpoints,
            }
            st.session_state.cases[normalized_case_id] = new_case
            saved = save_cases_to_json(CASES_FILE, st.session_state.cases)
            if neo4j_driver:
                sync_result = sync_case_to_neo4j(
                    neo4j_driver, normalized_case_id, new_case
                )
                if sync_result["status"] != "ok":
                    st.warning(
                        sync_result.get(
                            "message", "No se pudo sincronizar el caso a Neo4j."
                        )
                    )
            if saved:
                st.success(
                    f"Caso {normalized_case_id} registrado. "
                    "Selecciónalo en la barra lateral."
                )
                st.rerun()
            else:
                st.error(
                    f"El caso {normalized_case_id} está disponible en esta sesión, "
                    "pero no se pudo guardar en el archivo de casos."
                )

else:
    case_data = st.session_state.cases[selected_option]
    if not can_access_case(st.session_state.get("auth_user", ""), case_data, is_auth_enabled()):
        st.error("No tienes acceso a este caso.")
        st.stop()
    st.title(f"🔍 {case_data['title']}")
    st.caption(f"Víctima: {case_data['victim']} | Referencia Policial: {case_data['police_report']}")
    risk_score = compute_risk_score(case_data)

    # Botones de acción
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("💾 Guardar expediente"):
            saved = save_cases_to_json(CASES_FILE, st.session_state.cases)
            if saved:
                st.success(f"Expediente guardado en {CASES_FILE}.")
            else:
                st.error(f"No se pudo guardar el expediente en {CASES_FILE}.")
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

    if neo4j_driver and st.button("🔄 Sincronizar caso con Neo4j"):
        sync_result = sync_case_to_neo4j(neo4j_driver, selected_option, case_data)
        if sync_result["status"] == "ok":
            st.success(sync_result["message"])
        else:
            st.error(sync_result.get("message", sync_result.get("reason", "Sync failed")))

    # Métricas
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    col_m1.metric("Pérdida Principal Estimada", f"${case_data['total_loss_usd']:,.2f}")
    col_m2.metric("Fondos Trazados a CEX", f"${case_data['traced_usd']:,.2f}")
    col_m3.metric("Endpoints CEX Identificados", len(case_data['cex_endpoints']))
    col_m4.metric("Estado de Investigación", "Activo / Trazado")
    col_m5.metric("Riesgo", f"{risk_score}/100", get_risk_label(risk_score))

    st.markdown("---")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Evidencias & Transacciones",
        "🕸️ Grafo de Flujo On-Chain",
        "🔔 Alertas en Tiempo Real",
        "📄 Expediente para Autoridades",
        "🔗 Casos Vinculados",
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
            "Consulta balances nativos e historial reciente en Bitcoin, Litecoin, Ethereum, "
            "BNB Smart Chain, Polygon, Solana, XRP Ledger y TRON. "
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
        st.caption("Diagrama de wallets y endpoints registrados; no representa transacciones verificadas.")
        with st.expander("Diagrama estático (Graphviz)"):
            st.graphviz_chart(build_case_graph(case_data))

        graphs = st.session_state.setdefault("entity_graphs", {})
        if selected_option not in graphs:
            graphs[selected_option] = load_graph(selected_option) or case_to_graph(selected_option, case_data)
        entity_graph = graphs[selected_option]

        col_f, col_l = st.columns(2)
        visible = col_f.multiselect("Filtrar por tipo", ENTITY_TYPES, default=list(ENTITY_TYPES))
        layout = col_l.selectbox("Disposición", LAYOUTS)
        canvas = graph_to_canvas(entity_graph, visible)
        a_nodes = [Node(id=n["id"], label=n["label"], color=n["color"], title=n["title"], size=20)
                   for n in canvas["nodes"]]
        a_edges = [Edge(source=e["source"], target=e["target"], label=e["label"]) for e in canvas["edges"]]
        a_config = Config(width=900, height=500, directed=True,
                          hierarchical=layout == "hierarchical", physics=layout != "hierarchical")
        clicked = agraph(nodes=a_nodes, edges=a_edges, config=a_config)

        key = parse_node_id(clicked) if clicked else None
        selected_entity = entity_graph.entities.get(key) if key else None
        if selected_entity:
            st.markdown(f"**Nodo seleccionado:** `{selected_entity.type}` · {selected_entity.value}")
            options = available_transforms(selected_entity)
            if options:
                chosen = st.selectbox("Transformación", options, format_func=lambda t: f"{t.name} — {t.description}")
                if st.button("▶️ Ejecutar transformación"):
                    res = run_transform(chosen.name, selected_entity, entity_graph,
                                        {"cases": st.session_state.cases})
                    record_audit(st.session_state.get("auth_user", ""), f"transform:{chosen.name}",
                                 selected_option, f"{selected_entity.type}:{selected_entity.value} -> {res['status']}")
                    if res["status"] == "ok":
                        st.success(f"{res['added']} entidades nuevas.")
                        st.rerun()
                    else:
                        st.error(res["error"])
            else:
                st.info("No hay transformaciones disponibles para este tipo.")
        else:
            st.caption("Haz clic en un nodo para ejecutar transformaciones.")

        if selected_entity:
            compatible = {n: m for n, m in MACHINES.items()}
            machine_name = st.selectbox("Machine", list(compatible), format_func=lambda n: f"{n} — {compatible[n].description}")
            if st.button("⚙️ Ejecutar machine sobre el nodo"):
                with st.spinner("Ejecutando machine..."):
                    res = run_machine(machine_name, selected_entity, entity_graph, {"cases": st.session_state.cases})
                record_audit(st.session_state.get("auth_user", ""), f"machine:{machine_name}", selected_option,
                             f"{selected_entity.type}:{selected_entity.value} -> +{res['added']}")
                st.session_state["machine_result"] = res
                st.rerun()
        if st.session_state.get("machine_result"):
            res = st.session_state.pop("machine_result")
            st.success(f"Machine: {res['added']} entidades nuevas, {res.get('flagged', 0)} marcadas como exchange.")
            for err in res["errors"]:
                st.warning(err)

        with st.expander("📈 Análisis del grafo"):
            graph_risk = combined_risk(risk_score, entity_graph)
            st.metric("Riesgo combinado (caso + grafo)", f"{graph_risk['score']}/100", f"+{graph_risk['points']}")
            for finding in graph_risk["findings"]:
                st.caption(f"• {finding}")
            hubs = find_hubs(entity_graph)
            st.markdown("**Hubs**")
            if hubs:
                st.dataframe(pd.DataFrame(hubs))
            else:
                st.caption("Sin hubs detectados.")
            mixers = find_mixer_candidates(entity_graph)
            st.markdown("**Posibles mixers / agregadores (heurística, no prueba)**")
            if mixers:
                st.dataframe(pd.DataFrame(mixers))
            else:
                st.caption("Sin candidatos.")
            comps = clusters(entity_graph)
            st.markdown(f"**Clusters:** {len(comps)} (el mayor con {len(comps[0]) if comps else 0} entidades)")
            timeline = transaction_timeline(entity_graph)
            st.markdown("**Línea de tiempo de transacciones**")
            if timeline:
                st.dataframe(pd.DataFrame(timeline))
            else:
                st.caption("Sin transacciones con fecha. Ejecuta address_to_transactions.")

        col_s, col_r = st.columns(2)
        if col_s.button("💾 Guardar grafo"):
            if save_graph(selected_option, entity_graph):
                record_audit(st.session_state.get("auth_user", ""), "save_graph", selected_option)
                st.success("Grafo guardado.")
            else:
                st.error("No se pudo guardar.")
        if col_r.button("↩️ Reiniciar desde el caso"):
            graphs[selected_option] = case_to_graph(selected_option, case_data)
            st.rerun()

        st.markdown("#### Exportar y colaborar")
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.download_button("📥 CSV", graph_to_csv(entity_graph), f"grafo_{selected_option}.csv", "text/csv")
        col_b.download_button("📥 JSON", graph_to_json(entity_graph), f"grafo_{selected_option}.json", "application/json")
        col_c.download_button("📥 PDF", graph_to_pdf(selected_option, entity_graph), f"grafo_{selected_option}.pdf", "application/pdf")
        if col_d.button("🔄 Grafo a Neo4j"):
            res = sync_graph_to_neo4j(neo4j_driver, selected_option, entity_graph)
            record_audit(st.session_state.get("auth_user", ""), "neo4j_graph_sync", selected_option, res["status"])
            if res["status"] != "error":
                st.info(f"Neo4j: {res['status']}")
            else:
                st.error(res["error"])
        with st.expander("Registro de auditoría"):
            for entry in reversed(read_audit(selected_option)[-50:]):
                st.caption(f"{entry['timestamp']} · {entry['user']} · {entry['action']} · {entry['detail']}")

    with tab3:
        st.subheader("🔔 Sistema Móvil de Alertas Vía Telegram")
        st.markdown("Envía notificaciones automatizadas a tu teléfono cuando se detecte un movimiento crítico.")

        alert_text = st.text_area(
            "Mensaje de Alerta a Enviar:",
            value=(
                f"🚨 *ALERTA DE DETECCIÓN CEX - {selected_option}*\n\n"
                f"• *Víctima:* {case_data['victim']}\n"
                f"• *Monto Trazado:* ${case_data['traced_usd']:,.2f} USD\n"
                f"• *CEX Identificados:* "
                f"{', '.join(endpoint.get('exchange', 'Unknown') for endpoint in case_data['cex_endpoints']) or 'Sin datos'}\n"
                f"• *Estado:* Expediente disponible para revisión.\n\n"
                f"📍 *Acción:* Revisar expediente en el panel."
            ),
        )

        if st.button("📲 Transmitir Alerta Instantánea al Celular"):
            success, msg = send_telegram_alert(alert_text)
            if success:
                add_alert_history(selected_option, alert_text)
                st.success(msg)
            else:
                st.error(msg)

        st.markdown("#### Historial de alertas")
        case_alerts = get_case_alerts(selected_option)
        if case_alerts:
            for alert in case_alerts:
                st.caption(f"{alert['timestamp']} · {alert['message']}")
        else:
            st.info("Aún no hay alertas enviadas para este caso en esta sesión.")

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
            "entity_graph": (st.session_state.get("entity_graphs", {}).get(selected_option)
                             or case_to_graph(selected_option, case_data)).to_dict(),
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

    with tab5:
        st.subheader("🔗 Análisis de Vínculos entre Casos")
        st.caption("Pivote por direcciones compartidas (wallets y endpoints CEX) con otros casos; son pistas, no prueba.")
        linked = find_linked_cases(st.session_state.cases, selected_option)
        if linked:
            st.graphviz_chart(build_link_graph(st.session_state.cases, selected_option))
            for link in linked:
                st.markdown(f"**{link['case_id']}** · {link['title']} — {link['link_strength']} entidad(es) compartida(s)")
                for ent in link["shared_entities"]:
                    st.caption(f"{ent['label']} · {ent['address']}")
        else:
            st.info("No se encontraron direcciones compartidas con otros casos.")

# Footer
st.markdown("<hr>", unsafe_allow_html=True)
st.caption("Sistema de Ciberinteligencia & Rastreo Crypto · Modo Streamlit · Compatible con Railway")
