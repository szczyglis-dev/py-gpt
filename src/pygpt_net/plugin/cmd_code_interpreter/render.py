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

"""Code Interpreter input/output presentation rules."""

from pygpt_net.plugin.base.render import BaseToolRender, render_execution


class Render(BaseToolRender):
    tools = ('python_exec', 'python_exec_file', 'python_exec_all', 'python_sys_exec',
             'ipython_exec', 'ipython_sys_exec')

    def get_rules(self):
        return {name: {
            'input': {'parser': render_execution,
                      'language': 'bash' if name in ('python_sys_exec', 'ipython_sys_exec') else 'python'},
            'output': {'parser': render_execution, 'language': 'text'},
        } for name in self.tools}
