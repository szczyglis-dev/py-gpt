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

from dataclasses import dataclass
from typing import Optional, ClassVar

from .base import BaseEvent
from ...item.ctx import CtxItem


@dataclass(slots=True)
class RenderEvent(BaseEvent):
    """Events used for rendering"""
    # static id for event family
    id: ClassVar[str] = "RenderEvent"

    BEGIN = "render.begin"
    END = "render.end"
    FRESH = "render.fresh"
    PREPARE = "render.prepare"
    RELOAD = "render.reload"
    RESET = "render.reset"

    STREAM_APPEND = "render.stream.append"
    STREAM_BEGIN = "render.stream.begin"
    STREAM_END = "render.stream.end"
    STREAM_NEXT = "render.stream.next"

    CLEAR = "render.clear"
    CLEAR_ALL = "render.clear.all"
    CLEAR_INPUT = "render.clear.input"
    CLEAR_OUTPUT = "render.clear.output"

    CTX_APPEND = "render.ctx.append"
    INPUT_APPEND = "render.input.append"
    OUTPUT_APPEND = "render.output.append"

    EXTRA_APPEND = "render.extra.append"
    EXTRA_BEGIN = "render.extra.begin"
    EXTRA_END = "render.extra.end"

    ON_EDIT_DISABLE = "render.on.edit.disable"
    ON_EDIT_ENABLE = "render.on.edit.enable"
    ON_LOAD = "render.on.load"
    ON_PAGE_LOAD = "render.on.page.load"
    ON_SWITCH = "render.on.switch"
    ON_THEME_CHANGE = "render.on.theme.change"
    ON_TS_DISABLE = "render.on.ts.disable"
    ON_TS_ENABLE = "render.on.ts.enable"

    TOOL_BEGIN = "render.tool.begin"
    TOOL_CLEAR = "render.tool.clear"
    TOOL_END = "render.tool.end"
    TOOL_UPDATE = "render.tool.update"

    ACTION_EDIT_SUBMIT = "render.action.edit.submit"
    ACTION_REGEN_SUBMIT = "render.action.regen.submit"

    ITEM_DELETE_ID = "render.item.delete.id"
    ITEM_DELETE_FROM_ID = "render.item.delete.from_id"

    STATE_BUSY = "render.state.busy"
    STATE_ERROR = "render.state.error"
    STATE_IDLE = "render.state.idle"

    LIVE_APPEND = "render.live.append"
    LIVE_CLEAR = "render.live.clear"