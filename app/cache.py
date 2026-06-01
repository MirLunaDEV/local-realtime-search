from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.fetch.http_fetcher import FetchedPage
from app.search.base import SearchResult


class SearchCache:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                create table if not exists search_cache (
                    cache_key text primary key,
                    created_at real not null,
                    payload text not null
                )
                """
            )
            db.execute(
                """
                create table if not exists page_cache (
                    url text primary key,
                    created_at real not null,
                    payload text not null
                )
                """
            )

    def get_search(self, key: str, ttl_seconds: int) -> list[SearchResult] | None:
        row = self._get("search_cache", "cache_key", key, ttl_seconds)
        if row is None:
            return None
        return [SearchResult(**item) for item in row]

    def set_search(self, key: str, results: list[SearchResult]) -> None:
        self._set("search_cache", "cache_key", key, [asdict(result) for result in results])

    def get_page(self, url: str, ttl_seconds: int) -> FetchedPage | None:
        row = self._get("page_cache", "url", url, ttl_seconds)
        if row is None:
            return None
        return FetchedPage(**row)

    def set_page(self, url: str, page: FetchedPage) -> None:
        self._set("page_cache", "url", url, asdict(page))

    def _get(self, table: str, key_column: str, key: str, ttl_seconds: int) -> Any | None:
        with self._connect() as db:
            row = db.execute(
                f"select created_at, payload from {table} where {key_column} = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        created_at, payload = row
        if time.time() - float(created_at) > ttl_seconds:
            return None
        return json.loads(str(payload))

    def _set(self, table: str, key_column: str, key: str, payload: Any) -> None:
        with self._connect() as db:
            db.execute(
                f"""
                insert into {table} ({key_column}, created_at, payload)
                values (?, ?, ?)
                on conflict({key_column}) do update set
                  created_at=excluded.created_at,
                  payload=excluded.payload
                """,
                (key, time.time(), json.dumps(payload, ensure_ascii=False)),
            )

