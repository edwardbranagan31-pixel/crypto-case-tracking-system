from __future__ import annotations

import hmac
import os
import streamlit as st


def _get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _safe_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def is_auth_enabled() -> bool:
    """
    Activa autenticación si AUTH_USERNAME y AUTH_PASSWORD están definidos.
    """
    return bool(_get_env("AUTH_USERNAME") and _get_env("AUTH_PASSWORD"))


def is_authenticated() -> bool:
    return bool(st.session_state.get("authenticated", False))


def logout() -> None:
    st.session_state["authenticated"] = False
    st.session_state["auth_user"] = ""


def _validate_credentials(username: str, password: str) -> bool:
    expected_user = _get_env("AUTH_USERNAME")
    expected_pass = _get_env("AUTH_PASSWORD")
    if not expected_user or not expected_pass:
        return True  # modo abierto si no hay variables
    return _safe_compare(username, expected_user) and _safe_compare(password, expected_pass)


def require_login() -> bool:
    """
    Renderiza login y bloquea la app hasta autenticar.
    Devuelve True si ya está autenticado.
    """
    if is_authenticated():
        return True

    st.title("🔐 Acceso Seguro")
    st.caption("Ingresa tus credenciales para acceder al sistema.")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Usuario", placeholder="admin")
        password = st.text_input("Contraseña", type="password", placeholder="********")
        submit = st.form_submit_button("Entrar")

    if submit:
        if _validate_credentials(username.strip(), password):
            st.session_state["authenticated"] = True
            st.session_state["auth_user"] = username.strip() or "authorized_user"
            st.success("✅ Acceso concedido")
            st.rerun()
        else:
            st.error("❌ Credenciales inválidas")

    st.stop()
    return False


def auth_sidebar_status() -> None:
    """
    Muestra estado de sesión en sidebar.
    """
    if is_authenticated():
        user = st.session_state.get("auth_user", "authorized_user")
        st.sidebar.success(f"🔐 Sesión: {user}")
        if st.sidebar.button("Cerrar sesión"):
            logout()
            st.rerun()
    else:
        st.sidebar.warning("🔓 Sesión no autenticada")