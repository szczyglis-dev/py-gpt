#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.08 17:00:00                  #
# ================================================== #

from datetime import datetime


class Tab:

    # types
    TAB_ADD = -1
    TAB_CHAT = 0
    TAB_NOTEPAD = 1
    TAB_FILES = 2
    TAB_TOOL_PAINTER = 3
    TAB_TOOL_CALENDAR = 4

    def __init__(self):
        """
        Tab data
        """
        self.uuid = None
        self.pid = None
        self.idx = 0
        self.type = 0
        self.title = ""
        self.icon = None
        self.tooltip = None
        self.data_id = None
        self.reference = None
        self.new_idx = None
        self.custom_name = False

        dt = datetime.now()
        self.created_at = dt
        self.updated_at = dt

    def to_dict(self):
        return {
            "uuid": str(self.uuid),
            "pid": self.pid,
            "idx": self.idx,
            "type": self.type,
            "title": self.title,
            "icon": self.icon,
            "tooltip": self.tooltip,
            "data_id": self.data_id,
            "reference": str(self.reference),
            "custom_name": self.custom_name,
            "custom_idx": self.new_idx,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
        }