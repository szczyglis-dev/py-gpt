#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.31 23:00:00                  #
# ================================================== #

from enum import Enum

class TurnMode(str, Enum):
    MANUAL = "manual"
    AUTO = "auto"  # future (server VAD / automatic activity detection)

def apply_turn_mode_openai(session_payload: dict, mode: TurnMode):
    """
    Mutate OpenAI session.update payload to reflect turn mode.
    Manual: turn_detection=None (default).
    Auto: enable server VAD if available.
    """
    sess = session_payload.setdefault("session", {})
    if mode == TurnMode.AUTO:
        sess["turn_detection"] = {"type": "server_vad"}
    else:
        sess["turn_detection"] = None

def apply_turn_mode_google(live_cfg: dict, mode: TurnMode):
    """
    Mutate Google Live connect config to reflect turn mode.
    Manual: automatic_activity_detection.disabled=True
    Auto: disabled=False (server handles VAD).
    """
    ri = live_cfg.setdefault("realtime_input_config", {})
    aad = ri.setdefault("automatic_activity_detection", {})
    aad["disabled"] = (mode != TurnMode.AUTO)