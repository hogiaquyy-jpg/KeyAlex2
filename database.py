import os
import sqlite3
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---- SQLite (mặc định, chạy local) ----
# DB mac dinh nam canh code (khong phu thuoc thu muc chay).
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "licenses.db"))

# ---- Postgres (production trên Render, KHÔNG mất khi restart) ----
# Đặt biến môi trường DATABASE_URL (vd của Neon/Supabase) là web tự dùng Postgres.
# Không đặt DATABASE_URL thì dùng SQLite file như cũ.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)


def is_postgres() -> bool:
    return USE_POSTGRES


SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS licenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_key TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    customer_email TEXT,
    max_activations INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    expires_at TEXT,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS activations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_id INTEGER NOT NULL,
    device_id TEXT NOT NULL,
    activated_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_validated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (license_id) REFERENCES licenses (id),
    UNIQUE (license_id, device_id)
);
"""

SCHEMA_POSTGRES = """
CREATE TABLE IF NOT EXISTS licenses (
    id SERIAL PRIMARY KEY,
    license_key TEXT UNIQUE NOT NULL,
    product_name TEXT NOT NULL,
    customer_email TEXT,
    max_activations INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    expires_at TEXT,
    note TEXT,
    created_at TEXT NOT NULL DEFAULT (NOW()::TEXT)
);
CREATE TABLE IF NOT EXISTS activations (
    id SERIAL PRIMARY KEY,
    license_id INTEGER NOT NULL REFERENCES licenses (id),
    device_id TEXT NOT NULL,
    activated_at TEXT NOT NULL DEFAULT (NOW()::TEXT),
    last_validated_at TEXT NOT NULL DEFAULT (NOW()::TEXT),
    UNIQUE (license_id, device_id)
);
"""


def _to_pg(query: str) -> str:
    """App viết placeholder kiểu SQLite (?), dịch sang kiểu Postgres (%s).

    An toàn vì toàn bộ query trong app không chứa dấu '?' trong string literal.
    """
    return query.replace("?", "%s")


class _PgConn:
    """Bọc connection psycopg để dùng chung interface với sqlite3 trong app."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, query, params=()):
        return self._conn.execute(_to_pg(query), params)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()


def _connect_pg():
    import psycopg  # noqa: WPS433 (import chậm: chỉ cần khi chạy Postgres)
    from psycopg.rows import dict_row

    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    if USE_POSTGRES:
        conn = _connect_pg()
        try:
            # Chạy từng lệnh riêng vì psycopg execute() không chạy multi-statement
            # có placeholder; ở đây toàn DDL tĩnh nên tách theo dấu ';'.
            for stmt in SCHEMA_POSTGRES.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    conn.execute(stmt)
            conn.commit()
        finally:
            conn.close()
    else:
        with get_db() as db:
            db.executescript(SCHEMA_SQLITE)
            db.commit()


@contextmanager
def get_db():
    if USE_POSTGRES:
        conn = _PgConn(_connect_pg())
        try:
            yield conn
            # app tự gọi db.commit() như với sqlite; không commit ngầm ở đây
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()


def import_backup(db, data: dict):
    """Nhập backup {licenses:[...], activations:[...]}. Bỏ qua key đã tồn tại.

    Trả về (số key thêm mới, số activation thêm mới).
    """
    licenses = data.get("licenses", []) or []
    activations = data.get("activations", []) or []
    n_lic = 0
    n_act = 0

    lic_cols = ("id", "license_key", "product_name", "customer_email",
                "max_activations", "status", "expires_at", "note", "created_at")
    act_cols = ("id", "license_id", "device_id", "activated_at", "last_validated_at")

    if USE_POSTGRES:
        lic_sql = ("INSERT INTO licenses (id, license_key, product_name, customer_email,"
                   " max_activations, status, expires_at, note, created_at)"
                   " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                   " ON CONFLICT (license_key) DO NOTHING")
        act_sql = ("INSERT INTO activations (id, license_id, device_id,"
                   " activated_at, last_validated_at)"
                   " VALUES (?, ?, ?, ?, ?)"
                   " ON CONFLICT (license_id, device_id) DO NOTHING")
    else:
        lic_sql = ("INSERT OR IGNORE INTO licenses (id, license_key, product_name,"
                   " customer_email, max_activations, status, expires_at, note, created_at)"
                   " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)")
        act_sql = ("INSERT OR IGNORE INTO activations (id, license_id, device_id,"
                   " activated_at, last_validated_at)"
                   " VALUES (?, ?, ?, ?, ?)")

    for row in licenses:
        cur = db.execute(lic_sql, tuple(row.get(c) for c in lic_cols))
        if cur.rowcount and cur.rowcount > 0:
            n_lic += 1
    for row in activations:
        cur = db.execute(act_sql, tuple(row.get(c) for c in act_cols))
        if cur.rowcount and cur.rowcount > 0:
            n_act += 1
    db.commit()

    if USE_POSTGRES:
        # Đồng bộ lại sequence sau khi chèn id thủ công
        db.execute("SELECT setval(pg_get_serial_sequence('licenses', 'id'),"
                   " (SELECT COALESCE(MAX(id), 1) FROM licenses))")
        db.execute("SELECT setval(pg_get_serial_sequence('activations', 'id'),"
                   " (SELECT COALESCE(MAX(id), 1) FROM activations))")
        db.commit()

    return n_lic, n_act
