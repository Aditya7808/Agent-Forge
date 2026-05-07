"""
SQLite-backed search history.

Persists each completed analysis so users can revisit and re-export prior
searches without re-paying for Firecrawl + LLM calls.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional

from .config import get_settings
from .schemas import AnalysisResult

logger = logging.getLogger(__name__)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT,
    budget_min INTEGER,
    budget_max INTEGER,
    total_properties INTEGER,
    avg_score REAL,
    elapsed_seconds REAL,
    provider TEXT,
    model TEXT,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_searches_ts ON searches(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_searches_city ON searches(city);
"""


class SearchHistory:
    def __init__(self, db_path: Optional[Path] = None) -> None:
        self._db_path = db_path or get_settings().history_db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def save(self, result: AnalysisResult) -> int:
        avg_score = (
            sum(s.investment_score for s in result.scored) / len(result.scored)
            if result.scored
            else 0.0
        )
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO searches (
                    timestamp, city, state, budget_min, budget_max,
                    total_properties, avg_score, elapsed_seconds, provider, model, payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.timestamp.isoformat(),
                    result.criteria.city,
                    result.criteria.state,
                    result.criteria.min_price,
                    result.criteria.max_price,
                    result.total_properties,
                    round(avg_score, 1),
                    result.elapsed_seconds,
                    result.provider,
                    result.model,
                    result.model_dump_json(),
                ),
            )
            return int(cursor.lastrowid or 0)

    def list_recent(self, limit: int = 25) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, timestamp, city, state, budget_min, budget_max,
                       total_properties, avg_score, elapsed_seconds, provider, model
                FROM searches
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def load(self, search_id: int) -> Optional[AnalysisResult]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM searches WHERE id = ?", (search_id,)
            ).fetchone()
        if not row:
            return None
        try:
            return AnalysisResult.model_validate_json(row["payload"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to deserialize search %s: %s", search_id, exc)
            return None

    def delete(self, search_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM searches WHERE id = ?", (search_id,))
            return cursor.rowcount > 0

    def clear(self) -> int:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM searches")
            return cursor.rowcount

    @staticmethod
    def format_summary(row: dict) -> str:
        ts = row.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts).strftime("%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            pass
        location = f"{row.get('city', '')}".strip()
        if row.get("state"):
            location = f"{location}, {row['state']}"
        budget_min = row.get("budget_min") or 0
        budget_max = row.get("budget_max") or 0
        budget = (
            f"${budget_min:,}–${budget_max:,}" if budget_max else "Any budget"
        )
        return (
            f"#{row.get('id')} • {ts} • {location} • {budget} • "
            f"{row.get('total_properties', 0)} props • avg {row.get('avg_score', 0)}"
        )
