from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

APP_DATA_DIR = Path(os.getenv("GDP_DATA_DIR", Path.home() / ".gdp_pavimentos_pro"))
DB_PATH = Path(os.getenv("GDP_DB_PATH", APP_DATA_DIR / "gdp_web.sqlite3"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=20, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db() -> None:
    with _connect() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id, updated_at DESC);
            """
        )


def _hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    rounds = 260_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return f"pbkdf2_sha256${rounds}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        alg, rounds_s, salt_hex, digest_hex = encoded.split("$", 3)
        if alg != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        rounds = int(rounds_s)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds).hex()
        return hmac.compare_digest(candidate, digest_hex)
    except Exception:
        return False


def create_user(username: str, password: str, display_name: str = "") -> tuple[bool, str]:
    username = username.strip()
    display_name = (display_name.strip() or username)
    if len(username) < 3:
        return False, "El usuario debe tener al menos 3 caracteres."
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    try:
        with _connect() as con:
            con.execute(
                "INSERT INTO users(username,password_hash,display_name) VALUES(?,?,?)",
                (username, _hash_password(password), display_name),
            )
        return True, "Usuario creado correctamente."
    except sqlite3.IntegrityError:
        return False, "Ese nombre de usuario ya existe."


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    with _connect() as con:
        row = con.execute(
            "SELECT id,username,password_hash,display_name FROM users WHERE username=?",
            (username.strip(),),
        ).fetchone()
    if row and _verify_password(password, row["password_hash"]):
        return {"id": row["id"], "username": row["username"], "display_name": row["display_name"]}
    return None


def save_project(user_id: int, name: str, state: dict[str, Any]) -> None:
    payload = json.dumps(serialize_value(state), ensure_ascii=False)
    with _connect() as con:
        con.execute(
            """
            INSERT INTO projects(user_id,name,payload_json) VALUES(?,?,?)
            ON CONFLICT(user_id,name) DO UPDATE SET
                payload_json=excluded.payload_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (user_id, name.strip(), payload),
        )


def list_projects(user_id: int) -> list[dict[str, Any]]:
    with _connect() as con:
        rows = con.execute(
            "SELECT id,name,created_at,updated_at FROM projects WHERE user_id=? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def load_project(user_id: int, project_id: int) -> dict[str, Any] | None:
    with _connect() as con:
        row = con.execute(
            "SELECT payload_json FROM projects WHERE id=? AND user_id=?",
            (project_id, user_id),
        ).fetchone()
    if not row:
        return None
    return deserialize_value(json.loads(row["payload_json"]))


def delete_project(user_id: int, project_id: int) -> None:
    with _connect() as con:
        con.execute("DELETE FROM projects WHERE id=? AND user_id=?", (project_id, user_id))


def serialize_value(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return {"__type__": "dataframe", "columns": list(value.columns), "records": value.to_dict(orient="records")}
    if isinstance(value, pd.Series):
        return {"__type__": "series", "name": value.name, "data": value.to_dict()}
    if isinstance(value, (date, datetime)):
        return {"__type__": "datetime", "value": value.isoformat(), "date_only": isinstance(value, date) and not isinstance(value, datetime)}
    if isinstance(value, dict):
        return {str(k): serialize_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_value(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def deserialize_value(value: Any) -> Any:
    if isinstance(value, list):
        return [deserialize_value(v) for v in value]
    if isinstance(value, dict):
        typ = value.get("__type__")
        if typ == "dataframe":
            return pd.DataFrame(value.get("records", []), columns=value.get("columns", []))
        if typ == "series":
            return pd.Series(value.get("data", {}), name=value.get("name"))
        if typ == "datetime":
            text = value.get("value", "")
            try:
                dt = datetime.fromisoformat(text)
                return dt.date() if value.get("date_only") else dt
            except Exception:
                return text
        return {k: deserialize_value(v) for k, v in value.items()}
    return value


init_db()
