#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

from typing import Optional

from .base import BaseEvent


class RenderEvent(BaseEvent):
    """Events used for rendering"""
    BEGIN = "render.begin"
    END = "render.end"
    RELOAD = "render.reload"
    RESET = "render.reset"
    PREPARE = "render.prepare"

    STREAM_BEGIN = "render.stream.begin"
    STREAM_APPEND = "render.stream.append"
    STREAM_END = "render.stream.end"

    CLEAR = "render.clear"
    CLEAR_ALL = "render.clear.all"
    CLEAR_INPUT = "render.clear.input"
    CLEAR_OUTPUT = "render.clear.output"

    INPUT_APPEND = "render.input.append"
    OUTPUT_APPEND = "render.output.append"
    CTX_APPEND = "render.ctx.append"

    EXTRA_BEGIN = "render.extra.begin"
    EXTRA_APPEND = "render.extra.append"
    EXTRA_END = "render.extra.end"

    ON_LOAD = "render.on.load"
    ON_PAGE_LOAD = "render.on.page.load"
    ON_THEME_CHANGE = "render.on.theme.change"
    ON_EDIT_ENABLE = "render.on.edit.enable"
    ON_EDIT_DISABLE = "render.on.edit.disable"
    ON_TS_ENABLE = "render.on.ts.enable"
    ON_TS_DISABLE = "render.on.ts.disable"
    ON_SWITCH = "render.on.switch"

    TOOL_BEGIN = "render.tool.begin"
    TOOL_UPDATE = "render.tool.update"
    TOOL_CLEAR = "render.tool.clear"
    TOOL_END = "render.tool.end"

    ACTION_REGEN_SUBMIT = "render.action.regen.submit"
    ACTION_EDIT_SUBMIT = "render.action.edit.submit"

    def __init__(
            self,
            name: Optional[str] = None,
            data: Optional[dict] = None,
    ):
        """
        Event object class

        :param name: event name
        :param data: event data
        """
        super(RenderEvent, self).__init__(name, data)
        self.id = "RenderEvent"