#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.11 15:15:00                  #
# ================================================== #

import time
from typing import Optional

from sqlalchemy import bindparam, text
from sqlalchemy.exc import IntegrityError


class Store:
    """SQLite-backed memory store with one row per scope."""

    def __init__(self, window=None):
        self.window = window

    def _engine(self):
        db = self.window.core.db
        db.init()
        return db.get_db()

    def get(self, project_id: Optional[int] = None) -> str:
        engine = self._engine()
        with engine.connect() as conn:
            if project_id is None:
                stmt = text("SELECT content FROM memory WHERE project_id IS NULL LIMIT 1")
                row = conn.execute(stmt).fetchone()
            else:
                stmt = text("SELECT content FROM memory WHERE project_id = :project_id LIMIT 1")
                row = conn.execute(stmt, {"project_id": int(project_id)}).fetchone()
        return str(row[0] or "") if row else ""

    def set(self, content: str, project_id: Optional[int] = None) -> str:
        content = str(content or "")
        ts = int(time.time())
        engine = self._engine()
        with engine.begin() as conn:
            if project_id is None:
                row = conn.execute(text("SELECT id FROM memory WHERE project_id IS NULL LIMIT 1")).fetchone()
            else:
                row = conn.execute(
                    text("SELECT id FROM memory WHERE project_id = :project_id LIMIT 1"),
                    {"project_id": int(project_id)},
                ).fetchone()

            if row:
                conn.execute(
                    text("UPDATE memory SET content = :content, updated_at = :updated_at WHERE id = :id"),
                    {"content": content, "updated_at": ts, "id": int(row[0])},
                )
            else:
                conn.execute(
                    text(
                        "INSERT INTO memory (project_id, updated_at, content) "
                        "VALUES (:project_id, :updated_at, :content)"
                    ),
                    {"project_id": project_id, "updated_at": ts, "content": content},
                )
        return content

    def add(self, content: str, project_id: Optional[int] = None) -> str:
        current = self.get(project_id)
        addition = str(content or "").strip()
        if not addition:
            return current
        updated = addition if not current.strip() else current.rstrip() + "\n" + addition
        return self.set(updated, project_id)

    def clear(self, project_id: Optional[int] = None) -> bool:
        engine = self._engine()
        with engine.begin() as conn:
            if project_id is None:
                result = conn.execute(text("DELETE FROM memory WHERE project_id IS NULL"))
            else:
                result = conn.execute(
                    text("DELETE FROM memory WHERE project_id = :project_id"),
                    {"project_id": int(project_id)},
                )
        return bool(result.rowcount)


