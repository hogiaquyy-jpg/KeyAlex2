"""Chuyển toàn bộ key từ SQLite local sang Postgres (chạy 1 lần duy nhất).

Cách dùng (trên máy bạn, sau khi đã tạo database Neon/Supabase):
    set DATABASE_URL=postgresql://user:pass@host/db?sslmode=require   (PowerShell: $env:DATABASE_URL="...")
    python migrate.py [đường-dẫn-licenses.db]

Key đã có trên Postgres sẽ được bỏ qua, chạy lại nhiều lần cũng an toàn.
"""
import os
import sqlite3
import sys

SQLITE_PATH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "licenses.db")

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if not DATABASE_URL:
    sys.exit("Lỗi: chưa đặt biến môi trường DATABASE_URL.")

import psycopg  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

LIC_COLS = ("id", "license_key", "product_name", "customer_email",
            "max_activations", "status", "expires_at", "note", "created_at")
ACT_COLS = ("id", "license_id", "device_id", "activated_at", "last_validated_at")


def main():
    src = sqlite3.connect(SQLITE_PATH)
    src.row_factory = sqlite3.Row
    licenses = [dict(r) for r in src.execute("SELECT * FROM licenses ORDER BY id")]
    activations = [dict(r) for r in src.execute("SELECT * FROM activations ORDER BY id")]
    src.close()
    print(f"SQLite: {len(licenses)} key, {len(activations)} activation.")

    dst = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    n_lic = n_act = 0
    with dst:
        with dst.cursor() as cur:
            for r in licenses:
                cur.execute(
                    "INSERT INTO licenses (id, license_key, product_name, customer_email,"
                    " max_activations, status, expires_at, note, created_at)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    " ON CONFLICT (license_key) DO NOTHING",
                    tuple(r.get(c) for c in LIC_COLS))
                if cur.rowcount > 0:
                    n_lic += 1
            for r in activations:
                cur.execute(
                    "INSERT INTO activations (id, license_id, device_id,"
                    " activated_at, last_validated_at)"
                    " VALUES (%s, %s, %s, %s, %s)"
                    " ON CONFLICT (license_id, device_id) DO NOTHING",
                    tuple(r.get(c) for c in ACT_COLS))
                if cur.rowcount > 0:
                    n_act += 1
            cur.execute("SELECT setval(pg_get_serial_sequence('licenses', 'id'),"
                        " (SELECT COALESCE(MAX(id), 1) FROM licenses))")
            cur.execute("SELECT setval(pg_get_serial_sequence('activations', 'id'),"
                        " (SELECT COALESCE(MAX(id), 1) FROM activations))")
    dst.close()
    print(f"Postgres: thêm mới {n_lic} key, {n_act} activation (còn lại đã có, bỏ qua).")


if __name__ == "__main__":
    main()
