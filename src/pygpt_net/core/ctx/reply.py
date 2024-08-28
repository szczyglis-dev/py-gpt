#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.28 20:00:00                  #
# ================================================== #

class ReplyContext:

    AGENT_CONTINUE = "agent.continue"
    CMD_EXECUTE = "cmd.execute"
    CMD_EXECUTE_INLINE = "cmd.execute.inline"
    EXPERT_CALL = "expert.call"
    EXPERT_RESPONSE = "expert.response"

    def __init__(self):
        """Reply context"""
        self.type = None
        self.bridge_context = None
        self.ctx = None
        self.prev_ctx = None
        self.parent_id = None
        self.input = ""
        self.cmds = []

    def to_dict(self) -> dict:
        """
        Dump to dictionary

        :return: dict
        """
        data = {
            "type": self.type,
            "bridge_context": self.bridge_context,
            "ctx": self.ctx,
            "prev_ctx": self.prev_ctx,
            "parent_id": self.parent_id,
            "input": self.input,
            "cmds": self.cmds,
        }
        if self.bridge_context is not None:
            data["bridge_context"] = self.bridge_context.to_dict()
        if self.ctx is not None:
            data["ctx"] = self.ctx.to_dict()
        if self.prev_ctx is not None:
            data["prev_ctx"] = self.prev_ctx.to_dict()
        return data

class Reply:
    def __init__(self, window=None):
        """
        Reply core

        :param window: Window instance
        """
        self.window = window