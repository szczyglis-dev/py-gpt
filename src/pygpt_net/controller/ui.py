# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.12 06:00:00                  #
# ================================================== #

from pygpt_net.core.dispatcher import Event
from pygpt_net.utils import trans


class UI:
    def __init__(self, window=None):
        """
        UI update controller

        :param window: Window instance
        """
        self.window = window
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
        self.update_active()

        # update token counters
        self.update_tokens()

    def update_font_size(self):
        """Update font size"""
        self.window.controller.theme.apply_nodes(False)

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

        force_vision_allowed = self.window.controller.drawing.is_drawing()

        mode = self.window.core.config.data['mode']
        if mode == 'chat':
            # presets
            self.window.ui.nodes['presets.widget'].setVisible(True)
            self.window.ui.nodes['preset.clear'].setVisible(True)
            self.window.ui.nodes['preset.use'].setVisible(False)

            self.window.ui.nodes['indexes.widget'].setVisible(False)
            self.window.ui.nodes['assistants.widget'].setVisible(False)
            self.window.ui.nodes['dalle.options'].setVisible(False)

            # event: ui.vision
            value = False
            event = Event('ui.vision', {
                'mode': mode,
                'value': value,
            })
            self.window.core.dispatcher.dispatch(event)
            value = event.data['value']
            if force_vision_allowed:
                value = True

            # vision capture
            self.window.ui.nodes['vision.capture.options'].setVisible(value)
            self.window.ui.nodes['attachments.capture_clear'].setVisible(value)

            # event: ui.attachments
            value = False
            event = Event('ui.attachments', {
                'mode': mode,
                'value': value,
            })
            self.window.core.dispatcher.dispatch(event)
            value = event.data['value']

            # files tabs
            self.window.ui.tabs['input'].setTabVisible(1, value)  # files

            # uploaded files
            self.window.ui.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.ui.nodes['input.stream'].setVisible(True)

        elif mode == 'img':
            # presets
            self.window.ui.nodes['presets.widget'].setVisible(True)
            self.window.ui.nodes['preset.prompt'].setDisabled(False)
            self.window.ui.nodes['preset.clear'].setVisible(False)
            self.window.ui.nodes['preset.use'].setVisible(True)

            self.window.ui.nodes['indexes.widget'].setVisible(False)
            self.window.ui.nodes['assistants.widget'].setVisible(False)
            self.window.ui.nodes['dalle.options'].setVisible(True)

            value = False
            if force_vision_allowed:
                value = True

            # vision capture
            self.window.ui.nodes['vision.capture.options'].setVisible(value)
            self.window.ui.nodes['attachments.capture_clear'].setVisible(value)

            # files tabs
            self.window.ui.tabs['input'].setTabVisible(1, False)  # files
            self.window.ui.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.ui.nodes['input.stream'].setVisible(False)

        elif mode == 'completion':
            # presets
            self.window.ui.nodes['presets.widget'].setVisible(True)
            self.window.ui.nodes['preset.prompt'].setDisabled(False)
            self.window.ui.nodes['preset.clear'].setVisible(True)
            self.window.ui.nodes['preset.use'].setVisible(False)

            self.window.ui.nodes['indexes.widget'].setVisible(False)
            self.window.ui.nodes['assistants.widget'].setVisible(False)
            self.window.ui.nodes['dalle.options'].setVisible(False)

            # event: ui.vision
            value = False
            event = Event('ui.vision', {
                'mode': mode,
                'value': value,
            })
            self.window.core.dispatcher.dispatch(event)
            value = event.data['value']
            if force_vision_allowed:
                value = True

            # vision capture
            self.window.ui.nodes['vision.capture.options'].setVisible(value)
            self.window.ui.nodes['attachments.capture_clear'].setVisible(value)

            # event: ui.attachments
            value = False
            event = Event('ui.attachments', {
                'mode': mode,
                'value': value,
            })
            self.window.core.dispatcher.dispatch(event)
            value = event.data['value']

            # files tabs
            self.window.ui.tabs['input'].setTabVisible(1, value)  # files
            self.window.ui.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.ui.nodes['input.stream'].setVisible(True)

        elif mode == 'vision':
            # presets
            self.window.ui.nodes['presets.widget'].setVisible(True)
            self.window.ui.nodes['preset.clear'].setVisible(True)
            self.window.ui.nodes['preset.use'].setVisible(False)

            self.window.ui.nodes['indexes.widget'].setVisible(False)
            self.window.ui.nodes['assistants.widget'].setVisible(False)
            self.window.ui.nodes['dalle.options'].setVisible(False)

            value = False
            if force_vision_allowed:
                value = True

            # vision capture
            self.window.ui.nodes['vision.capture.options'].setVisible(value)
            self.window.ui.nodes['attachments.capture_clear'].setVisible(value)

            # files tabs
            self.window.ui.tabs['input'].setTabVisible(1, True)  # files
            self.window.ui.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.ui.nodes['input.stream'].setVisible(True)

        elif mode == 'langchain':
            # presets
            self.window.ui.nodes['presets.widget'].setVisible(True)
            self.window.ui.nodes['preset.clear'].setVisible(True)
            self.window.ui.nodes['preset.use'].setVisible(False)

            self.window.ui.nodes['indexes.widget'].setVisible(False)
            self.window.ui.nodes['assistants.widget'].setVisible(False)
            self.window.ui.nodes['dalle.options'].setVisible(False)

            # event: ui.vision
            value = False
            event = Event('ui.vision', {
                'mode': mode,
                'value': value,
            })
            self.window.core.dispatcher.dispatch(event)
            value = event.data['value']
            if force_vision_allowed:
                value = True

            # vision capture
            self.window.ui.nodes['vision.capture.options'].setVisible(value)
            self.window.ui.nodes['attachments.capture_clear'].setVisible(value)

            # event: ui.attachments
            value = False
            event = Event('ui.attachments', {
                'mode': mode,
                'value': value,
            })
            self.window.core.dispatcher.dispatch(event)
            value = event.data['value']

            # files tabs
            self.window.ui.tabs['input'].setTabVisible(1, value)  # files
            self.window.ui.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.ui.nodes['input.stream'].setVisible(True)

        elif mode == 'assistant':
            # presets
            self.window.ui.nodes['presets.widget'].setVisible(False)
            self.window.ui.nodes['preset.clear'].setVisible(True)
            self.window.ui.nodes['preset.use'].setVisible(False)

            self.window.ui.nodes['indexes.widget'].setVisible(False)
            self.window.ui.nodes['assistants.widget'].setVisible(True)
            self.window.ui.nodes['dalle.options'].setVisible(False)

            value = False
            if force_vision_allowed:
                value = True

            # vision capture
            self.window.ui.nodes['vision.capture.options'].setVisible(value)
            self.window.ui.nodes['attachments.capture_clear'].setVisible(value)

            # files tabs
            self.window.ui.tabs['input'].setTabVisible(1, True)  # files
            self.window.ui.tabs['input'].setTabVisible(2, True)  # uploaded files

            # stream checkbox
            self.window.ui.nodes['input.stream'].setVisible(False)

        elif mode == 'llama_index':
            # presets
            self.window.ui.nodes['presets.widget'].setVisible(True)
            self.window.ui.nodes['preset.prompt'].setDisabled(False)
            self.window.ui.nodes['preset.clear'].setVisible(False)
            self.window.ui.nodes['preset.use'].setVisible(False)

            self.window.ui.nodes['indexes.widget'].setVisible(True)
            self.window.ui.nodes['assistants.widget'].setVisible(False)
            self.window.ui.nodes['dalle.options'].setVisible(False)

            value = False
            if force_vision_allowed:
                value = True

            # vision capture
            self.window.ui.nodes['vision.capture.options'].setVisible(value)
            self.window.ui.nodes['attachments.capture_clear'].setVisible(value)

            # files tabs
            self.window.ui.tabs['input'].setTabVisible(1, False)  # files
            self.window.ui.tabs['input'].setTabVisible(2, False)  # uploaded files

            # stream checkbox
            self.window.ui.nodes['input.stream'].setVisible(False)

    def update_vision(self):
        # vision camera
        mode = self.window.core.config.data['mode']
        if self.window.controller.drawing.is_drawing():
            self.window.controller.camera.setup()
            self.window.controller.camera.show_camera()
        else:
            if self.window.controller.plugins.is_type_enabled('vision'):
                self.window.controller.camera.setup()
                self.window.controller.camera.show_camera()

                # if attachments then show enabled checkbox
                if mode != 'vision' and mode in self.window.controller.chat.vision.allowed_modes:
                    self.window.controller.chat.vision.show_inline()  # show enabled checkbox
            else:
                self.window.controller.camera.hide_camera()
                if mode != 'vision' or mode not in self.window.controller.chat.vision.allowed_modes:
                    self.window.controller.chat.vision.hide_inline()  # hide enabled checkbox

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
        :type idx: int
        """
        self.current_tab = idx
        self.window.controller.ui.update_active()

        if idx == self.tab_idx['calendar']:
            self.window.controller.notepad.opened_once = True
        elif idx == self.tab_idx['draw']:
            if self.window.core.config.get('vision.capture.enabled'):
                self.window.controller.camera.enable_capture()
