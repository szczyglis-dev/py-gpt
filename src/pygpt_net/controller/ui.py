# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.26 20:00:00                  #
# ================================================== #

from pygpt_net.utils import trans


class UI:
    def __init__(self, window=None):
        """
        UI update controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup UI"""
        self.update()

    def update(self):
        """Update all elements"""
        self.window.controller.layout.scroll_save()

        # update mode, models and presets lists
        self.update_toolbox()

        # update chat label
        self.update_chat_label()

        # show / hide widgets
        self.update_active()

        # update token counters
        self.update_tokens()

        self.window.controller.layout.scroll_restore()

    def update_toolbox(self):
        """Update toolbox"""
        self.window.controller.mode.update_mode()
        self.window.controller.model.update()
        self.window.controller.presets.refresh()
        self.window.controller.assistant.refresh()

    def update_tokens(self):
        """Update tokens counter in real-time"""
        prompt = str(self.window.ui.nodes['input'].toPlainText().strip())
        input_tokens, system_tokens, extra_tokens, ctx_tokens, ctx_len, ctx_len_all, \
        sum_tokens, max_current, threshold = self.window.core.tokens.get_current(prompt)

        # ctx tokens
        ctx_string = "{} / {} - {} {}".format(ctx_len, ctx_len_all, ctx_tokens, trans('ctx.tokens'))
        self.window.ui.nodes['prompt.context'].setText(ctx_string)

        # input tokens
        parsed_sum = str(int(sum_tokens))
        parsed_sum = parsed_sum.replace("000000", "M").replace("000", "k")

        parsed_max_current = str(int(max_current))
        parsed_max_current = parsed_max_current.replace("000000", "M").replace("000", "k")

        input_string = "{} + {} + {} + {} = {} / {}".format(input_tokens, system_tokens, ctx_tokens, extra_tokens,
                                                      parsed_sum, parsed_max_current)
        self.window.ui.nodes['input.counter'].setText(input_string)

    def update_active(self):
        """Update mode, model, preset and rest of the toolbox"""
        mode = self.window.core.config.data['mode']
        if mode == 'chat':
            # temperature
            self.window.ui.config_option['current_temperature'].slider.setDisabled(False)
            self.window.ui.config_option['current_temperature'].input.setDisabled(False)
            self.window.ui.config_option['current_temperature'].setVisible(True)
            self.window.ui.nodes['temperature.label'].setVisible(True)

            # presets
            self.window.ui.nodes['presets.widget'].setVisible(True)
            self.window.ui.nodes['preset.ai_name'].setDisabled(False)
            self.window.ui.nodes['preset.user_name'].setDisabled(False)
            self.window.ui.nodes['preset.clear'].setVisible(True)
            self.window.ui.nodes['preset.use'].setVisible(False)

            self.window.ui.nodes['assistants.widget'].setVisible(False)
            self.window.ui.nodes['dalle.options'].setVisible(False)

            # vision capture
            self.window.ui.nodes['vision.capture.options'].setVisible(False)
            self.window.ui.nodes['attachments.capture_clear'].setVisible(False)

            # files tabs
            self.window.ui.tabs['input'].setTabVisible(1, False)  # files
            self.window.ui.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.ui.nodes['input.stream'].setVisible(True)

        elif mode == 'img':
            # temperature
            self.window.ui.config_option['current_temperature'].slider.setDisabled(True)
            self.window.ui.config_option['current_temperature'].input.setDisabled(True)
            self.window.ui.config_option['current_temperature'].setVisible(False)
            self.window.ui.nodes['temperature.label'].setVisible(False)

            # presets
            self.window.ui.nodes['presets.widget'].setVisible(True)
            self.window.ui.nodes['preset.prompt'].setDisabled(False)
            self.window.ui.nodes['preset.ai_name'].setDisabled(True)
            self.window.ui.nodes['preset.user_name'].setDisabled(True)
            self.window.ui.nodes['preset.clear'].setVisible(False)
            self.window.ui.nodes['preset.use'].setVisible(True)

            self.window.ui.nodes['assistants.widget'].setVisible(False)
            self.window.ui.nodes['dalle.options'].setVisible(True)

            # vision capture
            self.window.ui.nodes['vision.capture.options'].setVisible(False)
            self.window.ui.nodes['attachments.capture_clear'].setVisible(False)

            # files tabs
            self.window.ui.tabs['input'].setTabVisible(1, False)  # files
            self.window.ui.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.ui.nodes['input.stream'].setVisible(False)

        elif mode == 'completion':
            # temperature
            self.window.ui.config_option['current_temperature'].slider.setDisabled(False)
            self.window.ui.config_option['current_temperature'].input.setDisabled(False)
            self.window.ui.config_option['current_temperature'].setVisible(True)
            self.window.ui.nodes['temperature.label'].setVisible(True)

            # presets
            self.window.ui.nodes['presets.widget'].setVisible(True)
            self.window.ui.nodes['preset.prompt'].setDisabled(False)
            self.window.ui.nodes['preset.ai_name'].setDisabled(False)
            self.window.ui.nodes['preset.user_name'].setDisabled(False)
            self.window.ui.nodes['preset.clear'].setVisible(True)
            self.window.ui.nodes['preset.use'].setVisible(False)

            self.window.ui.nodes['assistants.widget'].setVisible(False)
            self.window.ui.nodes['dalle.options'].setVisible(False)

            # vision capture
            self.window.ui.nodes['vision.capture.options'].setVisible(False)
            self.window.ui.nodes['attachments.capture_clear'].setVisible(False)

            # files tabs
            self.window.ui.tabs['input'].setTabVisible(1, False)  # files
            self.window.ui.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.ui.nodes['input.stream'].setVisible(True)

        elif mode == 'vision':
            # temperature
            self.window.ui.config_option['current_temperature'].slider.setDisabled(False)
            self.window.ui.config_option['current_temperature'].input.setDisabled(False)
            self.window.ui.config_option['current_temperature'].setVisible(False)
            self.window.ui.nodes['temperature.label'].setVisible(False)

            # presets
            self.window.ui.nodes['presets.widget'].setVisible(True)
            self.window.ui.nodes['preset.ai_name'].setDisabled(True)
            self.window.ui.nodes['preset.user_name'].setDisabled(True)
            self.window.ui.nodes['preset.clear'].setVisible(True)
            self.window.ui.nodes['preset.use'].setVisible(False)

            self.window.ui.nodes['assistants.widget'].setVisible(False)
            self.window.ui.nodes['dalle.options'].setVisible(False)

            # vision capture
            self.window.ui.nodes['vision.capture.options'].setVisible(True)
            self.window.ui.nodes['attachments.capture_clear'].setVisible(True)

            # files tabs
            self.window.ui.tabs['input'].setTabVisible(1, True)  # files
            self.window.ui.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.ui.nodes['input.stream'].setVisible(True)

        elif mode == 'langchain':
            # temperature
            self.window.ui.config_option['current_temperature'].slider.setDisabled(False)
            self.window.ui.config_option['current_temperature'].input.setDisabled(False)
            self.window.ui.config_option['current_temperature'].setVisible(True)
            self.window.ui.nodes['temperature.label'].setVisible(True)

            # presets
            self.window.ui.nodes['presets.widget'].setVisible(True)
            self.window.ui.nodes['preset.ai_name'].setDisabled(False)
            self.window.ui.nodes['preset.user_name'].setDisabled(False)
            self.window.ui.nodes['preset.clear'].setVisible(True)
            self.window.ui.nodes['preset.use'].setVisible(False)

            self.window.ui.nodes['assistants.widget'].setVisible(False)
            self.window.ui.nodes['dalle.options'].setVisible(False)

            # vision capture
            self.window.ui.nodes['vision.capture.options'].setVisible(False)
            self.window.ui.nodes['attachments.capture_clear'].setVisible(False)

            # files tabs
            self.window.ui.tabs['input'].setTabVisible(1, False)  # files
            self.window.ui.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.ui.nodes['input.stream'].setVisible(True)

        elif mode == 'assistant':
            # temperature
            self.window.ui.config_option['current_temperature'].slider.setDisabled(False)
            self.window.ui.config_option['current_temperature'].input.setDisabled(False)
            self.window.ui.config_option['current_temperature'].setVisible(True)
            self.window.ui.nodes['temperature.label'].setVisible(True)

            # presets
            self.window.ui.nodes['presets.widget'].setVisible(True)
            self.window.ui.nodes['preset.ai_name'].setDisabled(True)
            self.window.ui.nodes['preset.user_name'].setDisabled(True)
            self.window.ui.nodes['preset.clear'].setVisible(True)
            self.window.ui.nodes['preset.use'].setVisible(False)

            self.window.ui.nodes['assistants.widget'].setVisible(True)
            self.window.ui.nodes['dalle.options'].setVisible(False)

            # vision capture
            self.window.ui.nodes['vision.capture.options'].setVisible(False)
            self.window.ui.nodes['attachments.capture_clear'].setVisible(False)

            # files tabs
            self.window.ui.tabs['input'].setTabVisible(1, True)  # files
            self.window.ui.tabs['input'].setTabVisible(2, True)  # uploaded files

            # stream checkbox
            self.window.ui.nodes['input.stream'].setVisible(False)

    def update_chat_label(self):
        """Update chat label"""
        mode = self.window.core.config.get('mode')
        model = self.window.core.config.get('model')
        if model is None or model == "":
            model_str = "{}".format(trans("mode." + mode))
        else:
            model_str = "{} ({})".format(trans("mode." + mode), model)
        self.window.ui.nodes['chat.model'].setText(model_str)

    def update_ctx_label(self, label):
        """
        Update ctx label

        :param label: label
        """
        mode = self.window.core.config.get('mode')
        allowed = self.window.controller.ctx.is_allowed_for_mode(mode)
        if label is None:
            label = ''

        # add (+) if allowed to append data to this context
        if allowed:
            label += ' (+)'
        self.window.ui.nodes['chat.label'].setText(str(label))
