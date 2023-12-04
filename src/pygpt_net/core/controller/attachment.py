#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.03 16:00:00                  #
# ================================================== #
import os

from PySide6.QtWidgets import QFileDialog
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

    def open_add(self):
        dialog = QFileDialog(self.window)
        dialog.setFileMode(QFileDialog.ExistingFiles)
        if dialog.exec():
            files = dialog.selectedFiles()
            for path in files:
                basename = os.path.basename(path)
                self.attachments.new(basename, path, False)
            self.attachments.save()
            self.update()

    def clear(self, force=False):
        """
        Clears attachments list

        :param force: force clear
        """
        if not force:
            self.window.ui.dialogs.confirm('attachments.clear', -1, trans('attachments.clear.confirm'))
            return

        self.attachments.delete_all()
        self.update()

    def setup(self):
        """Setup attachments"""
        # send clear
        if 'attachments_send_clear' in self.window.config.data and self.window.config.data['attachments_send_clear']:
            self.window.data['attachments.send_clear'].setChecked(True)
        else:
            self.window.data['attachments.send_clear'].setChecked(False)

        self.attachments.load_list()
        self.update()

    def update(self):
        """Update attachments list"""
        items = self.attachments.get_list()
        self.window.ui.attachments.update_list('attachments', items)
        self.update_tab_label()

    def update_tab_label(self):
        """Updates tab label"""
        num_files = self.attachments.count()
        suffix = ''
        if num_files > 0:
            suffix = f' ({num_files})'
        self.window.data['input.tabs'].setTabText(1, trans('attachments.tab') + suffix)

    def selection_change(self):
        """
        Selects on list change
        """
        # TODO: implement this
        pass

    def select(self, idx):
        """
        Selects attachment

        :param idx: index
        """
        self.attachments.current = self.attachments.get_uuid_by_idx(idx)

    def delete(self, idx, force=False):
        """
        Deletes attachment

        :param idx: index
        :param force: force delete
        """
        if not force:
            self.window.ui.dialogs.confirm('attachments.delete', idx, trans('attachments.delete.confirm'))
            return

        uuid = self.attachments.get_uuid_by_idx(idx)
        self.attachments.delete(uuid)
        if self.attachments.current == uuid:
            self.attachments.current = None
        self.update()

    def rename(self, idx):
        """
        Renames attachment

        :param idx: selected attachment index
        """
        uuid = self.attachments.get_uuid_by_idx(idx)
        data = self.attachments.get_by_uuid(uuid)
        self.window.dialog['rename'].id = 'attachment'
        self.window.dialog['rename'].input.setText(data.name)
        self.window.dialog['rename'].current = uuid
        self.window.dialog['rename'].show()
        self.update()

    def update_name(self, uuid, name):
        """
        Updates name

        :param uuid: uuid
        :param name: name
        """
        data = self.attachments.get_by_uuid(uuid)
        data.name = name

        # rename filename in assistant data
        if self.window.config.data['mode'] == 'assistant' and self.window.config.data['assistant'] is not None:
            self.attachments.rename_in_assistant(self.window.config.data['assistant'], uuid, name)

        self.attachments.save()
        self.window.dialog['rename'].close()
        self.update()

    def add(self, item):
        """
        Adds attachment item

        :param item: item
        """
        self.attachments.add(item)
        self.update()

    def open_dir(self, idx):
        """
        Opens in directory

        :param idx: index
        """
        uuid = self.attachments.get_uuid_by_idx(idx)
        data = self.attachments.get_by_uuid(uuid)
        if data.path is not None and data.path != '' and os.path.exists(data.path):
            show_in_file_manager(data.path)

    def toggle_send_clear(self, value):
        """
        Toggles send clear

        :param value: value of the checkbox
        """
        self.window.config.data['attachments_send_clear'] = value

    def upload_to_assistant(self):
        """
        Uploads attachments to assistant
        """
        # get current chosen assistant
        assistant_id = self.window.config.data['assistant']
        if assistant_id is None:
            return
        assistant = self.window.config.get_assistant_by_id(assistant_id)

        # get attachments
        attachments = self.attachments.get_list()
        for uuid in attachments:
            attachment = attachments[uuid]
            tmp_id = attachment.uuid  # tmp id
            # check if not already uploaded
            if not attachment.send:
                # upload file and get new ID
                file_id = self.window.gpt.assistant_file_upload(assistant_id, attachment.path)
                if file_id is not None:
                    # mark as uploaded
                    attachment.send = True
                    attachment.uuid = file_id
                    attachment.remote = file_id

                    # replace old ID with new one
                    self.attachments.replace_id(tmp_id, attachment)

                    # update assistant files list
                    assistant['files'][file_id] = {
                        'name': attachment.name,
                        'id': file_id,
                        'path': attachment.path
                    }
        # update assistant
        self.window.config.save_assistants()
        self.update()  # update UI
