#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #
import os
from datetime import datetime

from PySide6.QtWidgets import QFileDialog
from pathlib import PurePath
from showinfm import show_in_file_manager

from ..utils import trans


class Attachment:
    def __init__(self, window=None):
        """
        Attachment controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup attachments"""
        # send clear
        if self.window.config.has('attachments_send_clear') and self.window.config.get('attachments_send_clear'):
            self.window.data['attachments.send_clear'].setChecked(True)
        else:
            self.window.data['attachments.send_clear'].setChecked(False)

        #  capture clear
        if self.window.config.has('attachments_capture_clear') and self.window.config.get('attachments_capture_clear'):
            self.window.data['attachments.capture_clear'].setChecked(True)
        else:
            self.window.data['attachments.capture_clear'].setChecked(False)

        self.window.app.attachments.load()
        self.update()

    def update(self):
        """Update attachments list"""
        mode = self.window.config.get('mode')
        items = self.window.app.attachments.get_all(mode)
        self.window.ui.attachments.update_list('attachments', items)
        self.update_tab_label(mode)

    def update_tab_label(self, mode):
        """
        Update tab label

        :param mode: mode
        """
        num_files = self.window.app.attachments.count(mode)
        suffix = ''
        if num_files > 0:
            suffix = f' ({num_files})'
        self.window.tabs['input'].setTabText(1, trans('attachments.tab') + suffix)

    def select(self, mode, idx):
        """
        Select attachment

        :param mode: mode
        :param idx: index
        """
        self.window.app.attachments.current = self.window.app.attachments.get_id_by_idx(mode, idx)

    def selection_change(self):
        """
        Select on list change
        """
        # TODO: implement this
        pass

    def delete(self, idx, force=False):
        """
        Delete attachment

        :param idx: index of attachment
        :param force: force delete
        """
        mode = self.window.config.get('mode')
        if not force:
            self.window.ui.dialogs.confirm('attachments.delete', idx, trans('attachments.delete.confirm'))
            return

        file_id = self.window.app.attachments.get_id_by_idx(mode, idx)
        self.window.app.attachments.delete(mode, file_id)

        # clear current if current == deleted
        if self.window.app.attachments.current == file_id:
            self.window.app.attachments.current = None

        self.update()

    def rename(self, mode, idx):
        """
        Rename attachment

        :param mode: mode
        :param idx: selected attachment index
        """

        # get attachment ID by index
        file_id = self.window.app.attachments.get_id_by_idx(mode, idx)

        # get attachment object by ID
        data = self.window.app.attachments.get_by_id(mode, file_id)
        if data is None:
            return

        # set dialog and show
        self.window.dialog['rename'].id = 'attachment'
        self.window.dialog['rename'].input.setText(data.name)
        self.window.dialog['rename'].current = file_id
        self.window.dialog['rename'].show()
        self.update()

    def update_name(self, file_id, name):
        """
        Update name

        :param file_id: file_id
        :param name: name
        """
        # rename filename in attachments
        mode = self.window.config.get('mode')
        self.window.app.attachments.rename_file(mode, file_id, name)

        # rename filename in assistant data if mode = assistant
        if self.window.config.get('mode') == 'assistant':
            assistant_id = self.window.config.get('assistant')
            if assistant_id is not None:
                self.window.controller.assistant_files.update_file_name(file_id, name)

        # close rename dialog and update attachments list
        self.window.dialog['rename'].close()
        self.update()

    def add(self, mode, attachment):
        """
        Add attachment item to list

        :param mode: mode
        :param attachment: attachment object
        """
        self.window.app.attachments.add(mode, attachment)
        self.update()

    def clear(self, force=False):
        """
        Clear attachments list

        :param force: force clear
        """
        if not force:
            self.window.ui.dialogs.confirm('attachments.clear', -1, trans('attachments.clear.confirm'))
            return

        # delete all from attachments for current mode
        mode = self.window.config.get('mode')
        self.window.app.attachments.delete_all(mode)

        if mode == 'assistant':
            # delete all from assistant data
            assistant_id = self.window.config.get('assistant')
            if assistant_id is not None:
                assistant = self.window.app.assistants.get_by_id(assistant_id)
                if assistant is not None:
                    self.window.controller.assistant_files.clear_attachments(assistant)
        self.update()

    def open_add(self):
        """Open add attachment file dialog"""
        mode = self.window.config.get('mode')
        dialog = QFileDialog(self.window)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        if dialog.exec():
            files = dialog.selectedFiles()
            for path in files:
                # build attachment object
                basename = os.path.basename(path)
                attachment = self.window.app.attachments.new(mode, basename, path, False)
                # append attachment to assistant if current mode = assistant
                if mode == 'assistant':
                    assistant_id = self.window.config.get('assistant')
                    if assistant_id is not None:
                        assistant = self.window.app.assistants.get_by_id(assistant_id)
                        if assistant is not None:
                            self.window.controller.assistant_files.append_attachment(assistant, attachment)

            # save attachments and update attachments list
            self.window.app.attachments.save()
            self.update()

    def open_dir(self, mode, idx):
        """
        Open in directory

        :param mode: mode
        :param idx: index
        """
        # TODO: check dict/obj
        file_id = self.window.app.attachments.get_id_by_idx(mode, idx)
        data = self.window.app.attachments.get_by_id(mode, file_id)
        if data.path is not None and data.path != '' and os.path.exists(data.path):
            path = data.path
            parts = PurePath(path).parts
            path_os = os.path.join(*parts)  # fix for windows \\ path separators
            show_in_file_manager(path_os)

    def import_from_assistant(self, mode, assistant):
        """
        Load attachments from assistant

        :param mode: mode
        :param assistant: assistant object
        """
        if assistant is None:
            return
        # restore attachments from assistant
        self.window.app.attachments.from_attachments(mode, assistant.attachments)

    def has_attachments(self, mode):
        """
        Return True if current mode has attachments

        :param mode: mode to check
        :return: true if has attachments
        :rtype: bool
        """
        return self.window.app.attachments.has(mode)

    def download(self, file_id):
        """
        Download file

        :param file_id: file id to download (id in OpenAI API)
        :return: path to downloaded file
        :rtype: str
        """
        try:
            # get file info from assistant API
            data = self.window.app.gpt.assistant_file_info(file_id)
            if data is None:
                return

            # prepare path to download file
            data.filename = os.path.basename(data.filename)
            path = os.path.join(self.window.config.path, 'output', data.filename)

            # check if file exists, if yes, append timestamp prefix
            if os.path.exists(path):
                # append timestamp prefix to filename
                filename = f'{datetime.now().strftime("%Y%m%d%H%M%S")}_{data.filename}'
                path = os.path.join(self.window.config.path, 'output', filename)

            # download file
            self.window.app.gpt.assistant_file_download(file_id, path)
            return path  # return path to downloaded file
        except Exception as e:
            print(e)
            self.window.ui.dialogs.alert(str(e))

    def toggle_send_clear(self, value):
        """
        Toggle send clear

        :param value: value of the checkbox
        """
        self.window.config.set('attachments_send_clear', value)

    def toggle_capture_clear(self, value):
        """
        Toggle capture clear

        :param value: value of the checkbox
        """
        self.window.config.set('attachments_capture_clear', value)

    def is_capture_clear(self):
        """
        Return True if capture clear is enabled

        :return: true if capture clear is enabled
        :rtype: bool
        """
        if not self.window.config.has('attachments_capture_clear'):
            self.window.config.set('attachments_capture_clear', False)
        return self.window.config.get('attachments_capture_clear')

    def is_send_clear(self):
        """
        Return True if send clear is enabled

        :return: true if send clear is enabled
        :rtype: bool
        """
        if not self.window.config.has('attachments_send_clear'):
            self.window.config.set('attachments_send_clear', False)
        return self.window.config.get('attachments_send_clear')

