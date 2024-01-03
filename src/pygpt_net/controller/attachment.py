#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

import os
from datetime import datetime

from PySide6.QtWidgets import QFileDialog

from pygpt_net.item.assistant import AssistantItem
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.utils import trans


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
        if self.window.core.config.has('attachments_send_clear') \
                and self.window.core.config.get('attachments_send_clear'):
            self.window.ui.nodes['attachments.send_clear'].setChecked(True)
        else:
            self.window.ui.nodes['attachments.send_clear'].setChecked(False)

        #  capture clear
        if self.window.core.config.has('attachments_capture_clear') \
                and self.window.core.config.get('attachments_capture_clear'):
            self.window.ui.nodes['attachments.capture_clear'].setChecked(True)
        else:
            self.window.ui.nodes['attachments.capture_clear'].setChecked(False)

        self.window.core.attachments.load()
        self.update()

    def update(self):
        """Update attachments list"""
        mode = self.window.core.config.get('mode')
        items = self.window.core.attachments.get_all(mode)
        self.window.ui.chat.input.attachments.update(items)
        self.update_tab(mode)

        if not self.has(mode):
            self.window.controller.chat.vision.unavailable()
        else:
            if mode == 'vision' or self.window.controller.plugins.is_type_enabled('vision'):
                self.window.controller.chat.vision.available()

    def update_tab(self, mode: str):
        """
        Update tab label

        :param mode: mode
        """
        num_files = self.window.core.attachments.count(mode)
        suffix = ''
        if num_files > 0:
            suffix = f' ({num_files})'
        self.window.ui.tabs['input'].setTabText(1, trans('attachments.tab') + suffix)

    def select(self, mode: str, idx: int):
        """
        Select attachment

        :param mode: mode
        :param idx: index
        """
        self.window.core.attachments.current = self.window.core.attachments.get_id_by_idx(mode, idx)

    def selection_change(self):
        """
        Select on list change
        """
        # TODO: implement this
        pass

    def delete(self, idx: int, force: bool = False):
        """
        Delete attachment

        :param idx: index of attachment
        :param force: force delete
        """
        mode = self.window.core.config.get('mode')
        if not force:
            self.window.ui.dialogs.confirm('attachments.delete', idx, trans('attachments.delete.confirm'))
            return

        file_id = self.window.core.attachments.get_id_by_idx(mode, idx)
        self.window.core.attachments.delete(mode, file_id)

        # clear current if current == deleted
        if self.window.core.attachments.current == file_id:
            self.window.core.attachments.current = None

        if not self.has(mode):
            self.window.controller.chat.vision.unavailable()

        self.update()

    def rename(self, mode: str, idx: int):
        """
        Rename attachment

        :param mode: mode
        :param idx: selected attachment index
        """

        # get attachment ID by index
        file_id = self.window.core.attachments.get_id_by_idx(mode, idx)

        # get attachment object by ID
        data = self.window.core.attachments.get_by_id(mode, file_id)
        if data is None:
            return

        # set dialog and show
        self.window.ui.dialog['rename'].id = 'attachment'
        self.window.ui.dialog['rename'].input.setText(data.name)
        self.window.ui.dialog['rename'].current = file_id
        self.window.ui.dialog['rename'].show()
        self.update()

    def update_name(self, file_id: str, name: str):
        """
        Update name

        :param file_id: file_id
        :param name: name
        """
        # rename filename in attachments
        mode = self.window.core.config.get('mode')
        self.window.core.attachments.rename_file(mode, file_id, name)

        # rename filename in assistant data if mode = assistant
        if self.window.core.config.get('mode') == 'assistant':
            assistant_id = self.window.core.config.get('assistant')
            if assistant_id is not None:
                self.window.controller.assistant.files.update_name(file_id, name)

        # close rename dialog and update attachments list
        self.window.ui.dialog['rename'].close()
        self.update()

    def add(self, mode: str, attachment: AttachmentItem):
        """
        Add attachment item to list

        :param mode: mode
        :param attachment: attachment object
        """
        self.window.core.attachments.add(mode, attachment)
        self.update()

    def clear(self, force: bool = False):
        """
        Clear attachments list

        :param force: force clear
        """
        if not force:
            self.window.ui.dialogs.confirm('attachments.clear', -1, trans('attachments.clear.confirm'))
            return

        # delete all from attachments for current mode
        mode = self.window.core.config.get('mode')
        self.window.core.attachments.delete_all(mode)

        self.window.controller.chat.vision.unavailable()  # set no content to provide

        if mode == 'assistant':
            # delete all from assistant data
            assistant_id = self.window.core.config.get('assistant')
            if assistant_id is not None:
                assistant = self.window.core.assistants.get_by_id(assistant_id)
                if assistant is not None:
                    self.window.controller.assistant.files.clear_attachments(assistant)
        self.update()

    def open_add(self):
        """Open add attachment file dialog"""
        mode = self.window.core.config.get('mode')
        dialog = QFileDialog(self.window)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        if dialog.exec():
            files = dialog.selectedFiles()
            for path in files:
                # build attachment object
                basename = os.path.basename(path)
                attachment = self.window.core.attachments.new(mode, basename, path, False)
                # append attachment to assistant if current mode = assistant
                if mode == 'assistant':
                    assistant_id = self.window.core.config.get('assistant')
                    if assistant_id is not None:
                        assistant = self.window.core.assistants.get_by_id(assistant_id)
                        if assistant is not None:
                            self.window.controller.assistant.files.append(assistant, attachment)

            # save attachments and update attachments list
            self.window.core.attachments.save()
            self.update()

    def open_dir(self, mode: str, idx: int):
        """
        Open in directory

        :param mode: mode
        :param idx: index
        """
        # TODO: check dict/obj
        file_id = self.window.core.attachments.get_id_by_idx(mode, idx)
        data = self.window.core.attachments.get_by_id(mode, file_id)
        if data.path is not None and data.path != '' and os.path.exists(data.path):
            self.window.controller.files.open_in_file_manager(data.path)

    def import_from_assistant(self, mode: str, assistant: AssistantItem):
        """
        Load attachments from assistant

        :param mode: mode
        :param assistant: assistant object
        """
        if assistant is None:
            return
        # restore attachments from assistant
        self.window.core.attachments.from_attachments(mode, assistant.attachments)

    def has(self, mode: str) -> bool:
        """
        Return True if current mode has attachments

        :param mode: mode to check
        :return: True if has attachments
        """
        return self.window.core.attachments.has(mode)

    def download(self, file_id: str) -> str or None:
        """
        Download file

        :param file_id: file id to download (id in OpenAI API)
        :return: path to downloaded file
        """
        try:
            # get file info from assistant API
            data = self.window.core.gpt.assistants.file_info(file_id)
            if data is None:
                return

            # prepare path to download file
            data.filename = os.path.basename(data.filename)
            path = os.path.join(self.window.core.config.path, 'output', data.filename)

            # check if file exists, if yes, append timestamp prefix
            if os.path.exists(path):
                # append timestamp prefix to filename
                filename = f'{datetime.now().strftime("%Y%m%d%H%M%S")}_{data.filename}'
                path = os.path.join(self.window.core.config.path, 'output', filename)

            # download file
            self.window.core.gpt.assistants.file_download(file_id, path)
            return path  # return path to downloaded file
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(str(e))

    def toggle_send_clear(self, value: bool):
        """
        Toggle send clear

        :param value: value of the checkbox
        """
        self.window.core.config.set('attachments_send_clear', value)

    def toggle_capture_clear(self, value: bool):
        """
        Toggle capture clear

        :param value: value of the checkbox
        """
        self.window.core.config.set('attachments_capture_clear', value)

    def is_capture_clear(self) -> bool:
        """
        Return True if capture clear is enabled

        :return: True if capture clear is enabled
        """
        if not self.window.core.config.has('attachments_capture_clear'):
            self.window.core.config.set('attachments_capture_clear', False)
        return self.window.core.config.get('attachments_capture_clear')

    def is_send_clear(self) -> bool:
        """
        Return True if send clear is enabled

        :return: True if send clear is enabled
        """
        if not self.window.core.config.has('attachments_send_clear'):
            self.window.core.config.set('attachments_send_clear', False)
        return self.window.core.config.get('attachments_send_clear')
