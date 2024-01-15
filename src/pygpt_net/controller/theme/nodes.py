#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.15 03:00:00                  #
# ================================================== #


class Nodes:
    def __init__(self, window=None):
        """
        Theme nodes controller

        :param window: Window instance
        """
        self.window = window

    def apply(self, key: str, type: str):
        """
        Apply stylesheet to node

        :param key: UI node key
        :param type: stylesheet type
        """
        if key not in self.window.ui.nodes:
            return

        if type == 'toolbox':
            self.window.ui.nodes[key].setStyleSheet(self.window.controller.theme.style('toolbox'))
        elif type == 'chat_output':
            self.window.ui.nodes[key].setStyleSheet(self.window.controller.theme.style('chat_output'))
        elif type == 'chat_input':
            self.window.ui.nodes[key].setStyleSheet(self.window.controller.theme.style('chat_input'))
        elif type == 'ctx.list':
            self.window.ui.nodes[key].setStyleSheet(self.window.controller.theme.style('ctx.list'))
        elif type == 'text_faded':
            self.window.ui.nodes[key].setStyleSheet(self.window.controller.theme.style('text_faded'))

    def apply_all(self, all: bool = True):
        """
        Apply stylesheets to nodes

        :param all: apply also to highlighter
        """
        nodes = {
            'chat_input': [
                'input',
            ],
            'chat_output': [
                'output',
            ],
            'ctx.list': [
                'ctx.list',
            ],
            'toolbox': [
                'assistants',
                'assistants.new',
                'assistants.import',
                'assistants.label',
                'cmd.enabled',
                'dalle.options',
                'img_variants.label',
                'preset.clear',
                'preset.presets',
                'preset.presets.label',
                'preset.presets.new',
                'preset.prompt',
                'preset.prompt.label',
                'preset.temperature.label',
                'preset.use',
                'prompt.label',
                'prompt.mode',
                'prompt.mode.label',
                'prompt.model',
                'prompt.model.label',
                'temperature.label',
                'toolbox.prompt.label',
                'toolbox.preset.ai_name.label',
                'toolbox.preset.user_name.label',
                'vision.capture.auto',
                'vision.capture.enable',
                'vision.capture.label',
                'vision.capture.options',
            ],
            'text_faded': [
                'input.label',
                'prompt.context',
                'chat.label',
                'chat.model',
                'tip.output.tab.files',
                'tip.output.tab.draw',
                'tip.output.tab.calendar',
                'tip.output.tab.notepad',
                'tip.input.attachments',
                'tip.input.attachments.uploaded',
                'tip.toolbox.presets',
                'tip.toolbox.prompt',
                'tip.toolbox.assistants',
                'tip.toolbox.indexes',
                'tip.toolbox.ctx',
                'tip.toolbox.mode',
            ],
        }

        # apply to nodes
        for type in nodes:
            for key in nodes[type]:
                self.apply(key, type)

        # apply to notepads
        num_notepads = self.window.controller.notepad.get_num_notepads()
        if num_notepads > 0:
            for id in range(1, num_notepads + 1):
                if id in self.window.ui.notepad:
                    self.window.ui.notepad[id].textarea.setStyleSheet(self.window.controller.theme.style('chat_output'))
