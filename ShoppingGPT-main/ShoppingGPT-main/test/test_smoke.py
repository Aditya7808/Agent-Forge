"""Smoke tests that don't require a network round-trip.

Runs SQL guardrails, product-code extraction, and DB schema checks. The
full LLM/agent flow is exercised manually via app.py + a real OpenAI key."""
from __future__ import annotations

import os
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Avoid hard-failing config import if no .env is present in CI; tests below
# don't actually need an OpenAI key.
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-used")


class GuardedSQLTests(unittest.TestCase):
    def test_select_allowed(self):
        from shoppinggpt.tool.product_search import _is_safe_select

        self.assertTrue(_is_safe_select("SELECT * FROM products LIMIT 5"))
        self.assertTrue(
            _is_safe_select(
                "select product_name from products where price < 500000 limit 12"
            )
        )

    def test_destructive_blocked(self):
        from shoppinggpt.tool.product_search import _is_safe_select

        self.assertFalse(_is_safe_select("DROP TABLE products"))
        self.assertFalse(_is_safe_select("DELETE FROM products"))
        self.assertFalse(_is_safe_select("UPDATE products SET price = 0"))
        self.assertFalse(_is_safe_select("INSERT INTO products VALUES (1)"))
        self.assertFalse(_is_safe_select("PRAGMA table_info(products)"))
        self.assertFalse(_is_safe_select(""))
        self.assertFalse(_is_safe_select("not sql at all"))


class ProductCodeExtractionTests(unittest.TestCase):
    def test_extracts_codes_in_order(self):
        from shoppinggpt.tool.catalogue import extract_product_codes

        text = "Try [P004] with [P011], or even P019. Already mentioned P004."
        self.assertEqual(extract_product_codes(text), ["P004", "P011", "P019"])

    def test_handles_empty(self):
        from shoppinggpt.tool.catalogue import extract_product_codes

        self.assertEqual(extract_product_codes(""), [])
        self.assertEqual(extract_product_codes(None), [])


class DatabaseTests(unittest.TestCase):
    def test_db_present_with_expected_schema(self):
        db_path = ROOT / "data" / "products.db"
        if not db_path.exists():
            self.skipTest("products.db not built; run scripts/init_db.py")
        conn = sqlite3.connect(db_path)
        try:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(products)")]
        finally:
            conn.close()
        for expected in (
            "product_code",
            "product_name",
            "material",
            "size",
            "color",
            "brand",
            "gender",
            "stock_quantity",
            "price",
        ):
            self.assertIn(expected, cols)


if __name__ == "__main__":
    unittest.main()
