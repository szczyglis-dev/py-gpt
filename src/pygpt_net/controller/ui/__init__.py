# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 03:00:00                  #
# ================================================== #

from PySide6.QtGui import QColor

from pygpt_net.utils import trans

from .mode import Mode
from .tabs import Tabs
from .vision import Vision


class UI:
    def __init__(self, window=None):
        """
        UI update controller

        :param window: Window instance
        """
        self.window = window
        self.mode = Mode(window)
        self.tabs = Tabs(window)
        self.vision = Vision(window)
        self.colors = {
            0: {'label': 'label.color.default', 'color': QColor(100, 100, 100), 'font': QColor(255, 255, 255)},
            1: {'label': 'label.color.red', 'color': QColor(255, 0, 0), 'font': QColor(255, 255, 255)},
            2: {'label': 'label.color.orange', 'color': QColor(255, 165, 0), 'font': QColor(255, 255, 255)},
            3: {'label': 'label.color.yellow', 'color': QColor(255, 255, 0), 'font': QColor(0, 0, 0)},
            4: {'label': 'label.color.green', 'color': QColor(0, 255, 0), 'font': QColor(0, 0, 0)},
            5: {'label': 'label.color.blue', 'color': QColor(0, 0, 255), 'font': QColor(255, 255, 255)},
            6: {'label': 'label.color.indigo', 'color': QColor(75, 0, 130), 'font': QColor(255, 255, 255)},
            7: {'label': 'label.color.violet', 'color': QColor(238, 130, 238), 'font': QColor(255, 255, 255)},
        }
        self.stop_action = None

    def setup(self):
        """Setup UI"""
        self.update_font_size()
        self.update()
        self.init_toolbox()

    def pre_setup(self):
        """Post setup UI"""
        self.tabs.setup()

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

        # update vision
        self.vision.update()

        # agent status
        self.window.controller.agent.update()

    def get_colors(self) -> dict:
        """
        Get color labels

        :return: color labels dict
        """
        return self.colors

    def update_font_size(self):
        """Update font size"""
        self.window.controller.theme.nodes.apply_all()

    def init_toolbox(self):
        """Init toolbox"""
        self.window.controller.mode.init_list()
        self.window.controller.model.init_list()

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

    def show_global_stop(self):
        """Show global stop button"""
        self.window.ui.nodes['global.stop'].setVisible(True)

    def hide_global_stop(self):
        """Hide global stop button"""
        self.window.ui.nodes['global.stop'].setVisible(False)

    def on_global_stop(self):
        """Global stop button action"""
        if self.stop_action == "idx":
            self.window.controller.idx.force_stop()