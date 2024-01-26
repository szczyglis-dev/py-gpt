# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.26 10:00:00                  #
# ================================================== #

from pygpt_net.utils import trans
from .mode import Mode
from .vision import Vision


class UI:
    def __init__(self, window=None):
        """
        UI update controller

        :param window: Window instance
        """
        self.window = window
        self.mode = Mode(window)
        self.vision = Vision(window)
        self.current_tab = 0
        self.tab_idx = {
            'chat': 0,
            'files': 1,
            'calendar': 2,
            'draw': 3,
        }

    def setup(self):
        """Setup UI"""
        self.update_font_size()
        self.update()

    def update(self):
        """Update all elements"""

        # update mode, models and presets list
        self.update_toolbox()

        # update chat label
        self.update_chat_label()

        # show / hide widgets
        self.mode.update()

        # update token counters
        self.update_tokens()

    def update_font_size(self):
        """Update font size"""
        self.window.controller.theme.nodes.apply_all()

    def update_toolbox(self):
        """Update toolbox"""
        self.window.controller.mode.update_mode()
        self.window.controller.model.update()
        self.window.controller.presets.refresh()
        self.window.controller.assistant.refresh()
        self.window.controller.idx.refresh()

    def update_tokens(self):
        """Update tokens counter in real-time"""
        prompt = str(self.window.ui.nodes['input'].toPlainText().strip())
        input_tokens, system_tokens, extra_tokens, ctx_tokens, ctx_len, ctx_len_all, \
            sum_tokens, max_current, threshold = self.window.core.tokens.get_current(prompt)

        # ctx tokens
        ctx_string = "{} / {} - {} {}".format(
            ctx_len,
            ctx_len_all,
            ctx_tokens,
            trans('ctx.tokens')
        )
        self.window.ui.nodes['prompt.context'].setText(ctx_string)

        # input tokens
        parsed_sum = str(int(sum_tokens))
        parsed_sum = parsed_sum.replace("000000", "M").replace("000", "k")

        parsed_max_current = str(int(max_current))
        parsed_max_current = parsed_max_current.replace("000000", "M").replace("000", "k")

        input_string = "{} + {} + {} + {} = {} / {}".format(
            input_tokens,
            system_tokens,
            ctx_tokens,
            extra_tokens,
            parsed_sum,
            parsed_max_current
        )
        self.window.ui.nodes['input.counter'].setText(input_string)

    def store_state(self):
        """Store UI state"""
        self.window.controller.layout.scroll_save()

    def restore_state(self):
        """Restore UI state"""
        self.window.controller.layout.scroll_restore()

    def update_chat_label(self):
        """Update chat label"""
        model = self.window.core.config.get('model')
        if model is None or model == "":
            model_str = ""
        else:
            model_str = str(model)
        self.window.ui.nodes['chat.model'].setText(model_str)

    def update_ctx_label(self, label: str = None):
        """
        Update ctx label

        :param label: label
        """
        mode = self.window.core.config.get('mode')
        allowed = self.window.core.ctx.is_allowed_for_mode(mode)
        if label is None:
            label = ''

        # add (+) if allowed appending data to this context
        if allowed:
            label += ' (+)'
        self.window.ui.nodes['chat.label'].setText(str(label))

    def output_tab_changed(self, idx: int):
        """
        Output tab changed

        :param idx: tab index
        """
        self.current_tab = idx
        self.mode.update()
        self.vision.update()

        if idx == self.tab_idx['calendar']:
            self.window.controller.notepad.opened_once = True
        elif idx == self.tab_idx['draw']:
            if self.window.core.config.get('vision.capture.enabled'):
                self.window.controller.camera.enable_capture()
