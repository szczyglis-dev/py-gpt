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
from .base import BaseEvent


@dataclass(slots=True)
class Event(BaseEvent):
    """Generic event with context serialization"""
    # static id for event family
    id: ClassVar[str] = "Event"

    # Events
    AI_NAME = "ai.name"
    AGENT_PROMPT = "agent.prompt"  # on agent prompt
    AUDIO_INPUT_RECORD_START = "audio.input.record.start"  # start audio input recording
    AUDIO_INPUT_RECORD_STOP = "audio.input.record.stop"  # stop audio input recording
    AUDIO_INPUT_RECORD_TOGGLE = "audio.input.record.toggle"  # toggle audio input recording
    AUDIO_INPUT_STOP = "audio.input.stop"
    AUDIO_INPUT_TOGGLE = "audio.input.toggle"
    AUDIO_INPUT_TRANSCRIBE = "audio.input.transcribe"  # transcribe audio file
    AUDIO_OUTPUT_STOP = "audio.output.stop"
    AUDIO_OUTPUT_TOGGLE = "audio.output.toggle"
    AUDIO_PLAYBACK = "audio.playback"
    AUDIO_READ_TEXT = "audio.read_text"
    BRIDGE_BEFORE = "bridge.before"
    CMD_EXECUTE = "cmd.execute"
    CMD_INLINE = "cmd.inline"
    CMD_SYNTAX = "cmd.syntax"
    CMD_SYNTAX_INLINE = "cmd.syntax.inline"
    CTX_AFTER = "ctx.after"
    CTX_BEFORE = "ctx.before"
    CTX_BEGIN = "ctx.begin"
    CTX_END = "ctx.end"
    CTX_SELECT = "ctx.select"
    DISABLE = "disable"
    ENABLE = "enable"
    FORCE_STOP = "force.stop"
    INPUT_ACCEPT = "input.accept"
    INPUT_BEFORE = "input.before"
    INPUT_BEGIN = "input.begin"
    MODE_BEFORE = "mode.before"
    MODE_SELECT = "mode.select"
    MODEL_BEFORE = "model.before"
    MODEL_SELECT = "model.select"
    MODELS_CHANGED = "models.changed"
    PLUGIN_OPTION_GET = "plugin.option.get"
    PLUGIN_SETTINGS_CHANGED = "plugin.settings.changed"
    POST_PROMPT = "post.prompt"
    POST_PROMPT_ASYNC = "post.prompt.async"
    POST_PROMPT_END = "post.prompt.end"
    PRE_PROMPT = "pre.prompt"
    SETTINGS_CHANGED = "settings.changed"
    SYSTEM_PROMPT = "system.prompt"
    TOOL_OUTPUT_RENDER = "tool.output.render"
    UI_ATTACHMENTS = "ui.attachments"
    UI_VISION = "ui.vision"
    USER_NAME = "user.name"
    USER_SEND = "user.send"