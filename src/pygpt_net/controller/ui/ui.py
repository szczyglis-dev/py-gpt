#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 02:00:00                  #
# ================================================== #

from typing import Optional

from PySide6.QtGui import QColor

from pygpt_net.core.types import MODE_IMAGE
from pygpt_net.core.events import BaseEvent, Event
from pygpt_net.utils import trans, short_num

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
        self.splitter_output_size_input = None
        self.splitter_output_size_files = None

        self._last_ctx_string = None
        self._last_input_string = None
        self._last_chat_model = None
        self._last_chat_label = None

        # Cache for Input tab tooltip to avoid redundant updates
        self._last_input_tab_tooltip = None
        self._input_extra_tab_idx = 4

    def setup(self):
        """Setup UI"""
        self.update_font_size()
        self.update()
        self.init_toolbox()

    def update(self):
        """Update all elements"""
        self.update_toolbox()
        self.update_chat_label()
        self.mode.update()
        self.update_tokens()
        self.vision.update()
        self.window.controller.agent.legacy.update()
        self.img_update_available_modes()
        self.img_update_available_resolutions()

    def handle(self, event: BaseEvent):
        """
        Handle events

        :param event: BaseEvent: Event to handle
        """
        name = event.name

        # on input begin
        if name == Event.INPUT_BEGIN:
            self.tabs.switch_to_first_chat()  # switch to first active chat tab
        elif name == Event.CTX_END:
            self.update_tokens()  # update UI

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
        self.init_computer_env()
        self.init_computer_sandbox()

    def init_computer_env(self):
        """Init computer environment"""
        env = self.window.core.config.get("remote_tools.computer_use.env", "linux")
        if env == "" or env is None:
            if self.window.core.platforms.is_windows():
                env = "windows"
            elif self.window.core.platforms.is_mac():
                env = "mac"
            else:
                env = "linux"
        node = self.window.ui.nodes["computer_env"]
        index = node.findData(env)
        if index != -1 and node.currentIndex() != index:
            node.setCurrentIndex(index)

    def init_computer_sandbox(self):
        """Init computer sandbox"""
        sandbox = bool(self.window.core.config.get("remote_tools.computer_use.sandbox", False))
        node = self.window.ui.nodes["computer_sandbox"]
        if node.isChecked() != sandbox:
            node.box.setChecked(sandbox)

    def on_computer_env_changed(self, env: str):
        """
        Handle computer environment change

        :param env: selected environment
        """
        cfg = self.window.core.config
        if cfg.get("remote_tools.computer_use.env") != env:
            cfg.set("remote_tools.computer_use.env", env)
            cfg.save()

    def on_computer_sandbox_toggled(self, checked: bool):
        """
        Handle computer sandbox toggle

        :param checked: bool
        """
        cfg = self.window.core.config
        if cfg.get("remote_tools.computer_use.sandbox") != checked:
            cfg.set("remote_tools.computer_use.sandbox", checked)
            cfg.save()

    def update_toolbox(self):
        """Update toolbox"""
        ctrl = self.window.controller
        ctrl.mode.update_mode()
        ctrl.model.update()
        ctrl.presets.refresh()
        ctrl.assistant.refresh()
        ctrl.idx.refresh()

    def format_tokens(self, num: int) -> str:
        """
        Format tokens
        :param num: number of tokens
        :return: formatted string
        """
        num = int(num)
        if num >= 1_000_000:
            return f"{num // 1_000_000}M"
        if num >= 1_000:
            return f"{num // 1_000}k"
        return str(num)

    def update_tokens(self):
        """Update tokens counter in real-time"""
        ui_nodes = self.window.ui.nodes

        # Read raw input for accurate character count (without trimming)
        raw_text = ui_nodes['input'].toPlainText()
        prompt = raw_text.strip()

        input_tokens, system_tokens, extra_tokens, ctx_tokens, ctx_len, ctx_len_all, \
            sum_tokens, max_current, threshold = self.window.core.tokens.get_current(prompt)
        attachments_tokens = self.window.controller.chat.attachment.get_current_tokens()
        sum_tokens += attachments_tokens

        ctx_string = f"{short_num(ctx_len)} / {short_num(ctx_len_all)} - {short_num(ctx_tokens)} {trans('ctx.tokens')}"
        if ctx_string != self._last_ctx_string:
            ui_nodes['prompt.context'].setText(ctx_string)
            self._last_ctx_string = ctx_string

        if max_current > 0:
            max_str = short_num(max_current)
        else:
            max_str = "∞"

        input_string = f"{short_num(input_tokens)} + {short_num(system_tokens)} + {short_num(ctx_tokens)} + {short_num(extra_tokens)} + {short_num(attachments_tokens)} = {short_num(sum_tokens)} / {max_str}"
        if input_string != self._last_input_string:
            ui_nodes['input.counter'].setText(input_string)
            self._last_input_string = input_string

        # Update Input tab tooltip with live "<chars> chars (~<tokens> tokens)" string
        try:
            tabs = self.window.ui.tabs.get('input')
        except Exception:
            tabs = None

        if tabs is not None:
            try:
                tooltip = trans("input.tab.tooltip").format(chars=short_num(len(raw_text)), tokens=short_num(input_tokens))
            except Exception:
                tooltip = ""
            #tooltip = f"{short_num(len(raw_text))} chars (~{short_num(input_tokens)} tokens)"
            if tooltip != self._last_input_tab_tooltip:
                tabs.setTabToolTip(0, tooltip)
                self._last_input_tab_tooltip = tooltip

    def store_state(self):
        """Store UI state"""
        self.window.controller.layout.scroll_save()

    def restore_state(self):
        """Restore UI state"""
        self.window.controller.layout.scroll_restore()

    def update_chat_label(self):
        """Update chat label"""
        model = self.window.core.config.get('model')
        model_str = "" if not model else str(model)
        if model_str != self._last_chat_model:
            self.window.ui.nodes['chat.model'].setText(model_str)
            self._last_chat_model = model_str

    def update_ctx_label(self, label: Optional[str] = None):
        """
        Update ctx label

        :param label: label
        """
        mode = self.window.core.config.get('mode')
        allowed = self.window.core.ctx.is_allowed_for_mode(mode)
        if label is None:
            label = ''
        if allowed:
            label += ' (+)'
        label_str = str(label)
        if label_str != self._last_chat_label:
            self.window.ui.nodes['chat.label'].setText(label_str)
            self._last_chat_label = label_str

    def show_global_stop(self):
        """Show global stop button"""
        node = self.window.ui.nodes['global.stop']
        if not node.isVisible():
            node.setVisible(True)

    def hide_global_stop(self):
        """Hide global stop button"""
        node = self.window.ui.nodes['global.stop']
        if node.isVisible():
            node.setVisible(False)

    def on_global_stop(self):
        """Global stop button action"""
        if self.stop_action == "idx":
            self.window.controller.idx.force_stop()

    def img_update_available_resolutions(self):
        """Update available resolutions for images"""
        mode = self.window.core.config.get('mode')
        if mode != MODE_IMAGE:
            return
        model = self.window.core.config.get('model')
        keys = self.window.core.image.get_available_resolutions(model)
        current = self.window.core.config.get('img_resolution', '1024x1024')
        self.window.ui.config['global']['img_resolution'].set_keys(keys, lock=False)
        self.window.controller.config.apply_value(
            parent_id="global",
            key="img_resolution",
            option=self.window.core.image.get_resolution_option(),
            value=current,
        )

    def img_update_available_modes(self):
        """Update available modes for images"""
        mode = self.window.core.config.get('mode')
        if mode != MODE_IMAGE:
            return
        model = self.window.core.config.get('model')
        keys = self.window.core.image.get_available_modes(model)
        current = self.window.core.config.get('img_mode', 'image')
        self.window.ui.config['global']['img_mode'].set_keys(keys, lock=False)
        self.window.controller.config.apply_value(
            parent_id="global",
            key="img_mode",
            option=self.window.core.image.get_mode_option(),
            value=current,
        )

    def show_input_extra(self):
        """Show extra input area"""
        if self.window.ui.tabs['input'].isTabVisible(self._input_extra_tab_idx):
            return
        self.window.ui.tabs['input'].setTabText(self._input_extra_tab_idx, trans('input.tab.extra.negative_prompt'))
        self.window.ui.tabs['input'].setTabVisible(self._input_extra_tab_idx, True)

    def hide_input_extra(self):
        """Hide extra input area"""
        if not self.window.ui.tabs['input'].isTabVisible(self._input_extra_tab_idx):
            return
        self.window.ui.tabs['input'].setTabVisible(self._input_extra_tab_idx, False)
        self.window.ui.tabs['input'].setCurrentIndex(0)