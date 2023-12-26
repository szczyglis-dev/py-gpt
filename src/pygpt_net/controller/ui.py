# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #

from pygpt_net.core.dispatcher import Event
from pygpt_net.core.tokens import num_tokens_prompt, num_tokens_only, num_tokens_extra
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
        # update mode, models and presets lists
        self.update_toolbox()

        # update chat label
        self.update_chat_label()

        # show / hide widgets
        self.update_active()

        # update token counters
        self.update_tokens()

    def update_toolbox(self):
        """Update toolbox"""
        self.window.controller.model.update_mode()
        self.window.controller.model.update_models()
        self.window.controller.model.update_presets()
        self.window.controller.assistant.update_assistants()

    def build_final_system_prompt(self, prompt):
        # tmp dispatch event: system.prompt
        event = Event('system.prompt', {
            'value': prompt,
            'silent': True,
        })
        self.window.app.dispatcher.dispatch(event)
        prompt = event.data['value']

        if self.window.app.config.get('cmd'):
            # cmd prompt
            prompt += self.window.app.command.get_prompt()

            # cmd syntax tokens
            data = {
                'prompt': prompt,
                'syntax': [],
            }
            # tmp dispatch event: cmd.syntax
            event = Event('cmd.syntax', data)
            self.window.app.dispatcher.dispatch(event)
            prompt = self.window.app.command.append_syntax(event.data)

        return prompt

    def update_tokens(self):
        """Update tokens counters"""
        model = self.window.app.config.get('model')
        mode = self.window.app.config.get('mode')
        user_name = self.window.app.config.get('user_name')
        ai_name = self.window.app.config.get('ai_name')
        max_total_tokens = self.window.app.config.get('max_total_tokens')
        extra_tokens = num_tokens_extra(model)

        prompt_tokens = 0
        input_tokens = 0

        if mode == "chat" or mode == "vision" or mode == "langchain" or mode == "assistant":
            # prompt tokens (without extra tokens)
            system_prompt = str(self.window.app.config.get('prompt')).strip()
            system_prompt = self.build_final_system_prompt(system_prompt)  # add addons
            prompt_tokens = num_tokens_prompt(system_prompt, "", model)
            prompt_tokens += num_tokens_only("system", model)

            # input tokens
            input_text = str(self.window.ui.nodes['input'].toPlainText().strip())
            input_tokens = num_tokens_prompt(input_text, "", model)
            input_tokens += num_tokens_only("user", model)
        elif mode == "completion":
            # prompt tokens (without extra tokens)
            system_prompt = str(self.window.app.config.get('prompt')).strip()
            system_prompt = self.build_final_system_prompt(system_prompt)  # add addons
            prompt_tokens = num_tokens_only(system_prompt, model)

            # input tokens
            input_text = str(self.window.ui.nodes['input'].toPlainText().strip())
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

        # check real model max
        max_to_calc = max_total_tokens
        model_ctx = self.window.app.models.get_num_ctx(model)
        if max_to_calc > model_ctx:
            max_to_calc = model_ctx

        to_check = max_to_calc - self.window.app.config.get('context_threshold')

        # context tokens
        ctx_len_all = len(self.window.app.ctx.items)
        ctx_len, ctx_tokens = self.window.app.ctx.count_prompt_items(model, mode, used_tokens, to_check)

        # zero if context not used
        if not self.window.app.config.get('use_context'):
            ctx_tokens = 0
            ctx_len = 0

        # total tokens
        total_tokens = prompt_tokens + input_tokens + ctx_tokens + extra_tokens

        # update counters
        string = "{} / {} - {} {}".format(ctx_len, ctx_len_all, ctx_tokens, trans('ctx.tokens'))
        self.window.ui.nodes['prompt.context'].setText(string)

        # threshold = str(int(self.window.app.config.get('context_threshold')))

        parsed_total = str(int(total_tokens))
        parsed_total = parsed_total.replace("000000", "M").replace("000", "k")

        parsed_max_total = str(int(max_to_calc))
        parsed_max_total = parsed_max_total.replace("000000", "M").replace("000", "k")

        string = "{} + {} + {} + {} = {} / {}".format(input_tokens, prompt_tokens, ctx_tokens, extra_tokens,
                                                      parsed_total, parsed_max_total)
        self.window.ui.nodes['input.counter'].setText(string)

    def update_active(self):
        """Update mode, model, preset and rest of the toolbox"""
        mode = self.window.app.config.data['mode']
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
        mode = self.window.app.config.get('mode')
        model = self.window.app.config.get('model')
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
        mode = self.window.app.config.get('mode')
        allowed = self.window.controller.ctx.is_allowed_for_mode(mode)
        if label is None:
            label = ''

        # add (+) if allowed to append data to this context
        if allowed:
            label += ' (+)'
        self.window.ui.nodes['chat.label'].setText(str(label))
