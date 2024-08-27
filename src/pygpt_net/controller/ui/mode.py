# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.27 22:00:00                  #
# ================================================== #

from pygpt_net.core.dispatcher import Event
from pygpt_net.utils import trans


class Mode:
    def __init__(self, window=None):
        """
        UI mode switch controller

        :param window: Window instance
        """
        self.window = window

    def update(self):
        """Update mode, model, preset and rest of the toolbox"""

        mode = self.window.core.config.data['mode']

        # presets
        if mode != "assistant":
            self.window.ui.nodes['presets.widget'].setVisible(True)
        else:
            self.window.ui.nodes['presets.widget'].setVisible(False)

        # presets: labels
        if mode == "agent":
            self.window.ui.nodes['preset.agents.label'].setVisible(True)
            self.window.ui.nodes['preset.experts.label'].setVisible(False)
            self.window.ui.nodes['preset.presets.label'].setVisible(False)
        elif mode == "expert":
            self.window.ui.nodes['preset.agents.label'].setVisible(False)
            self.window.ui.nodes['preset.experts.label'].setVisible(True)
            self.window.ui.nodes['preset.presets.label'].setVisible(False)
        else:
            self.window.ui.nodes['preset.agents.label'].setVisible(False)
            self.window.ui.nodes['preset.experts.label'].setVisible(False)
            self.window.ui.nodes['preset.presets.label'].setVisible(True)

        # presets: editor
        if mode == "agent":
            self.window.ui.nodes['preset.editor.functions'].setVisible(False)
            self.window.ui.nodes['preset.editor.modes'].setVisible(False)
            self.window.ui.nodes['preset.editor.experts'].setVisible(True)
            self.window.ui.nodes["preset.prompt.label"].setText(trans("preset.prompt.agent"))
        else:
            self.window.ui.nodes['preset.editor.functions'].setVisible(True)
            self.window.ui.nodes['preset.editor.modes'].setVisible(True)
            self.window.ui.nodes['preset.editor.experts'].setVisible(False)
            self.window.ui.nodes["preset.prompt.label"].setText(trans("preset.prompt"))

        # presets: clear
        self.window.ui.nodes['preset.clear'].setVisible(False)
        """
        if mode in ["img", "assistant"]:
            self.window.ui.nodes['preset.clear'].setVisible(False)
        else:
            self.window.ui.nodes['preset.clear'].setVisible(True)
        """

        # presets: use
        if mode == 'img':
            self.window.ui.nodes['preset.use'].setVisible(True)
        else:
            self.window.ui.nodes['preset.use'].setVisible(False)

        # img options
        if mode == "img":
            self.window.ui.nodes['dalle.options'].setVisible(True)
        else:
            self.window.ui.nodes['dalle.options'].setVisible(False)

        # agent options
        if mode == "agent":
            self.window.ui.nodes['agent.options'].setVisible(True)
        else:
            self.window.ui.nodes['agent.options'].setVisible(False)

        # assistants list
        if mode == "assistant":
            self.window.ui.nodes['assistants.widget'].setVisible(True)
        else:
            self.window.ui.nodes['assistants.widget'].setVisible(False)

        # indexes list
        if mode == "llama_index":
            # self.window.ui.nodes['indexes.widget'].setVisible(True)
            self.window.ui.nodes['idx.options'].setVisible(True)
        else:
            # self.window.ui.nodes['indexes.widget'].setVisible(False)
            self.window.ui.nodes['idx.options'].setVisible(False)

        # stream mode
        if mode in ["img"]:
            self.window.ui.nodes['input.stream'].setVisible(False)
        else:
            self.window.ui.nodes['input.stream'].setVisible(True)

        # vision
        show = self.is_vision(mode)
        self.window.ui.menu['menu.video'].menuAction().setVisible(show)
        self.window.ui.nodes['icon.video.capture'].setVisible(show)
        # self.window.ui.nodes['vision.capture.options'].setVisible(show)
        self.window.ui.nodes['attachments.capture_clear'].setVisible(show)

        # attachments
        show = self.are_attachments(mode)
        self.window.ui.tabs['input'].setTabVisible(1, show)  # attachments

        # uploaded files
        if mode == "assistant":
            self.window.ui.tabs['input'].setTabVisible(2, True)
        else:
            self.window.ui.tabs['input'].setTabVisible(2, False)

        # toggle chat footer
        if not self.is_chat_tab():
            self.hide_chat_footer()
        else:
            self.show_chat_footer()

    def is_vision(self, mode: str) -> bool:
        """
        Check if vision is allowed

        :param mode: current mode
        """
        if mode == "vision":
            return True

        allowed = self.window.controller.painter.is_active()
        if allowed:
            return True

        if mode in ["img", "assistant"]:
            return False

        if self.window.controller.ui.vision.is_vision_model():
            return True

        # event: UI: vision
        value = False
        event = Event(Event.UI_VISION, {
            'mode': mode,
            'value': value,
        })
        self.window.core.dispatcher.dispatch(event)
        return event.data['value']

    def are_attachments(self, mode: str) -> bool:
        """Check if attachments are allowed"""
        if mode in ["vision", "assistant"]:
            return True

        if mode == "img":
            return False

        if self.window.controller.ui.vision.is_vision_model():
            return True

        # event: UI: attachments
        value = False
        event = Event(Event.UI_ATTACHMENTS, {
            'mode': mode,
            'value': value,
        })
        self.window.core.dispatcher.dispatch(event)
        return event.data['value']

    def is_chat_tab(self) -> bool:
        """Check if current tab is chat"""
        return self.window.controller.ui.current_tab == self.window.controller.ui.tab_idx['chat']

    def show_chat_footer(self):
        """Show chat footer"""
        self.window.ui.nodes['chat.footer'].setVisible(True)

    def hide_chat_footer(self):
        """Hide chat footer"""
        self.window.ui.nodes['chat.footer'].setVisible(False)

