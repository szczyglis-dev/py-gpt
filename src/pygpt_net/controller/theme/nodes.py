#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.24 23:00:00                  #
# ================================================== #

from pygpt_net.core.events import RenderEvent


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
        nodes = self.window.ui.nodes
        theme = self.window.controller.theme

        if key not in nodes:
            return

        if type == 'font.toolbox':
            nodes[key].setStyleSheet(theme.style('font.toolbox'))
        elif type == 'font.chat.output':
            style_output = theme.style('font.chat.output')
            for pid in nodes[key]:
                try:
                    nodes[key][pid].setStyleSheet(style_output)
                except Exception as e:
                    pass
        elif type == 'font.chat.input':
            nodes[key].setStyleSheet(theme.style('font.chat.input'))
        elif type == 'font.ctx.list':
            nodes[key].setStyleSheet(theme.style('font.ctx.list'))

    def apply_all(self):
        """Apply stylesheets to nodes"""
        w = self.window
        ui = w.ui
        ctrl = w.controller
        engine = ctrl.chat.render.get_engine()

        nodes = {
            'font.chat.input': [
                'input',
            ],
            'font.chat.output': [
                'output',
                'output_plain',
            ],
            'font.ctx.list': [
                'ctx.list',
            ],
            'font.toolbox': [
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
        }

        # apply to nodes
        apply_ref = self.apply
        skip_output = engine != 'legacy'
        for t, keys in nodes.items():
            for k in keys:
                if skip_output and k == "output":
                    continue
                apply_ref(k, t)

        # apply to notepads
        size = w.core.config.get('font_size')
        style_output = ctrl.theme.style('font.chat.output')
        if ui.notepad:
            for np in ui.notepad.values():
                ta = np.textarea
                ta.setStyleSheet(style_output)
                ta.value = size

        # apply to calendar
        note = ui.calendar.get('note')
        if note is not None:
            note.setStyleSheet(style_output)
            note.value = size

        # plain text/markdown
        output_plain = ui.nodes.get('output_plain', {})
        for obj in output_plain.values():
            try:
                obj.value = size
                obj.update()
            except Exception:
                pass

        # ------------------------

        # zoom, (Chromium, web engine)
        output_nodes = ui.nodes.get('output', {})
        if engine == 'web':
            zoom = w.core.config.get('zoom')
            for obj in output_nodes.values():
                try:
                    obj.value = zoom
                    obj.update_zoom()
                except Exception:
                    pass
            w.dispatch(RenderEvent(RenderEvent.ON_THEME_CHANGE))

        # font size, legacy (markdown)
        elif engine == 'legacy':
            for obj in output_nodes.values():
                obj.value = size
                obj.update()

        w.tools.setup_theme()  # update tools
