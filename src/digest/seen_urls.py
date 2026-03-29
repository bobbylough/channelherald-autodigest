from __future__ import annotations

import sqlite3


class SeenUrls:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS seen_urls (url TEXT PRIMARY KEY)"
            )

    def contains(self, url: str) -> bool:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM seen_urls WHERE url = ?", (url,)
            ).fetchone()
        return row is not None

    def add(self, url: str) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO seen_urls (url) VALUES (?)", (url,)
            )