class KeyStore:
    """SQLite-backed raw key/value memory store, isolated per global/project scope."""

    COLUMNS = "id, project_id, key, updated_at, content"

    def __init__(self, window=None):
        self.window = window

    def _engine(self):
        db = self.window.core.db
        db.init()
        return db.get_db()

    @staticmethod
    def _normalize_key(key) -> str:
        value = str(key or "").strip()
        if not value:
            raise ValueError("Memory key cannot be empty.")
        return value

    @classmethod
    def _normalize_keys(cls, keys) -> list[str]:
        if keys is None:
            return []
        if not isinstance(keys, (list, tuple, set)):
            keys = [keys]
        result = []
        seen = set()
        for key in keys:
            value = cls._normalize_key(key)
            if value not in seen:
                result.append(value)
                seen.add(value)
        return result

    @staticmethod
    def _row_to_dict(row) -> Optional[dict]:
        if row is None:
            return None
        mapping = row._mapping
        return {
            "id": int(mapping["id"]),
            "project_id": mapping["project_id"],
            "key": str(mapping["key"]),
            "updated_at": int(mapping["updated_at"] or 0),
            "content": str(mapping["content"] or ""),
        }

    @staticmethod
    def _scope_clause(project_id: Optional[int]) -> tuple[str, dict]:
        if project_id is None:
            return "project_id IS NULL", {}
        return "project_id = :project_id", {"project_id": int(project_id)}

    def get(self, keys, project_id: Optional[int] = None) -> list[dict]:
        keys = self._normalize_keys(keys)
        if not keys:
            return []
        scope_sql, params = self._scope_clause(project_id)
        stmt = text(
            f"SELECT {self.COLUMNS} FROM memory_keys "
            f"WHERE {scope_sql} AND key IN :keys"
        ).bindparams(bindparam("keys", expanding=True))
        params["keys"] = keys
        engine = self._engine()
        with engine.connect() as conn:
            rows = conn.execute(stmt, params).fetchall()
        found = {str(row._mapping["key"]): self._row_to_dict(row) for row in rows}
        return [found[key] for key in keys if key in found]

    def get_one(self, key, project_id: Optional[int] = None) -> Optional[dict]:
        rows = self.get([key], project_id)
        return rows[0] if rows else None

    def add(self, key, content, project_id: Optional[int] = None) -> dict:
        key = self._normalize_key(key)
        content = str(content if content is not None else "")
        ts = int(time.time())
        engine = self._engine()
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "INSERT INTO memory_keys (project_id, key, updated_at, content) "
                        "VALUES (:project_id, :key, :updated_at, :content)"
                    ),
                    {
                        "project_id": project_id,
                        "key": key,
                        "updated_at": ts,
                        "content": content,
                    },
                )
        except IntegrityError as exc:
            raise ValueError(
                f"Memory key already exists: {key}. Use memory_key_update or memory_key_append."
            ) from exc
        return self.get_one(key, project_id)

    def append(self, key, content, project_id: Optional[int] = None) -> dict:
        key = self._normalize_key(key)
        addition = str(content if content is not None else "")
        ts = int(time.time())
        scope_sql, params = self._scope_clause(project_id)
        params.update({"key": key, "content": addition, "updated_at": ts})
        engine = self._engine()
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    "UPDATE memory_keys "
                    "SET content = content || :content, updated_at = :updated_at "
                    f"WHERE {scope_sql} AND key = :key"
                ),
                params,
            )
        if not result.rowcount:
            raise ValueError(f"Memory key not found: {key}.")
        return self.get_one(key, project_id)

    def update(self, key, content, project_id: Optional[int] = None) -> dict:
        key = self._normalize_key(key)
        value = str(content if content is not None else "")
        ts = int(time.time())
        scope_sql, params = self._scope_clause(project_id)
        params.update({"key": key, "content": value, "updated_at": ts})
        engine = self._engine()
        with engine.begin() as conn:
            result = conn.execute(
                text(
                    "UPDATE memory_keys SET content = :content, updated_at = :updated_at "
                    f"WHERE {scope_sql} AND key = :key"
                ),
                params,
            )
        if not result.rowcount:
            raise ValueError(f"Memory key not found: {key}.")
        return self.get_one(key, project_id)

    def list_keys(self, project_id: Optional[int] = None) -> list[str]:
        scope_sql, params = self._scope_clause(project_id)
        engine = self._engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text(f"SELECT key FROM memory_keys WHERE {scope_sql} ORDER BY key ASC"),
                params,
            ).fetchall()
        return [str(row[0]) for row in rows]

    def search(
            self,
            query: str,
            project_id: Optional[int] = None,
            search_content: bool = False,
    ) -> list[dict]:
        query = str(query or "")
        if not query:
            return []
        scope_sql, params = self._scope_clause(project_id)
        params["query"] = f"%{query}%"
        search_sql = "key LIKE :query"
        if search_content:
            search_sql = "(key LIKE :query OR content LIKE :query)"
        engine = self._engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT {self.COLUMNS} FROM memory_keys "
                    f"WHERE {scope_sql} AND {search_sql} ORDER BY key ASC"
                ),
                params,
            ).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def remove(self, keys, project_id: Optional[int] = None) -> list[str]:
        keys = self._normalize_keys(keys)
        if not keys:
            return []
        existing = self.get(keys, project_id)
        removed = [row["key"] for row in existing]
        if not removed:
            return []
        scope_sql, params = self._scope_clause(project_id)
        stmt = text(
            f"DELETE FROM memory_keys WHERE {scope_sql} AND key IN :keys"
        ).bindparams(bindparam("keys", expanding=True))
        params["keys"] = removed
        engine = self._engine()
        with engine.begin() as conn:
            conn.execute(stmt, params)
        return removed
