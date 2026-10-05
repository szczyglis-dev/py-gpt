#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.02 14:00:00                  #
# ================================================== #

"""System/OS input/output presentation rules."""
from pygpt_net.plugin.base.render import BaseToolRender, render_execution


class Render(BaseToolRender):
    tools = ('shell_exec',)

    def get_rules(self):
        return {'shell_exec': {
            'input': {'parser': render_execution, 'language': 'bash'},
            'output': {'parser': render_execution, 'language': 'text'},
        }}
