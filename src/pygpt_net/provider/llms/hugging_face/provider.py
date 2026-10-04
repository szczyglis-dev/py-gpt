#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 12:00:00                  #
# ================================================== #

from pygpt_net.provider.llms.base import BaseLLM


class HuggingFaceLLM(BaseLLM):
    def __init__(self, *args, **kwargs):
        super(HuggingFaceLLM, self).__init__(*args, **kwargs)
        self.id = "huggingface"
        self.name = "HuggingFace"
        self.type = []
