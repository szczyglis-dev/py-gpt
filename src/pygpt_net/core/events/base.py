#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.04 00:00:00                  #
# ================================================== #

import json
from dataclasses import dataclass
from typing import Optional, Dict, Any, ClassVar

from pygpt_net.item.ctx import CtxItem


@dataclass(slots=True)
class BaseEvent:
    """Base Event object class"""
    id: ClassVar[str] = None
    name: Optional[str] = None
    data: Optional[dict] = None
    ctx: Optional[CtxItem] = None  # CtxItem
    stop: bool = False  # True to stop propagation
    internal: bool = False
    call_id: int = 0

    def __post_init__(self):
        # Normalize None to empty dict for convenience and safety
        if self.data is None:
            self.data = {}

    @property
    def full_name(self) -> str:
        """
        Get full event name

        :return: Full event name
        """
        return self.id + ": " + self.name  # type: ignore[operator]

    def to_dict(self) -> Dict[str, Any]:
        """Dump event to dict"""
        return {
            'name': self.name,
            'data': self.data,
            'stop': self.stop,
            'internal': self.internal,
        }

    def dump(self) -> str:
        """
        Dump event to json string

        :return: JSON string
        """
        try:
            return json.dumps(self.to_dict())
        except Exception:
            pass
        return ""

    def __str__(self):
        return self.dump()