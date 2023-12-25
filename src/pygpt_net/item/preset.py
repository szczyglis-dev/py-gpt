#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #


class PresetItem:
    def __init__(self):
        self.name = "*"
        self.ai_name = ""
        self.user_name = ""
        self.prompt = ""
        self.chat = False
        self.completion = False
        self.img = False
        self.vision = False
        self.langchain = False
        self.assistant = False
        self.temperature = 1.0
        self.filename = None
        self.version = None
