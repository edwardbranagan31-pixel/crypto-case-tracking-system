"""Multi-tenant SaaS layer: tenants, user accounts with roles, tenant-scoped cases and usage limits.

Enabled with SAAS_MODE=1. State lives in a SQLite database (SAAS_DB, default saas.db).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROLES = ("admin", "analyst", "viewer")
WRITE_ROLES = ("admin", "analyst")

# monthly / total limits per plan; None = unlimited
PLANS: Dict[str, Dict[str, Optional[int]]] = {
    "free": {"cases": 5, "transforms_month": 50, "onchain_month": 20, "users": 2},
    "pro": {"cases": 100, "transforms_month": 2000, "onchain_month": 1000, "users": 10},
    "enterprise": {"cases": None, "transforms_month": None, "onchain_month": None, "users": None},
}
_PBKDF2_ROUNDS = 200_000
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.@-]{3,64}$")


def is_saas_enabled() -> bool:
    return os.getenv("SAAS_MODE", "").strip().lower() in {"1", "true", "yes", "on"}


def db_path() -> Path:
    return Path(os.getenv("SAAS_DB", Path(__file__).resolve().parent.parent / "saas.db"))


def _connect(path: Path | None = None) -> sqlite3.Connection:
    target = Path(path or db_path())
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL,
            plan TEXT NOT NULL DEFAULT 'free', created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL,
            created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS cases (
            tenant_id INTEGER NOT NULL REFERENCES tenants(id), case_id TEXT NOT NULL,
            data TEXT NOT NULL, PRIMARY KEY (tenant_id, case_id));
        CREATE TABLE IF NOT EXISTS usage (
            tenant_id INTEGER NOT NULL REFERENCES tenants(id), metric TEXT NOT NULL,
            period TEXT NOT NULL, count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (tenant_id, metric, period));
        """
    )
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, rounds, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(rounds))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def _validate_new_user(username: str, password: str) -> Optional[str]:
    if not _USERNAME_RE.match(username or ""):
        return "Usuario inválido (3-64 caracteres: letras, números, . _ @ -)."
    if len(password or "") < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    return None


def create_tenant(name: str, admin_username: str, admin_password: str, plan: str = "free",
                  path: Path | None = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Create a tenant and its first admin user. Returns (user, error)."""
    name = (name or "").strip()
    if not name:
        return None, "El nombre de la organización es obligatorio."
    if plan not in PLANS:
        return None, f"Plan desconocido: {plan}"
    error = _validate_new_user(admin_username, admin_password)
    if error:
        return None, error
    try:
        with _connect(path) as conn:
            cur = conn.execute("INSERT INTO tenants (name, plan, created_at) VALUES (?, ?, ?)", (name, plan, _now()))
            tenant_id = cur.lastrowid
            conn.execute(
                "INSERT INTO users (tenant_id, username, password_hash, role, created_at) VALUES (?, ?, ?, 'admin', ?)",
                (tenant_id, admin_username, hash_password(admin_password), _now()))
    except sqlite3.IntegrityError:
        return None, "La organización o el usuario ya existe."
    return {"tenant_id": tenant_id, "tenant": name, "username": admin_username, "role": "admin", "plan": plan}, None


def authenticate(username: str, password: str, path: Path | None = None) -> Optional[Dict[str, Any]]:
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT u.username, u.password_hash, u.role, t.id AS tenant_id, t.name AS tenant, t.plan "
            "FROM users u JOIN tenants t ON t.id = u.tenant_id WHERE u.username = ?", (username,)).fetchone()
    if row is None:
        verify_password(password, hash_password("x"))  # equalize timing
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return {k: row[k] for k in ("tenant_id", "tenant", "username", "role", "plan")}


def get_plan(tenant_id: int, path: Path | None = None) -> str:
    with _connect(path) as conn:
        row = conn.execute("SELECT plan FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
    return row["plan"] if row else "free"


def set_plan(tenant_id: int, plan: str, path: Path | None = None) -> bool:
    if plan not in PLANS:
        return False
    with _connect(path) as conn:
        return conn.execute("UPDATE tenants SET plan = ? WHERE id = ?", (plan, tenant_id)).rowcount > 0


def can_write(role: str) -> bool:
    return role in WRITE_ROLES


def add_user(tenant_id: int, actor_role: str, username: str, password: str, role: str,
             path: Path | None = None) -> Optional[str]:
    """Add a user to a tenant (admin only, respects plan user limit). Returns error or None."""
    if actor_role != "admin":
        return "Solo los administradores pueden crear usuarios."
    if role not in ROLES:
        return f"Rol inválido: {role}"
    error = _validate_new_user(username, password)
    if error:
        return error
    limit = PLANS[get_plan(tenant_id, path)]["users"]
    try:
        with _connect(path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM users WHERE tenant_id = ?", (tenant_id,)).fetchone()[0]
            if limit is not None and count >= limit:
                return f"Límite de usuarios del plan alcanzado ({limit})."
            conn.execute(
                "INSERT INTO users (tenant_id, username, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (tenant_id, username, hash_password(password), role, _now()))
    except sqlite3.IntegrityError:
        return "El usuario ya existe."
    return None


def list_users(tenant_id: int, path: Path | None = None) -> list:
    with _connect(path) as conn:
        rows = conn.execute("SELECT username, role FROM users WHERE tenant_id = ? ORDER BY username", (tenant_id,))
        return [dict(r) for r in rows]


# ---- tenant-scoped case storage -------------------------------------------------

def load_tenant_cases(tenant_id: int, path: Path | None = None) -> Dict[str, Dict[str, Any]]:
    with _connect(path) as conn:
        rows = conn.execute("SELECT case_id, data FROM cases WHERE tenant_id = ?", (tenant_id,)).fetchall()
    cases = {}
    for row in rows:
        try:
            cases[row["case_id"]] = json.loads(row["data"])
        except ValueError:
            continue
    return cases


def save_tenant_cases(tenant_id: int, cases: Dict[str, Dict[str, Any]], path: Path | None = None) -> bool:
    """Replace the tenant's cases with the given set. Never touches other tenants."""
    try:
        with _connect(path) as conn:
            conn.execute("DELETE FROM cases WHERE tenant_id = ?", (tenant_id,))
            conn.executemany("INSERT INTO cases (tenant_id, case_id, data) VALUES (?, ?, ?)",
                             [(tenant_id, cid, json.dumps(data, ensure_ascii=False)) for cid, data in cases.items()])
    except (sqlite3.Error, TypeError):
        return False
    return True


# ---- usage limits ---------------------------------------------------------------

def get_usage(tenant_id: int, metric: str, path: Path | None = None) -> int:
    with _connect(path) as conn:
        row = conn.execute("SELECT count FROM usage WHERE tenant_id = ? AND metric = ? AND period = ?",
                           (tenant_id, metric, _period())).fetchone()
    return row["count"] if row else 0


def consume(tenant_id: int, metric: str, amount: int = 1, path: Path | None = None) -> bool:
    """Atomically count a monthly-metered action; False (and no charge) if over the plan limit."""
    limit = PLANS[get_plan(tenant_id, path)].get(f"{metric}_month")
    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT count FROM usage WHERE tenant_id = ? AND metric = ? AND period = ?",
                           (tenant_id, metric, _period())).fetchone()
        current = row["count"] if row else 0
        if limit is not None and current + amount > limit:
            conn.rollback()
            return False
        conn.execute(
            "INSERT INTO usage (tenant_id, metric, period, count) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(tenant_id, metric, period) DO UPDATE SET count = count + excluded.count",
            (tenant_id, metric, _period(), amount))
    return True


