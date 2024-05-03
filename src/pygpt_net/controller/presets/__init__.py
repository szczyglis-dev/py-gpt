#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.03 12:00:00                  #
# ================================================== #

import re

from PySide6.QtGui import QTextCursor

from pygpt_net.controller.presets.editor import Editor
from pygpt_net.core.access.events import AppEvent
from pygpt_net.utils import trans


class Presets:
    def __init__(self, window=None):
        """
        Presets controller

        :param window: Window instance
        """
        self.window = window
        self.editor = Editor(window)
        self.locked = False

    def setup(self):
        """Setup presets"""
        self.editor.setup()

    def select(self, idx: int):
        """
        Select preset

        :param idx: value of the list (row idx)
        """
        # check if preset change is not locked
        if self.preset_change_locked():
            return
        mode = self.window.core.config.get('mode')
        self.set_by_idx(mode, idx)  # set global and current dict

        # update all layout
        self.window.controller.ui.update()
        self.window.core.dispatcher.dispatch(AppEvent(AppEvent.PRESET_SELECTED))  # app event

    def next(self):
        """Select next preset"""
        idx = self.window.ui.nodes['preset.presets'].currentIndex().row()
        idx += 1
        if idx >= self.window.ui.models['preset.presets'].rowCount():
            idx = 0
        self.select(idx)

    def prev(self):
        """Select previous preset"""
        idx = self.window.ui.nodes['preset.presets'].currentIndex().row()
        idx -= 1
        if idx < 0:
            idx = self.window.ui.models['preset.presets'].rowCount() - 1
        self.select(idx)

    def use(self):
        """Copy preset prompt to input"""
        self.window.controller.chat.common.append_to_input(
            self.window.ui.nodes['preset.prompt'].toPlainText()
        )

    def paste_prompt(self, idx: int, parent: str = "global"):
        """
        Paste prompt from template

        :param idx: prompt index
        :param parent: parent name
        """
        template = self.window.core.prompt.template.get_by_id(idx)
        if template is None:
            return
        if parent == "global":
            self.paste_to_textarea(self.window.ui.nodes['preset.prompt'], template['prompt'])
        elif parent == "input":
            self.paste_to_textarea(self.window.ui.nodes['input'], template['prompt'])
        elif parent == "editor":
            self.paste_to_textarea(self.window.ui.config["preset"]["prompt"], template['prompt'])

    def paste_to_textarea(self, textarea, text: str):
        """
        Paste text to textarea

        :param textarea: textarea widget
        :param text: text to paste
        """
        separator = "\n"
        prev_text = textarea.toPlainText()
        cur = textarea.textCursor()
        cur.movePosition(QTextCursor.End)
        text = str(text).strip()
        if prev_text.strip() != "":
            text = separator + text
        s = text
        while s:
            head, sep, s = s.partition("\n")
            cur.insertText(head)
            if sep:
                cur.insertBlock()
        cur.movePosition(QTextCursor.End)
        textarea.setTextCursor(cur)
        textarea.setFocus()

    def set(self, mode: str, preset_id: str):
        """
        Set preset

        :param mode: mode name
        :param preset_id: preset ID
        """
        if not self.window.core.presets.has(mode, preset_id):
            return False
        self.window.core.config.data['preset'] = preset_id
        if 'current_preset' not in self.window.core.config.data:
            self.window.core.config.data['current_preset'] = {}
        self.window.core.config.data['current_preset'][mode] = preset_id

    def set_by_idx(self, mode: str, idx: int):
        """
        Set preset by index

        :param mode: mode name
        :param idx: preset index
        """
        preset_id = self.window.core.presets.get_by_idx(idx, mode)

        # set preset
        self.window.core.config.set("preset", preset_id)
        if 'current_preset' not in self.window.core.config.data:
            self.window.core.config.data['current_preset'] = {}
        self.window.core.config.data['current_preset'][mode] = preset_id

        # select model
        self.select_model()

    def select_current(self):
        """Select preset by current"""
        mode = self.window.core.config.get('mode')
        preset_id = self.window.core.config.get('preset')
        items = self.window.core.presets.get_by_mode(mode)
        if preset_id in items:
            idx = list(items.keys()).index(preset_id)
            current = self.window.ui.models['preset.presets'].index(idx, 0)
            self.window.ui.nodes['preset.presets'].setCurrentIndex(current)

    def select_default(self):
        """Set default preset"""
        preset_id = self.window.core.config.get('preset')

        # if preset is not set, set default
        if preset_id is None or preset_id == "":
            mode = self.window.core.config.get('mode')
            # set previously selected preset
            current = self.window.core.config.get('current_preset')  # dict of modes, preset per mode
            if mode in current and \
                    current[mode] is not None and \
                    current[mode] != "" and \
                    current[mode] in self.window.core.presets.get_by_mode(mode):
                self.window.core.config.set('preset', current[mode])
            else:
                # or set default preset
                self.window.core.config.set('preset', self.window.core.presets.get_default(mode))

    def update_data(self):
        """Update preset data"""
        preset_id = self.window.core.config.get('preset')
        if preset_id is None or preset_id == "":
            self.reset()  # clear preset fields
            self.window.controller.mode.reset_current()
            return

        if preset_id not in self.window.core.presets.items:
            self.window.core.config.set('preset', "")  # clear preset if not found
            self.reset()  # clear preset fields
            self.window.controller.mode.reset_current()
            return

        # update preset fields
        preset = self.window.core.presets.items[preset_id]
        self.window.ui.nodes['preset.prompt'].setPlainText(preset.prompt)
        # self.window.ui.nodes['preset.ai_name'].setText(preset.ai_name)
        # self.window.ui.nodes['preset.user_name'].setText(preset.user_name)

        # update current data
        self.window.core.config.set('prompt', preset.prompt)
        self.window.core.config.set('ai_name', preset.ai_name)
        self.window.core.config.set('user_name', preset.user_name)

    def update_current(self):
        """Update current mode, model and preset"""
        mode = self.window.core.config.get('mode')

        # if preset chosen, update current config
        preset_id = self.window.core.config.get('preset')
        if preset_id is not None and preset_id != "":
            if preset_id in self.window.core.presets.items:
                preset = self.window.core.presets.items[preset_id]
                self.window.core.config.set('user_name', preset.user_name)
                self.window.core.config.set('ai_name', preset.ai_name)
                self.window.core.config.set('prompt', preset.prompt)
                self.window.core.config.set('temperature', preset.temperature)
                return

        self.window.core.config.set('user_name', None)
        self.window.core.config.set('ai_name', None)
        self.window.core.config.set('temperature', 1.0)

        # set default prompt if mode is chat
        if mode == 'chat':
            self.window.core.config.set('prompt', self.window.core.prompt.get('default'))
        else:
            self.window.core.config.set('prompt', None)

    def get_current_functions(self) -> list or None:
        """
        Get current preset functions

        :return: list of functions
        """
        preset_id = self.window.core.config.get('preset')
        if preset_id is not None and preset_id != "":
            if preset_id in self.window.core.presets.items:
                preset = self.window.core.presets.items[preset_id]
                if preset.has_functions():
                    return preset.get_functions()
        return None

    def from_global(self):
        """Update current preset from global prompt"""
        if self.locked:
            return
        preset_id = self.window.core.config.get('preset')
        if preset_id is not None and preset_id != "":
            if preset_id in self.window.core.presets.items:
                preset = self.window.core.presets.items[preset_id]
                preset.prompt = self.window.core.config.get('prompt')
                self.window.core.presets.save(preset)

    def select_model(self):
        """Select model by current preset"""
        mode = self.window.core.config.get('mode')
        preset_id = self.window.core.config.get('preset')
        if preset_id is not None and preset_id != "":
            if preset_id in self.window.core.presets.items:
                preset = self.window.core.presets.items[preset_id]
                if preset.model is not None and preset.model != "" and preset.model != "_":
                    if preset.model in self.window.core.models.items:
                        if self.window.core.models.has(preset.model) \
                                and self.window.core.models.is_allowed(preset.model, mode):
                            self.window.core.config.set('model', preset.model)
                            self.window.controller.model.set(mode, preset.model)
                            self.window.controller.model.update_list()
                            self.window.controller.model.select_current()

    def refresh(self):
        """Refresh presets"""
        mode = self.window.core.config.get('mode')
        if mode == 'assistant':
            return

        self.select_default()  # if no preset then select previous from current presets
        self.update_current()  # apply preset data to current config
        self.update_data()  # update config and prompt from preset data
        self.window.controller.mode.update_temperature()
        self.update_list()  # update presets list only
        self.select_current()  # select current preset on list

    def update_list(self):
        """Update presets list"""
        mode = self.window.core.config.get('mode')
        items = self.window.core.presets.get_by_mode(mode)
        self.window.ui.toolbox.presets.update_presets(items)

    def reset(self):
        """Reset preset data"""
        self.window.ui.nodes['preset.prompt'].setPlainText("")
        # self.window.ui.nodes['preset.ai_name'].setText("")
        # self.window.ui.nodes['preset.user_name'].setText("")

    def make_filename(self, name: str) -> str:
        """
        Make preset filename from name

        :param name: preset name
        :return: preset filename
        """
        filename = name.lower()
        filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
        return filename

    def duplicate(self, idx: int = None):
        """
        Duplicate preset

        :param idx: preset index (row index)
        """
        if idx is not None:
            mode = self.window.core.config.get('mode')
            preset = self.window.core.presets.get_by_idx(idx, mode)
            if preset is not None and preset != "":
                if preset in self.window.core.presets.items:
                    new_id = self.window.core.presets.duplicate(preset)
                    self.window.core.config.set('preset', new_id)
                    self.refresh()
                    idx = self.window.core.presets.get_idx_by_id(mode, new_id)
                    self.editor.edit(idx)
                    self.window.ui.status(trans('status.preset.duplicated'))

    def enable(self, idx: int = None):
        """
        Enable preset

        :param idx: preset index (row index)
        """
        if idx is not None:
            mode = self.window.core.config.get('mode')
            preset_id = self.window.core.presets.get_by_idx(idx, mode)
            if preset_id is not None and preset_id != "":
                if preset_id in self.window.core.presets.items:
                    self.window.core.presets.enable(preset_id)
                    self.refresh()

    def disable(self, idx: int = None):
        """
        Disable preset

        :param idx: preset index (row index)
        """
        if idx is not None:
            mode = self.window.core.config.get('mode')
            preset_id = self.window.core.presets.get_by_idx(idx, mode)
            if preset_id is not None and preset_id != "":
                if preset_id in self.window.core.presets.items:
                    self.window.core.presets.disable(preset_id)
                    self.refresh()

    def clear(self, force: bool = False):
        """
        Clear preset data

        :param force: force clear data
        """
        preset = self.window.core.config.get('preset')

        if not force:
            self.window.ui.dialogs.confirm(
                type='preset_clear', 
                id='', 
                msg=trans('confirm.preset.clear'),
            )
            return

        self.window.core.config.set('prompt', "")
        self.window.core.config.set('ai_name', "")
        self.window.core.config.set('user_name', "")
        self.window.core.config.set('temperature', 1.0)

        if preset is not None and preset != "":
            if preset in self.window.core.presets.items:
                self.window.core.presets.items[preset].ai_name = ""
                self.window.core.presets.items[preset].user_name = ""
                self.window.core.presets.items[preset].prompt = ""
                self.window.core.presets.items[preset].temperature = 1.0
                self.refresh()

        self.window.ui.status(trans('status.preset.cleared'))

        # reload assistant default instructions
        mode = self.window.core.config.get('mode')
        if mode == "assistant":
            self.window.core.assistants.load()

    def delete(self, idx: int = None, force: bool = False):
        """
        Delete preset

        :param idx: preset index (row index)
        :param force: force delete without confirmation
        """
        if idx is not None:
            mode = self.window.core.config.get('mode')
            preset_id = self.window.core.presets.get_by_idx(idx, mode)
            if preset_id is not None and preset_id != "":
                if preset_id in self.window.core.presets.items:
                    # if exists show confirmation dialog
                    if not force:
                        self.window.ui.dialogs.confirm(
                            type='preset_delete', 
                            id=idx, 
                            msg=trans('confirm.preset.delete'),
                        )
                        return

                    if preset_id == self.window.core.config.get('preset'):
                        self.window.core.config.set('preset', None)
                        self.window.ui.nodes['preset.prompt'].setPlainText("")
                    self.window.core.presets.remove(preset_id, True)
                    self.refresh()
                    self.window.ui.status(trans('status.preset.deleted'))

    def restore(self, force: bool = False):
        """
        Restore preset data

        :param force: force restore data
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='preset_restore',
                id='',
                msg=trans('confirm.preset.restore'),
            )
            return
        mode = self.window.core.config.get('mode')
        if mode == "agent":
            mode = "expert"  # shared presets
        self.window.core.presets.restore(mode)
        self.refresh()

    def is_current(self, idx: int = None) -> bool:
        """
        Check if preset is current

        :param idx: preset index (row index)
        :return: True if current
        """
        if idx is not None:
            mode = self.window.core.config.get('mode')
            if mode == "agent":
                mode = "expert"  # shared presets
            preset_id = self.window.core.presets.get_by_idx(idx, mode)
            if preset_id is not None and preset_id != "":
                if preset_id == "current." + mode:
                    return True
        return False

    def validate_filename(self, value: str) -> str:
        """
        Validate filename

        :param value: filename
        :return: sanitized filename
        """
        # strip not allowed characters
        return re.sub(r'[^\w\s\-\.]', '', value)

    def preset_change_locked(self) -> bool:
        """
        Check if preset change is locked

        :return: True if locked
        """
        # if self.window.controller.chat.input.generating:
        # return True
        mode = self.window.core.config.get('mode')
        if mode == "assistant":
            return True
        return False

    def reload(self):
        """Reload presets"""
        self.locked = True
        self.window.core.presets.load()
        self.refresh()
        self.locked = False
