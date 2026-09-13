#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczyglinski                  #
# Updated Date: 2026.09.13 15:14:00                  #
# ================================================== #

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from .mode import AgentMode


@dataclass(frozen=True)
class RuntimeInput:
    """Stable high-level input contract for one isolated Agents v2 runtime."""

    window: Any
    context: Any
    extra: Dict[str, Any]
    signals: Any
    emitter: Any


@dataclass(frozen=True)
class RuntimeOutput:
    """Small execution snapshot safe to consume outside runtime internals."""

    run_id: str
    agent_mode: AgentMode
    finished: bool
    final_answer: str
