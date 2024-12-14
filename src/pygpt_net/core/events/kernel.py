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


class KernelEvent(BaseEvent):
    """Kernel events"""

    # core, events sent from kernel
    INIT = "kernel.init"
    RESTART = "kernel.restart"
    STOP = "kernel.stop"
    TERMINATE = "kernel.terminate"

    # input
    INPUT_SYSTEM = "kernel.input.system"
    INPUT_USER = "kernel.input.user"

    # queue
    AGENT_CALL = "kernel.agent.call"
    AGENT_CONTINUE = "kernel.agent.continue"
    APPEND_BEGIN = "kernel.append.begin"
    APPEND_DATA = "kernel.append.data"
    APPEND_END = "kernel.append.end"
    CALL = "kernel.call"
    REQUEST = "kernel.request"
    REQUEST_NEXT = "kernel.request.next"
    RESPONSE_ERROR = "kernel.response.error"
    RESPONSE_FAILED = "kernel.response.failed"
    RESPONSE_OK = "kernel.response.OK"
    TOOL_CALL = "kernel.tool.call"

    # reply
    REPLY_ADD = "kernel.reply.add"
    REPLY_RETURN = "kernel.reply.return"

    # state
    STATE = "kernel.state"
    STATE_BUSY = "kernel.state.busy"
    STATE_IDLE = "kernel.state.idle"
    STATE_ERROR = "kernel.state.error"
    STATUS = "kernel.status"

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
        super(KernelEvent, self).__init__(name, data)
        self.id = "KernelEvent"
