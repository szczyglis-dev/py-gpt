# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 19:00:00                  #
# ================================================== #

from ..tokens import num_tokens_prompt, num_tokens_only, num_tokens_extra
from ..utils import trans


class UI:
    def __init__(self, window=None):
        """
        UI update controller

        :param window: main UI window object
        """
        self.window = window

    def setup(self):
        """Setups UI"""
        self.update()

    def update(self):
        """Updates all elements"""
        # update mode, models and presets lists
        self.update_toolbox()

        # update chat label
        self.update_chat_label()

        # show / hide widgets
        self.update_active()

        # update token counters
        self.update_tokens()

    def update_toolbox(self):
        """Updates toolbox"""
        self.window.controller.model.update_mode()
        self.window.controller.model.update_models()
        self.window.controller.model.update_presets()
        self.window.controller.assistant.update_assistants()

    def update_tokens(self):
        """Updates tokens counters"""
        model = self.window.config.get('model')
        mode = self.window.config.get('mode')
        user_name = self.window.config.get('user_name')
        ai_name = self.window.config.get('ai_name')
        max_total_tokens = self.window.config.get('max_total_tokens')
        extra_tokens = num_tokens_extra(model)

        prompt_tokens = 0
        input_tokens = 0

        if mode == "chat" or mode == "vision" or mode == "langchain" or mode == "assistant":
            # prompt tokens (without extra tokens)
            system_prompt = str(self.window.config.get('prompt')).strip()
            prompt_tokens = num_tokens_prompt(system_prompt, "", model)
            prompt_tokens += num_tokens_only("system", model)

            # input tokens
            input_text = str(self.window.data['input'].toPlainText().strip())
            input_tokens = num_tokens_prompt(input_text, "", model)
            input_tokens += num_tokens_only("user", model)
        elif mode == "completion":
            # prompt tokens (without extra tokens)
            system_prompt = str(self.window.config.get('prompt')).strip()
            prompt_tokens = num_tokens_only(system_prompt, model)

            # input tokens
            input_text = str(self.window.data['input'].toPlainText().strip())
            message = ""
            if user_name is not None \
                    and ai_name is not None \
                    and user_name != "" \
                    and ai_name != "":
                message += "\n" + user_name + ": " + str(input_text)
                message += "\n" + ai_name + ":"
            else:
                message += "\n" + str(input_text)
            input_tokens = num_tokens_only(message, model)
            extra_tokens = 0  # no extra tokens in completion mode

        # used tokens
        used_tokens = prompt_tokens + input_tokens

        # context tokens
        ctx_len_all = len(self.window.gpt.context.items)
        ctx_len, ctx_tokens = self.window.gpt.context.count_prompt_items(model, mode, used_tokens, max_total_tokens)

        # zero if context not used
        if not self.window.config.get('use_context'):
            ctx_tokens = 0
            ctx_len = 0

        # total tokens
        total_tokens = prompt_tokens + input_tokens + ctx_tokens + extra_tokens

        # update counters
        string = "{} / {} - {} {}".format(ctx_len, ctx_len_all, ctx_tokens, trans('ctx.tokens'))
        self.window.data['prompt.context'].setText(string)

        # threshold = str(int(self.window.config.get('context_threshold')))

        parsed_total = str(int(total_tokens))
        parsed_total = parsed_total.replace("000000", "M").replace("000", "k")

        parsed_max_total = str(int(max_total_tokens))
        parsed_max_total = parsed_max_total.replace("000000", "M").replace("000", "k")

        string = "{} + {} + {} + {} = {} / {}".format(input_tokens, prompt_tokens, ctx_tokens, extra_tokens,
                                                      parsed_total, parsed_max_total)
        self.window.data['input.counter'].setText(string)

    def update_active(self):
        """Updates mode, model, preset and rest of the toolbox"""
        mode = self.window.config.data['mode']
        if mode == 'chat':
            # temperature
            self.window.config_option['current_temperature'].slider.setDisabled(False)
            self.window.config_option['current_temperature'].input.setDisabled(False)
            self.window.config_option['current_temperature'].setVisible(True)
            self.window.data['temperature.label'].setVisible(True)

            # presets
            self.window.data['presets.widget'].setVisible(True)
            self.window.data['preset.ai_name'].setDisabled(False)
            self.window.data['preset.user_name'].setDisabled(False)
            self.window.data['preset.clear'].setVisible(True)
            self.window.data['preset.use'].setVisible(False)

            self.window.data['assistants.widget'].setVisible(False)
            self.window.data['dalle.options'].setVisible(False)

            # vision capture
            self.window.data['vision.capture.options'].setVisible(False)
            self.window.data['attachments.capture_clear'].setVisible(False)

            # files tabs
            self.window.tabs['input'].setTabVisible(1, False)  # files
            self.window.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.data['input.stream'].setVisible(True)

        elif mode == 'img':
            # temperature
            self.window.config_option['current_temperature'].slider.setDisabled(True)
            self.window.config_option['current_temperature'].input.setDisabled(True)
            self.window.config_option['current_temperature'].setVisible(False)
            self.window.data['temperature.label'].setVisible(False)

            # presets
            self.window.data['presets.widget'].setVisible(True)
            self.window.data['preset.prompt'].setDisabled(False)
            self.window.data['preset.ai_name'].setDisabled(True)
            self.window.data['preset.user_name'].setDisabled(True)
            self.window.data['preset.clear'].setVisible(False)
            self.window.data['preset.use'].setVisible(True)

            self.window.data['assistants.widget'].setVisible(False)
            self.window.data['dalle.options'].setVisible(True)

            # vision capture
            self.window.data['vision.capture.options'].setVisible(False)
            self.window.data['attachments.capture_clear'].setVisible(False)

            # files tabs
            self.window.tabs['input'].setTabVisible(1, False)  # files
            self.window.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.data['input.stream'].setVisible(False)

        elif mode == 'completion':
            # temperature
            self.window.config_option['current_temperature'].slider.setDisabled(False)
            self.window.config_option['current_temperature'].input.setDisabled(False)
            self.window.config_option['current_temperature'].setVisible(True)
            self.window.data['temperature.label'].setVisible(True)

            # presets
            self.window.data['presets.widget'].setVisible(True)
            self.window.data['preset.prompt'].setDisabled(False)
            self.window.data['preset.ai_name'].setDisabled(False)
            self.window.data['preset.user_name'].setDisabled(False)
            self.window.data['preset.clear'].setVisible(True)
            self.window.data['preset.use'].setVisible(False)

            self.window.data['assistants.widget'].setVisible(False)
            self.window.data['dalle.options'].setVisible(False)

            # vision capture
            self.window.data['vision.capture.options'].setVisible(False)
            self.window.data['attachments.capture_clear'].setVisible(False)

            # files tabs
            self.window.tabs['input'].setTabVisible(1, False)  # files
            self.window.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.data['input.stream'].setVisible(True)

        elif mode == 'vision':
            # temperature
            self.window.config_option['current_temperature'].slider.setDisabled(False)
            self.window.config_option['current_temperature'].input.setDisabled(False)
            self.window.config_option['current_temperature'].setVisible(False)
            self.window.data['temperature.label'].setVisible(False)

            # presets
            self.window.data['presets.widget'].setVisible(True)
            self.window.data['preset.ai_name'].setDisabled(True)
            self.window.data['preset.user_name'].setDisabled(True)
            self.window.data['preset.clear'].setVisible(True)
            self.window.data['preset.use'].setVisible(False)

            self.window.data['assistants.widget'].setVisible(False)
            self.window.data['dalle.options'].setVisible(False)

            # vision capture
            self.window.data['vision.capture.options'].setVisible(True)
            self.window.data['attachments.capture_clear'].setVisible(True)

            # files tabs
            self.window.tabs['input'].setTabVisible(1, True)  # files
            self.window.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.data['input.stream'].setVisible(True)

        elif mode == 'langchain':
            # temperature
            self.window.config_option['current_temperature'].slider.setDisabled(False)
            self.window.config_option['current_temperature'].input.setDisabled(False)
            self.window.config_option['current_temperature'].setVisible(True)
            self.window.data['temperature.label'].setVisible(True)

            # presets
            self.window.data['presets.widget'].setVisible(True)
            self.window.data['preset.ai_name'].setDisabled(False)
            self.window.data['preset.user_name'].setDisabled(False)
            self.window.data['preset.clear'].setVisible(True)
            self.window.data['preset.use'].setVisible(False)

            self.window.data['assistants.widget'].setVisible(False)
            self.window.data['dalle.options'].setVisible(False)

            # vision capture
            self.window.data['vision.capture.options'].setVisible(False)
            self.window.data['attachments.capture_clear'].setVisible(False)

            # files tabs
            self.window.tabs['input'].setTabVisible(1, False)  # files
            self.window.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.data['input.stream'].setVisible(True)

        elif mode == 'assistant':
            # temperature
            self.window.config_option['current_temperature'].slider.setDisabled(False)
            self.window.config_option['current_temperature'].input.setDisabled(False)
            self.window.config_option['current_temperature'].setVisible(True)
            self.window.data['temperature.label'].setVisible(True)

            # presets
            self.window.data['presets.widget'].setVisible(True)
            self.window.data['preset.ai_name'].setDisabled(True)
            self.window.data['preset.user_name'].setDisabled(True)
            self.window.data['preset.clear'].setVisible(True)
            self.window.data['preset.use'].setVisible(False)

            self.window.data['assistants.widget'].setVisible(True)
            self.window.data['dalle.options'].setVisible(False)

            # vision capture
            self.window.data['vision.capture.options'].setVisible(False)
            self.window.data['attachments.capture_clear'].setVisible(False)

            # files tabs
            self.window.tabs['input'].setTabVisible(1, True)  # files
            self.window.tabs['input'].setTabVisible(2, True)  # uploaded files

            # stream checkbox
            self.window.data['input.stream'].setVisible(False)

    def update_chat_label(self):
        """Updates chat label"""
        mode = self.window.config.get('mode')
        model = self.window.config.get('model')
        if model is None or model == "":
            model_str = "{}".format(trans("mode." + mode))
        else:
            model_str = "{} ({})".format(trans("mode." + mode), model)
        self.window.data['chat.model'].setText(model_str)
