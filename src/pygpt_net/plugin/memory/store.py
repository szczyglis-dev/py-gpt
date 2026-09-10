#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.09 19:45:00                  #
# ================================================== #

import time
from typing import Optional

from sqlalchemy import text


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