def can_add_case(tenant_id: int, current_cases: int, path: Path | None = None) -> bool:
    limit = PLANS[get_plan(tenant_id, path)]["cases"]
    return limit is None or current_cases < limit


# ---- Streamlit session helpers --------------------------------------------------

def tenant_dir(tenant_id: int) -> Path:
    base = Path(os.getenv("SAAS_DATA_DIR", Path(__file__).resolve().parent.parent / "saas_data"))
    return base / f"tenant_{int(tenant_id)}"


def saas_login(st: Any) -> Dict[str, Any]:
    """Render login / sign-up; stop the script until authenticated. Returns the session identity."""
    ident = st.session_state.get("saas_identity")
    if ident:
        return ident
    st.title("🔐 Acceso Seguro")
    login_tab, signup_tab = st.tabs(["Entrar", "Crear organización"])
    with login_tab:
        with st.form("saas_login"):
            user = st.text_input("Usuario")
            pwd = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Entrar"):
                found = authenticate(user.strip(), pwd)
                if found:
                    st.session_state["saas_identity"] = found
                    st.session_state["auth_user"] = found["username"]
                    st.session_state.pop("cases", None)
                    st.rerun()
                else:
                    st.error("❌ Credenciales inválidas")
    with signup_tab:
        with st.form("saas_signup"):
            org = st.text_input("Organización")
            user = st.text_input("Usuario administrador")
            pwd = st.text_input("Contraseña (mín. 8)", type="password")
            if st.form_submit_button("Crear cuenta (plan free)"):
                created, error = create_tenant(org, user.strip(), pwd)
                if error:
                    st.error(error)
                else:
                    st.session_state["saas_identity"] = created
                    st.session_state["auth_user"] = created["username"]
                    st.session_state.pop("cases", None)
                    st.rerun()
    st.stop()
    return {}


def saas_sidebar(st: Any, ident: Dict[str, Any]) -> None:
    tid = ident["tenant_id"]
    plan = get_plan(tid)
    limits = PLANS[plan]
    st.sidebar.success(f"🏢 {ident['tenant']} · {ident['username']} ({ident['role']})")
    st.sidebar.caption(
        f"Plan {plan}: transformaciones {get_usage(tid, 'transforms')}/{limits['transforms_month'] or '∞'}, "
        f"on-chain {get_usage(tid, 'onchain')}/{limits['onchain_month'] or '∞'}")
    if ident["role"] == "admin":
        with st.sidebar.expander("👥 Administración"):
            new_plan = st.selectbox("Plan", list(PLANS), index=list(PLANS).index(plan))
            if new_plan != plan and st.button("Cambiar plan"):
                set_plan(tid, new_plan)
                st.rerun()
            with st.form("saas_add_user", clear_on_submit=True):
                u = st.text_input("Nuevo usuario")
                p = st.text_input("Contraseña", type="password")
                r = st.selectbox("Rol", ROLES, index=1)
                if st.form_submit_button("Agregar usuario"):
                    err = add_user(tid, ident["role"], u.strip(), p, r)
                    st.error(err) if err else st.success("Usuario creado.")
            st.caption(", ".join(f"{x['username']} ({x['role']})" for x in list_users(tid)))
    if st.sidebar.button("Cerrar sesión"):
        for key in ("saas_identity", "auth_user", "cases"):
            st.session_state.pop(key, None)
        st.rerun()
