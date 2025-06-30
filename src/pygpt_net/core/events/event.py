#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.06.30 02:00:00                  #
# ================================================== #

import json
from typing import Optional, Dict, Any

from pygpt_net.item.ctx import CtxItem
from .base import BaseEvent

class Event(BaseEvent):

    # Events
    AI_NAME = "ai.name"
    AGENT_PROMPT = "agent.prompt"  # on agent prompt
    AUDIO_INPUT_RECORD_START = "audio.input.record.start"  # start audio input recording
    AUDIO_INPUT_RECORD_STOP = "audio.input.record.stop"  # stop audio input recording
    AUDIO_INPUT_RECORD_TOGGLE = "audio.input.record.toggle"  # toggle audio input recording
    AUDIO_INPUT_TRANSCRIBE = "audio.input.transcribe"  # transcribe audio file
    AUDIO_INPUT_STOP = "audio.input.stop"
    AUDIO_INPUT_TOGGLE = "audio.input.toggle"
    AUDIO_OUTPUT_STOP = "audio.output.stop"
    AUDIO_OUTPUT_TOGGLE = "audio.output.toggle"
    AUDIO_PLAYBACK = "audio.playback"
    AUDIO_READ_TEXT = "audio.read_text"
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
    INPUT_BEFORE = "input.before"
    MODE_BEFORE = "mode.before"
    MODE_SELECT = "mode.select"
    MODEL_BEFORE = "model.before"
    MODEL_SELECT = "model.select"
    MODELS_CHANGED = "models.changed"
    PLUGIN_SETTINGS_CHANGED = "plugin.settings.changed"
    PLUGIN_OPTION_GET = "plugin.option.get"
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

    def __init__(
            self,
            name: Optional[str] = None,
            data: Optional[dict] = None,
            ctx: Optional[CtxItem] = None
    ):
        """
        Event object class

        :param name: event name
        :param data: event data
        :param ctx: context instance
        """
        super(Event, self).__init__(name, data, ctx)
        self.id = "Event"
        self.name = name
        self.data = data
        if self.data is None:
            self.data = {}
        self.ctx = ctx  # CtxItem
        self.stop = False  # True to stop propagation
        self.internal = False
        # internal event, not called from user
        # internal event is handled synchronously, ctx item has internal flag

    def to_dict(self) -> Dict[str, Any]:
        """
        Dump event to dict

        :return: Event dict
        """
        return {
            'name': self.name,
            'data': self.data,
            'ctx': self.ctx.to_dict() if self.ctx else None,
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
        except Exception as e:
            pass
        return ""

    def __str__(self) -> str:
        """
        String representation of event

        :return: Event string
        """
        return self.dump()