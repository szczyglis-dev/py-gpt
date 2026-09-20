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
from typing import Optional
from uuid import uuid4

from .ctx_part_task import CtxItemPartTask


@dataclass(slots=True)
class CtxItemPart:
    """A durable logical fragment of one user-visible context turn."""

    id: Optional[int] = None
    uuid: str = field(default_factory=lambda: str(uuid4()))
    parent_item_id: Optional[int] = None
    agent_id: Optional[str] = None
    name: Optional[str] = None
    output: Optional[str] = None
    extra: dict = field(default_factory=dict)
    created_at: int = field(default_factory=lambda: int(time.time()))
    updated_at: int = field(default_factory=lambda: int(time.time()))
    tasks: list[CtxItemPartTask] = field(default_factory=list)

    def touch(self):
        self.updated_at = int(time.time())

    def set_output(self, output: Optional[str]):
        self.output = output
        self.touch()

    def append_output(self, output: Optional[str]):
        if not output:
            return
        if self.output is None:
            self.output = ""
        self.output += str(output)
        self.touch()

    def add_task(self, task: CtxItemPartTask):
        if task not in self.tasks:
            self.tasks.append(task)
        self.touch()
