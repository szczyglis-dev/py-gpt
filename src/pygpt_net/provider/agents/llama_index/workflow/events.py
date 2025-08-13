#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.14 01:00:00                  #
# ================================================== #

from typing import Optional, Dict, Any
from pydantic import Field

from llama_index.core.workflow import (
    Event,
)

class StepEvent(Event):
    """Represents an event that occurs during a step in the workflow."""
    name: str # eg. "make_plan", "execute_plan", "subtask"
    index: Optional[int] = None
    total: Optional[int] = None
    meta: Dict[str, Any] = Field(default_factory=dict)