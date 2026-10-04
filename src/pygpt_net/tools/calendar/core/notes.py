#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #
"""Headless date-based note operations, shared by all frontends."""
import datetime

class Notes:
    def __init__(self, tool):
        self.tool = tool

    def append_today(self, text):
        text = '' if text is None else str(text).strip()
        if not text:
            return
        today = datetime.date.today()
        self.tool.storage.append_to_note(today.year, today.month, today.day, text)
        self.tool.refresh_notes()
