#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

from pygpt_net.utils import trans
from .summarizer import Summarizer


class Common:
    def __init__(self, window=None):
        """
        Common ctx controller

        :param window: Window instance
        """
        self.window = window
        self.summarizer = Summarizer(window)

    def update_label_by_current(self):
        """Update ctx label from current ctx"""
        mode = self.window.core.ctx.mode

        # if no ctx mode then use current mode
        if mode is None:
            mode = self.window.core.config.get('mode')

        label = trans('mode.' + mode)

        # append assistant name to ctx name label
        if mode == 'assistant':
            id = self.window.core.ctx.assistant
            assistant = self.window.core.assistants.get_by_id(id)
            if assistant is not None:
                # get ctx assistant
                label += ' (' + assistant.name + ')'
            else:
                # get current assistant
                id = self.window.core.config.get('assistant')
                assistant = self.window.core.assistants.get_by_id(id)
                if assistant is not None:
                    label += ' (' + assistant.name + ')'

        # update ctx label
        self.window.controller.ui.update_ctx_label(label)

    def update_label(self, mode, assistant_id=None):
        """
        Update ctx label

        :param mode: Mode
        :param assistant_id: Assistant id
        """
        if mode is None:
            return
        label = trans('mode.' + mode)
        if mode == 'assistant' and assistant_id is not None:
            assistant = self.window.core.assistants.get_by_id(assistant_id)
            if assistant is not None:
                label += ' (' + assistant.name + ')'

        # update ctx label
        self.window.controller.ui.update_ctx_label(label)

    def dismiss_rename(self):
        """Dismiss rename dialog"""
        self.window.ui.dialog['rename'].close()

    def focus_chat(self):
        """Focus chat"""
        if self.window.controller.ui.current_tab != self.window.controller.ui.tab_idx['chat']:
            self.window.ui.tabs['output'].setCurrentIndex(self.window.controller.ui.tab_idx['chat'])
