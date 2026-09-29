#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.07 12:00:00                  #
# ================================================== #

import time
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import uuid4


@dataclass(slots=True)
class CtxItemPartTask:
    """One executable/logical task belonging to a context partial item."""

    id: Optional[int] = None
    uuid: str = field(default_factory=lambda: str(uuid4()))
    parent_item_part_id: Optional[int] = None
    agent_id: Optional[str] = None
    name: Optional[str] = None
    task_name: Optional[str] = None
    task_summary: Optional[str] = None
    input: Optional[str] = None
    output: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_input: Any = field(default_factory=dict)
    tool_output: Any = None
    extra: dict = field(default_factory=dict)
    created_at: int = field(default_factory=lambda: int(time.time()))
    updated_at: int = field(default_factory=lambda: int(time.time()))

    def touch(self):
        self.updated_at = int(time.time())

    def set_result(self, result: Any, output: Optional[str] = None):
        self.tool_output = result
        if output is not None:
            self.output = output
        elif result is not None:
            self.output = result if isinstance(result, str) else str(result)
        if not isinstance(self.extra, dict):
            self.extra = {}
        self.extra["status"] = "completed"
        self.touch()

    def mark_ui_ready(self, ready: bool = True):
        if not isinstance(self.extra, dict):
            self.extra = {}
        self.extra["ui_ready"] = bool(ready)
        self.touch()

    def is_ui_ready(self) -> bool:
        return bool(isinstance(self.extra, dict) and self.extra.get("ui_ready"))
