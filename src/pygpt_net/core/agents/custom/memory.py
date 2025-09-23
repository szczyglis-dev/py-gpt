#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.24 23:00:00                  #
# ================================================== #

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from agents import TResponseInputItem


@dataclass
class MemoryState:
    """Holds conversation items and last response id for a memory node."""
    mem_id: str
    items: List[TResponseInputItem] = field(default_factory=list)
    last_response_id: Optional[str] = None

    def is_empty(self) -> bool:
        return not self.items

    def set_from(self, items: List[TResponseInputItem], last_response_id: Optional[str]) -> None:
        self.items = list(items or [])
        self.last_response_id = last_response_id

    def update_from_result(self, items: List[TResponseInputItem], last_response_id: Optional[str]) -> None:
        self.set_from(items, last_response_id)


class MemoryManager:
    """Manages MemoryState instances keyed by memory node id."""
    def __init__(self) -> None:
        self._mem: Dict[str, MemoryState] = {}

    def get(self, mem_id: str) -> MemoryState:
        if mem_id not in self._mem:
            self._mem[mem_id] = MemoryState(mem_id=mem_id)
        return self._mem[mem_id]

    def set(self, mem_id: str, items: List[TResponseInputItem], last_response_id: Optional[str]) -> None:
        self.get(mem_id).set_from(items, last_response_id)

    def snapshot(self) -> Dict[str, MemoryState]:
        return dict(self._mem)