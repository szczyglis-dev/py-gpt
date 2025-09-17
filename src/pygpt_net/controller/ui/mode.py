#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.17 20:00:00                  #
# ================================================== #

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_ASSISTANT,
    MODE_EXPERT,
    MODE_IMAGE,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_COMPUTER,
    MODE_AGENT_OPENAI,
    MODE_COMPLETION,
    MODE_AUDIO,
)
from pygpt_net.core.tabs.tab import Tab
from pygpt_net.core.events import Event
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

        ui_nodes = self.window.ui.nodes
        ui_tabs = self.window.ui.tabs
        ui_menu = self.window.ui.menu
        ctrl = self.window.controller
        presets_editor = ctrl.presets.editor

        is_assistant = mode == MODE_ASSISTANT
        is_computer = mode == MODE_COMPUTER
        is_agent = mode == MODE_AGENT
        is_agent_llama = mode == MODE_AGENT_LLAMA
        is_agent_openai = mode == MODE_AGENT_OPENAI
        is_expert = mode == MODE_EXPERT
        is_image = mode == MODE_IMAGE
        is_llama_index = mode == MODE_LLAMA_INDEX
        is_completion = mode == MODE_COMPLETION
        is_audio = mode == MODE_AUDIO

        if not is_audio:
            ui_nodes['audio.auto_turn'].setVisible(False)
            ui_nodes["audio.loop"].setVisible(False)
            if not ctrl.plugins.is_enabled('audio_output'):
                ctrl.audio.toggle_output_icon(False)
        else:
            ui_nodes['audio.auto_turn'].setVisible(True)
            ui_nodes["audio.loop"].setVisible(True)
            if not ctrl.audio.is_muted():
                ctrl.audio.toggle_output_icon(True)
            else:
                ctrl.audio.toggle_output_icon(False)

        if not is_assistant:
            ui_nodes['presets.widget'].setVisible(True)
        else:
            ui_nodes['presets.widget'].setVisible(False)

        if not is_computer:
            ui_nodes['env.widget'].setVisible(False)
        else:
            ui_nodes['env.widget'].setVisible(True)

        show_agents_label = is_agent or is_agent_llama or is_agent_openai
        if show_agents_label:
            ui_nodes['preset.agents.label'].setVisible(True)
            ui_nodes['preset.experts.label'].setVisible(False)
            ui_nodes['preset.presets.label'].setVisible(False)
        elif is_expert:
            ui_nodes['preset.agents.label'].setVisible(False)
            ui_nodes['preset.experts.label'].setVisible(True)
            ui_nodes['preset.presets.label'].setVisible(False)
        else:
            ui_nodes['preset.agents.label'].setVisible(False)
            ui_nodes['preset.experts.label'].setVisible(False)
            ui_nodes['preset.presets.label'].setVisible(True)

        if is_expert:
            ui_nodes['preset.editor.description'].setVisible(True)
            presets_editor.toggle_tab("remote_tools", True)
        else:
            presets_editor.toggle_tab("remote_tools", False)
            ui_nodes['preset.editor.description'].setVisible(False)

        if is_completion:
            ui_nodes['preset.editor.user_name'].setVisible(True)
        else:
            ui_nodes['preset.editor.user_name'].setVisible(False)

        if is_agent_openai:
            ui_nodes['preset.editor.agent_provider_openai'].setVisible(True)
        else:
            ui_nodes['preset.editor.agent_provider_openai'].setVisible(False)

        if is_agent:
            presets_editor.toggle_tab("experts", True)
            ui_nodes['preset.editor.temperature'].setVisible(True)
            ui_nodes['preset.editor.idx'].setVisible(False)
            ui_nodes['preset.editor.agent_provider'].setVisible(False)
            ui_nodes['preset.editor.modes'].setVisible(False)
            ui_tabs['preset.editor.extra'].setTabText(0, trans("preset.prompt.agent"))
        elif is_agent_llama:
            presets_editor.toggle_tab("experts", False)
            ui_nodes['preset.editor.temperature'].setVisible(False)
            ui_nodes['preset.editor.idx'].setVisible(True)
            ui_nodes['preset.editor.agent_provider'].setVisible(True)
            ui_nodes['preset.editor.modes'].setVisible(False)
            ui_tabs['preset.editor.extra'].setTabText(0, trans("preset.prompt.agent_llama"))
        elif is_agent_openai:
            presets_editor.toggle_tab("experts", True)
            ui_nodes['preset.editor.temperature'].setVisible(False)
            ui_nodes['preset.editor.idx'].setVisible(True)
            ui_nodes['preset.editor.agent_provider'].setVisible(False)
            ui_nodes['preset.editor.modes'].setVisible(False)
            ui_tabs['preset.editor.extra'].setTabText(0, trans("preset.prompt.agent_llama"))
        else:
            if is_expert:
                ui_nodes['preset.editor.idx'].setVisible(True)
            else:
                ui_nodes['preset.editor.idx'].setVisible(False)

            presets_editor.toggle_tab("experts", False)
            ui_nodes['preset.editor.temperature'].setVisible(True)
            ui_nodes['preset.editor.agent_provider'].setVisible(False)
            ui_nodes['preset.editor.modes'].setVisible(True)
            ui_tabs['preset.editor.extra'].setTabText(0, trans("preset.prompt"))

        if is_image:
            ui_nodes['media.raw'].setVisible(True)
            if ctrl.media.is_video_model():
                ui_nodes['video.options'].setVisible(True)
                ui_nodes['dalle.options'].setVisible(False)
            elif ctrl.media.is_image_model():
                ui_nodes['dalle.options'].setVisible(True)
                ui_nodes['video.options'].setVisible(False)
            else:
                ui_nodes['media.raw'].setVisible(False)
                ui_nodes['dalle.options'].setVisible(False)
                ui_nodes['video.options'].setVisible(False)
        else:
            ui_nodes['media.raw'].setVisible(False)
            ui_nodes['dalle.options'].setVisible(False)
            ui_nodes['video.options'].setVisible(False)

        if is_agent:
            ui_nodes['agent.options'].setVisible(True)
        else:
            ui_nodes['agent.options'].setVisible(False)

        if is_agent_llama or is_agent_openai:
            ui_nodes['agent_llama.options'].setVisible(True)
        else:
            ui_nodes['agent_llama.options'].setVisible(False)

        if is_assistant:
            ui_nodes['assistants.widget'].setVisible(True)
        else:
            ui_nodes['assistants.widget'].setVisible(False)

        if is_llama_index:
            ui_nodes['idx.options'].setVisible(True)
        else:
            ui_nodes['idx.options'].setVisible(False)

        if is_image:
            ui_nodes['input.stream'].setVisible(False)
        else:
            ui_nodes['input.stream'].setVisible(True)

        show = self.is_vision(mode)
        ui_menu['menu.video'].menuAction().setVisible(show)
        ui_nodes['icon.video.capture'].setVisible(show)
        ui_nodes['attachments.capture_clear'].setVisible(show)

        show = self.are_attachments(mode)
        ui_tabs['input'].setTabVisible(1, show)

        # remote tools icon visibility
        if not is_image and not is_completion:
            ui_nodes['icon.remote_tool.web'].setVisible(True)
        else:
            ui_nodes['icon.remote_tool.web'].setVisible(False)

        ui_tabs['input'].setTabVisible(2, is_assistant)
        ui_tabs['input'].setTabVisible(3, (not is_assistant) and (not is_image))

        presets_editor.toggle_extra_options()

        self.toggle_chat_footer()

    def toggle_chat_footer(self):
        """Toggle chat footer"""
        if self.window.controller.ui.tabs.get_current_type() != Tab.TAB_CHAT:
            self.hide_chat_footer()
        else:
            self.show_chat_footer()

    def is_vision(self, mode: str) -> bool:
        """
        Check if vision is allowed

        :param mode: current mode
        :return: True if vision is allowed
        """
        ctrl = self.window.controller
        if ctrl.ui.vision.has_vision():
            return True

        if ctrl.painter.is_active():
            return True

        value = False
        event = Event(Event.UI_VISION, {
            'mode': mode,
            'value': value,
        })
        self.window.dispatch(event)
        return event.data['value']

    def are_attachments(self, mode: str) -> bool:
        """
        Check if attachments are allowed

        :param mode: current mode
        :return: True if attachments are allowed
        """
        event = Event(Event.UI_ATTACHMENTS, {
            'mode': mode,
            'value': True,
        })
        self.window.dispatch(event)
        return event.data['value']

    def show_chat_footer(self):
        """Show chat footer"""
        self.window.ui.nodes['chat.footer'].setVisible(True)

    def hide_chat_footer(self):
        """Hide chat footer"""
        self.window.ui.nodes['chat.footer'].setVisible(False)