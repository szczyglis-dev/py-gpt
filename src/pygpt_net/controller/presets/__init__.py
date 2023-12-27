#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.26 21:00:00                  #
# ================================================== #

import re

from .editor import Editor
from pygpt_net.utils import trans


class Presets:
    def __init__(self, window=None):
        """
        Presets controller

        :param window: Window instance
        """
        self.window = window
        self.editor = Editor(window)

    def use(self):
        """Copy preset prompt to input"""
        self.window.controller.input.append(self.window.ui.nodes['preset.prompt'].toPlainText())

    def make_preset_filename(self, name):
        """
        Make preset filename from name

        :param name: preset name
        :return: preset filename
        :rtype: str
        """
        filename = name.lower()
        filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)
        return filename

    def duplicate(self, idx=None):
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
                    self.window.controller.model.update_presets()
                    idx = self.window.core.presets.get_idx_by_id(mode, new_id)
                    self.editor.edit(idx)
                    self.window.set_status(trans('status.preset.duplicated'))

    def clear(self, force=False):
        """
        Clear preset data

        :param force: force clear data
        """
        preset = self.window.core.config.get('preset')

        if not force:
            self.window.ui.dialogs.confirm('preset_clear', '', trans('confirm.preset.clear'))
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
                self.window.controller.model.update_presets()

        self.window.set_status(trans('status.preset.cleared'))

    def delete(self, idx=None, force=False):
        """
        Delete preset

        :param idx: preset index (row index)
        :param force: force delete without confirmation
        """
        if idx is not None:
            mode = self.window.core.config.get('mode')
            preset = self.window.core.presets.get_by_idx(idx, mode)
            if preset is not None and preset != "":
                if preset in self.window.core.presets.items:
                    # if exists then show confirmation dialog
                    if not force:
                        self.window.ui.dialogs.confirm('preset_delete', idx, trans('confirm.preset.delete'))
                        return

                    if preset == self.window.core.config.get('preset'):
                        self.window.core.config.set('preset', None)
                    self.window.core.presets.remove(preset, True)
                    self.window.controller.model.update_presets()
                    self.window.set_status(trans('status.preset.deleted'))

    def validate_filename(self, value):
        """
        Validate filename

        :param value: filename
        :return: sanitized filename
        :rtype: str
        """
        # strip not allowed characters
        return re.sub(r'[^\w\s-]', '', value)
