"""SQLite-backed auth store: users, refresh-token revocation, secret vault.

Kept separate from the trading audit DB (SQLiteStore) so credentials and
secrets live in their own file with their own lifecycle. All SQL is
parameterized. Thread-safe via a single guarded connection.
"""

from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any


class AuthStore:
    def __init__(self, db_path: str | Path) -> None:
        self._path = str(db_path)
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    disabled INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    jti TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    revoked INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS user_secrets (
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    ciphertext TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (user_id, name)
                );
                """
            )
            self._conn.commit()

    # -- users ---------------------------------------------------------------
    def count_users(self) -> int:
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) AS c FROM users")
            return int(cur.fetchone()["c"])

    def create_user(self, username: str, password_hash: str, role: str = "user") -> dict[str, Any]:
        uname = (username or "").strip().lower()
        if not uname or len(uname) < 3 or len(uname) > 64:
            raise ValueError("username must be 3-64 characters")
        if not all(ch.isalnum() or ch in "._-" for ch in uname):
            raise ValueError("username may only contain letters, digits, . _ -")
        if role not in {"user", "admin"}:
            raise ValueError("invalid role")
        uid = uuid.uuid4().hex
        now = time.time()
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO users (id, username, password_hash, role, created_at) VALUES (?,?,?,?,?)",
                    (uid, uname, password_hash, role, now),
                )
                self._conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError("username already exists") from exc
        return {"id": uid, "username": uname, "role": role, "created_at": now}

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        uname = (username or "").strip().lower()
        with self._lock:
            cur = self._conn.execute("SELECT * FROM users WHERE username = ?", (uname,))
            row = cur.fetchone()
        return dict(row) if row else None

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cur.fetchone()
        return dict(row) if row else None

    # -- refresh tokens ------------------------------------------------------
    def store_refresh(self, jti: str, user_id: str, expires_at: float) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO refresh_tokens (jti, user_id, expires_at, revoked, created_at) "
                "VALUES (?,?,?,0,?)",
                (jti, user_id, expires_at, time.time()),
            )
            self._conn.commit()

    def is_refresh_valid(self, jti: str, user_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "SELECT expires_at, revoked FROM refresh_tokens WHERE jti = ? AND user_id = ?",
                (jti, user_id),
            )
            row = cur.fetchone()
        if not row:
            return False
        if int(row["revoked"]) == 1:
            return False
        return float(row["expires_at"]) > time.time()

    def revoke_refresh(self, jti: str) -> None:
        with self._lock:
            self._conn.execute("UPDATE refresh_tokens SET revoked = 1 WHERE jti = ?", (jti,))
            self._conn.commit()

    def revoke_all_user_refresh(self, user_id: str) -> None:
        with self._lock:
            self._conn.execute("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?", (user_id,))
            self._conn.commit()

    def purge_expired_refresh(self) -> int:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM refresh_tokens WHERE expires_at < ?", (time.time(),)
            )
            self._conn.commit()
            return cur.rowcount

    # -- secret vault (ciphertext only) -------------------------------------
    def put_secret(self, user_id: str, name: str, ciphertext: str) -> None:
        sname = (name or "").strip()
        if not sname or len(sname) > 64:
            raise ValueError("secret name must be 1-64 characters")
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO user_secrets (user_id, name, ciphertext, created_at) "
                "VALUES (?,?,?,?)",
                (user_id, sname, ciphertext, time.time()),
            )
            self._conn.commit()

    def list_secret_names(self, user_id: str) -> list[str]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT name FROM user_secrets WHERE user_id = ? ORDER BY name", (user_id,)
            )
            return [r["name"] for r in cur.fetchall()]

    def get_secret_cipher(self, user_id: str, name: str) -> str | None:
        with self._lock:
            cur = self._conn.execute(
                "SELECT ciphertext FROM user_secrets WHERE user_id = ? AND name = ?",
                (user_id, (name or "").strip()),
            )
            row = cur.fetchone()
        return row["ciphertext"] if row else None

    def delete_secret(self, user_id: str, name: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM user_secrets WHERE user_id = ? AND name = ?",
                (user_id, (name or "").strip()),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def close(self) -> None:
        with self._lock:
            self._conn.close()


_STORE: AuthStore | None = None
_STORE_LOCK = threading.Lock()


def get_auth_store(settings: Any | None = None) -> AuthStore:
    global _STORE
    if _STORE is not None:
        return _STORE
    with _STORE_LOCK:
        if _STORE is None:
            if settings is None:
                from apex.core.config import get_settings

                settings = get_settings()
            _STORE = AuthStore(settings.auth_db_path)
    return _STORE


def reset_auth_store_for_tests(store: AuthStore | None = None) -> None:
    """Test hook to swap the process singleton."""
    global _STORE
    _STORE = store
