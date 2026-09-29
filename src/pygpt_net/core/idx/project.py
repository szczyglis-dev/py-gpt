#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.04 17:00:00                  #
# ================================================== #

import time
from typing import Optional


class Project:
    VIRTUAL_ID = "__project__"
    PREFIX = "proj_"

    def __init__(self, window=None, provider=None):
        self.window = window
        self.provider = provider

    def get_current_group_id(self) -> Optional[int]:
        meta = self.window.core.ctx.get_current_meta()
        if meta is None:
            return None
        group_id = getattr(meta, "group_id", None)
        if group_id is None or int(group_id) <= 0:
            return None
        return int(group_id)

    def get_idx_id(self, group_id: int) -> str:
        return f"{self.PREFIX}{int(group_id)}"

    def get_group_id_from_idx(self, idx: Optional[str]) -> Optional[int]:
        if not self.is_project_idx(idx):
            return None
        try:
            return int(str(idx)[len(self.PREFIX):])
        except (TypeError, ValueError):
            return None

    def is_virtual(self, idx: Optional[str]) -> bool:
        return idx == self.VIRTUAL_ID

    def is_project_idx(self, idx: Optional[str]) -> bool:
        return bool(idx and str(idx).startswith(self.PREFIX))

    def resolve(self, idx: Optional[str], group_id: Optional[int] = None) -> Optional[str]:
        if not self.is_virtual(idx):
            return idx
        if group_id is None:
            group_id = self.get_current_group_id()
        if group_id is None:
            return None
        return self.get_idx_id(group_id)

    def get(self, group_id: int) -> Optional[dict]:
        return self.provider.get_project(int(group_id))

    def all(self) -> list:
        return self.provider.get_projects()

    def ensure(self, group_id: int) -> bool:
        """Ensure an empty project-index tracking row exists."""
        group_id = int(group_id)
        state = self.get(group_id)
        if state is not None:
            return True
        return self.provider.upsert_project(
            group_id, self.get_idx_id(group_id), 0, 0, 0,
        )

    def touch(self, group_id: int, last_meta: int, last_item: int) -> bool:
        return self.provider.upsert_project(
            int(group_id), self.get_idx_id(group_id), int(last_meta or 0),
            int(last_item or 0), int(time.time()),
        )

    def remove_state(self, group_id: int) -> bool:
        return self.provider.remove_project(int(group_id))

    def clear_states(self) -> bool:
        """Remove all project incremental cursors without deleting indexes."""
        return self.provider.truncate_projects()

    def get_last_update(self, group_id: int) -> int:
        state = self.get(group_id)
        return int(state.get("last_update", 0)) if state else 0

    def get_last_item(self, group_id: int) -> int:
        state = self.get(group_id)
        return int(state.get("last_item", 0)) if state else 0
