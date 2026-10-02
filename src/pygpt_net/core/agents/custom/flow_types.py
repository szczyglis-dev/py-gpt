#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.27 06:00:00                  #
# ================================================== #

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from pygpt_net.item.ctx import CtxItem

@dataclass
class FlowResult:
    ctx: CtxItem
    final_output: str
    last_response_id: Optional[str]


@dataclass
class DebugConfig:
    log_runtime: bool = True
    log_routes: bool = True
    log_inputs: bool = False
    log_outputs: bool = False
    preview_chars: int = 280


@dataclass
class FlowOptions:
    agent_kwargs: dict
    preset: Any
    model: Any
    stream: bool
    use_partial_ctx: bool
    base_prompt: Optional[str]
    system_prompt_extra: Optional[str]
    allow_local_tools: bool
    allow_remote_tools: bool
    function_tools: list
    max_iterations: int
    router_stream_mode: str
    option_get: Any


@dataclass
class PreparedStep:
    built: Any
    run_kwargs: dict
    baton: str
    memory_state: Any


@dataclass
class StepOutput:
    text: str
    response_id: Optional[str]
    decision: Any = None
    router_mode: str = "off"
