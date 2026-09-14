#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import time
from typing import Optional

from sqlalchemy import text


class ContextMemoryStore:
    """DB-backed compact continuation memory, one row per conversation meta."""

    def __init__(self, window=None):
        self.window = window

    def _engine(self):
        db = self.window.core.db
        db.init()
        return db.get_db()

    @staticmethod
    def _meta_id(meta_id) -> int:
        try:
            value = int(meta_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Conversation meta id is required.") from exc
        if value <= 0:
            raise ValueError("Conversation meta id is required.")
        return value

    @staticmethod
    def _row(row) -> dict:
        if row is None:
            return {
                "id": None,
                "meta_id": None,
                "updated_at": 0,
                "last_item_id": 0,
                "generation": 0,
                "revision": 0,
                "content": "",
            }
        m = row._mapping
        return {
            "id": int(m["id"]),
            "meta_id": int(m["meta_id"]),
            "updated_at": int(m["updated_at"] or 0),
            "last_item_id": int(m["last_item_id"] or 0),
            "generation": int(m["generation"] or 0),
            "revision": int(m["revision"] or 0),
            "content": str(m["content"] or ""),
        }

    def get(self, meta_id) -> dict:
        meta_id = self._meta_id(meta_id)
        with self._engine().connect() as conn:
            row = conn.execute(text(
                "SELECT id, meta_id, updated_at, last_item_id, generation, revision, content "
                "FROM memory_ctx WHERE meta_id = :meta_id LIMIT 1"
            ), {"meta_id": meta_id}).fetchone()
        data = self._row(row)
        if data["meta_id"] is None:
            data["meta_id"] = meta_id
        return data

    def content(self, meta_id) -> str:
        return self.get(meta_id)["content"]

    def _write(self, meta_id: int, content: str, *, last_item_id: Optional[int] = None,
               generation: Optional[int] = None) -> dict:
        meta_id = self._meta_id(meta_id)
        content = str(content or "")
        now = int(time.time())
        engine = self._engine()
        with engine.begin() as conn:
            row = conn.execute(text(
                "SELECT id, last_item_id, generation, revision FROM memory_ctx "
                "WHERE meta_id = :meta_id LIMIT 1"
            ), {"meta_id": meta_id}).fetchone()
            if row:
                m = row._mapping
                conn.execute(text(
                    "UPDATE memory_ctx SET content = :content, updated_at = :updated_at, "
                    "last_item_id = :last_item_id, generation = :generation, revision = :revision "
                    "WHERE id = :id"
                ), {
                    "content": content,
                    "updated_at": now,
                    "last_item_id": int(m["last_item_id"] or 0) if last_item_id is None else int(last_item_id or 0),
                    "generation": int(m["generation"] or 0) if generation is None else int(generation or 0),
                    "revision": int(m["revision"] or 0) + 1,
                    "id": int(m["id"]),
                })
            else:
                conn.execute(text(
                    "INSERT INTO memory_ctx (meta_id, updated_at, last_item_id, generation, revision, content) "
                    "VALUES (:meta_id, :updated_at, :last_item_id, :generation, 1, :content)"
                ), {
                    "meta_id": meta_id,
                    "updated_at": now,
                    "last_item_id": int(last_item_id or 0),
                    "generation": int(generation or 0),
                    "content": content,
                })
        return self.get(meta_id)

    def replace(self, meta_id, content: str) -> str:
        return self._write(meta_id, str(content or ""))["content"]

    def add(self, meta_id, content: str) -> str:
        addition = str(content or "").strip()
        current = self.get(meta_id)
        if not addition:
            return current["content"]
        previous = current["content"].rstrip()
        merged = addition if not previous else previous + "\n" + addition
        return self._write(meta_id, merged)["content"]


    def runtime_summary(
            self,
            meta_id,
            content: str,
            expected_revision: int,
            last_item_id: int = 0,
    ) -> Optional[dict]:
        """Atomically store an in-run rolling summary.

        ``last_item_id`` is optional.  When it advances, the corresponding
        durable turns are now represented by ``content`` and a new context
        generation is created so stateful provider chains are broken on the
        next top-level request.  A revision mismatch means a manual/tool edit
        won the race; callers should re-merge against the newest notes rather
        than overwriting them.
        """
        meta_id = self._meta_id(meta_id)
        last_item_id = max(0, int(last_item_id or 0))
        expected_revision = int(expected_revision or 0)
        now = int(time.time())
        engine = self._engine()
        with engine.begin() as conn:
            row = conn.execute(text(
                "SELECT id, last_item_id, generation, revision FROM memory_ctx "
                "WHERE meta_id = :meta_id LIMIT 1"
            ), {"meta_id": meta_id}).fetchone()
            if row:
                m = row._mapping
                current_revision = int(m["revision"] or 0)
                if current_revision != expected_revision:
                    return None
                current_floor = int(m["last_item_id"] or 0)
                new_floor = max(current_floor, last_item_id)
                current_generation = int(m["generation"] or 0)
                new_generation = current_generation + (1 if new_floor > current_floor else 0)
                result = conn.execute(text(
                    "UPDATE memory_ctx SET content = :content, updated_at = :updated_at, "
                    "last_item_id = :last_item_id, generation = :generation, revision = :revision "
                    "WHERE id = :id AND revision = :expected_revision"
                ), {
                    "content": str(content or ""),
                    "updated_at": now,
                    "last_item_id": new_floor,
                    "generation": new_generation,
                    "revision": current_revision + 1,
                    "expected_revision": current_revision,
                    "id": int(m["id"]),
                })
                if not result.rowcount:
                    return None
            else:
                if expected_revision != 0:
                    return None
                conn.execute(text(
                    "INSERT INTO memory_ctx (meta_id, updated_at, last_item_id, generation, revision, content) "
                    "VALUES (:meta_id, :updated_at, :last_item_id, :generation, 1, :content)"
                ), {
                    "meta_id": meta_id,
                    "updated_at": now,
                    "last_item_id": last_item_id,
                    "generation": 1 if last_item_id > 0 else 0,
                    "content": str(content or ""),
                })
        return self.get(meta_id)

    def checkpoint(self, meta_id, content: str, last_item_id: int,
                   expected_revision: int) -> Optional[dict]:
        """Atomically advance a checkpoint without overwriting a concurrent manual edit."""
        meta_id = self._meta_id(meta_id)
        now = int(time.time())
        engine = self._engine()
        with engine.begin() as conn:
            row = conn.execute(text(
                "SELECT id, generation, revision FROM memory_ctx WHERE meta_id = :meta_id LIMIT 1"
            ), {"meta_id": meta_id}).fetchone()
            if row:
                m = row._mapping
                if int(m["revision"] or 0) != int(expected_revision or 0):
                    return None
                result = conn.execute(text(
                    "UPDATE memory_ctx SET content = :content, updated_at = :updated_at, "
                    "last_item_id = :last_item_id, generation = :generation, revision = :revision "
                    "WHERE id = :id AND revision = :expected_revision"
                ), {
                    "content": str(content or ""),
                    "updated_at": now,
                    "last_item_id": int(last_item_id or 0),
                    "generation": int(m["generation"] or 0) + 1,
                    "revision": int(expected_revision or 0) + 1,
                    "expected_revision": int(expected_revision or 0),
                    "id": int(m["id"]),
                })
                if not result.rowcount:
                    return None
            else:
                if int(expected_revision or 0) != 0:
                    return None
                conn.execute(text(
                    "INSERT INTO memory_ctx (meta_id, updated_at, last_item_id, generation, revision, content) "
                    "VALUES (:meta_id, :updated_at, :last_item_id, 1, 1, :content)"
                ), {
                    "meta_id": meta_id,
                    "updated_at": now,
                    "last_item_id": int(last_item_id or 0),
                    "content": str(content or ""),
                })
        return self.get(meta_id)
