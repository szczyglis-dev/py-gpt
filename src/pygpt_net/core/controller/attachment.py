#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.10 13:00:00                  #
# ================================================== #
import os
from datetime import datetime

from PySide6.QtWidgets import QFileDialog
from pathlib import PurePath
from showinfm import show_in_file_manager

from ..utils import trans
from ..attachments import Attachments


class Attachment:
    def __init__(self, window=None):
        """
        Attachment controller

        :param window: main window object
        """
        self.window = window
        self.attachments = Attachments(self.window.config)

    def setup(self):
        """Setup attachments"""
        # send clear
        if 'attachments_send_clear' in self.window.config.data and self.window.config.data['attachments_send_clear']:
            self.window.data['attachments.send_clear'].setChecked(True)
        else:
            self.window.data['attachments.send_clear'].setChecked(False)

        self.attachments.load()
        self.update()

    def update(self):
        """Update attachments list"""
        mode = self.window.config.data['mode']
        items = self.attachments.get_all(mode)
        self.window.ui.attachments.update_list('attachments', items)
        self.update_tab_label(mode)

    def update_tab_label(self, mode):
        """
        Updates tab label

        :param mode: mode
        """
        num_files = self.attachments.count(mode)
        suffix = ''
        if num_files > 0:
            suffix = f' ({num_files})'
        self.window.tabs['input'].setTabText(1, trans('attachments.tab') + suffix)

    def select(self, mode, idx):
        """
        Selects attachment

        :param mode: mode
        :param idx: index
        """
        self.attachments.current = self.attachments.get_id_by_idx(mode, idx)

    def selection_change(self):
        """
        Selects on list change
        """
        # TODO: implement this
        pass

    def delete(self, idx, force=False):
        """
        Deletes attachment

        :param mode: mode
        :param idx: index
        :param force: force delete
        """
        mode = self.window.config.data['mode']
        if not force:
            self.window.ui.dialogs.confirm('attachments.delete', idx, trans('attachments.delete.confirm'))
            return

        file_id = self.attachments.get_id_by_idx(mode, idx)
        self.attachments.delete(mode, file_id)
        if self.attachments.current == file_id:
            self.attachments.current = None

        # delete file from assistant data
        if self.window.config.data['mode'] == 'assistant':
            assistant_id = self.window.config.data['assistant']
            if assistant_id is not None:
                self.window.controller.assistant.delete_file(assistant_id, file_id)

        self.update()

    def rename(self, mode, idx):
        """
        Renames attachment

        :param mode: mode
        :param idx: selected attachment index
        """
        file_id = self.attachments.get_id_by_idx(mode, idx)
        data = self.attachments.get_by_id(mode, file_id)
        if data is None:
            return

        self.window.dialog['rename'].id = 'attachment'
        self.window.dialog['rename'].input.setText(data.name)
        self.window.dialog['rename'].current = file_id
        self.window.dialog['rename'].show()
        self.update()

    def update_name(self, file_id, name):
        """
        Updates name

        :param file_id: file_id
        :param name: name
        """
        mode = self.window.config.data['mode']
        self.attachments.rename_file(mode, file_id, name)

        # rename filename in assistant data
        assistant_id = self.window.config.data['assistant']
        if self.window.config.data['mode'] == 'assistant' and assistant_id is not None:
            self.window.controller.assistant.rename_file(assistant_id, file_id, name)

        self.window.dialog['rename'].close()
        self.update()

    def add(self, mode, item):
        """
        Adds attachment item

        :param mode: mode
        :param item: item
        """
        self.attachments.add(mode, item)
        self.update()

    def clear(self, force=False):
        """
        Clears attachments list

        :param force: force clear
        """
        if not force:
            self.window.ui.dialogs.confirm('attachments.clear', -1, trans('attachments.clear.confirm'))
            return

        # delete from attachments
        mode = self.window.config.data['mode']
        self.attachments.delete_all(mode)

        # delete files from assistant
        if self.window.config.data['mode'] == 'assistant':
            assistant_id = self.window.config.data['assistant']
            if assistant_id is not None:
                self.window.controller.assistant.clear_files(assistant_id)

        self.update()

    def open_add(self):
        mode = self.window.config.data['mode']
        dialog = QFileDialog(self.window)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        if dialog.exec():
            files = dialog.selectedFiles()
            for path in files:
                basename = os.path.basename(path)
                self.attachments.new(mode, basename, path, False)
            self.attachments.save()
            self.update()

    def open_dir(self, mode, idx):
        """
        Opens in directory

        :param mode: mode
        :param idx: index
        """
        file_id = self.attachments.get_id_by_idx(mode, idx)
        data = self.attachments.get_by_id(mode, file_id)
        if data.path is not None and data.path != '' and os.path.exists(data.path):
            path = data.path
            parts = path_split = PurePath(path).parts
            path_os = os.path.join(*parts)  # fix for windows \\ path separators
            show_in_file_manager(path_os)

    def toggle_send_clear(self, value):
        """
        Toggles send clear

        :param value: value of the checkbox
        """
        self.window.config.data['attachments_send_clear'] = value

    def import_from_assistant(self, mode, assistant):
        """
        Loads attachments from assistant

        :param mode: mode
        :param assistant: assistant
        """
        if assistant is None:
            return
        self.attachments.from_files(mode, assistant.files)

    def download(self, file_id):
        """
        Downloads file

        :param file_id: file id
        :return:
        """
        try:
            data = self.window.gpt.assistant_file_info(file_id)
            if data is None:
                return
            data.filename = os.path.basename(data.filename)
            path = os.path.join(self.window.config.path, 'output', data.filename)
            if os.path.exists(path):
                # append timestamp prefix to filename
                filename = f'{datetime.now().strftime("%Y%m%d%H%M%S")}_{data.filename}'
                path = os.path.join(self.window.config.path, 'output', filename)

            self.window.gpt.assistant_file_download(file_id, path)
            return path
        except Exception as e:
            print(e)
            self.window.ui.dialogs.alert(str(e))

