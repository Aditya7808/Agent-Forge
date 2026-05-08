"""Rebuild the products SQLite database from data/products.csv.

Run once after cloning, or whenever you edit the CSV.

    python scripts/init_db.py
"""
from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "products.csv"
DB_PATH = ROOT / "data" / "products.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    product_code   TEXT PRIMARY KEY,
    product_name   TEXT NOT NULL,
    material       TEXT,
    size           TEXT,
    color          TEXT,
    brand          TEXT,
    gender         TEXT,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    price          INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_products_name   ON products(product_name);
CREATE INDEX IF NOT EXISTS idx_products_brand  ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_gender ON products(gender);
"""


def main() -> int:
    if not CSV_PATH.exists():
        print(f"missing CSV: {CSV_PATH}", file=sys.stderr)
        return 1

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        conn.execute("DELETE FROM products")
        with CSV_PATH.open("r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = [
                (
                    row["product_code"],
                    row["product_name"],
                    row.get("material"),
                    row.get("size"),
                    row.get("color"),
                    row.get("brand"),
                    row.get("gender"),
                    int(row.get("stock_quantity") or 0),
                    int(float(row.get("price") or 0)),
                )
                for row in reader
            ]
        conn.executemany(
            "INSERT OR REPLACE INTO products "
            "(product_code, product_name, material, size, color, brand, gender, stock_quantity, price) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        print(f"loaded {len(rows)} products into {DB_PATH}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
