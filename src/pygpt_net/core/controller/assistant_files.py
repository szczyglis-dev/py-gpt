#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.18 01:00:00                  #
# ================================================== #
import os

from ..utils import trans


class AssistantFiles:
    def __init__(self, window=None):
        """
        Assistants controller

        :param window: Window instance
        """
        self.window = window

    def update(self):
        """
        Update assistants files list
        """
        self.update_uploaded()

    def select_file(self, idx):
        """
        Select file

        :param idx: index of file
        """
        id = self.window.config.get('assistant')
        if id is None or id == "":
            return
        assistant = self.window.app.assistants.get_by_id(id)
        if assistant is None:
            return
        self.window.app.assistants.current_file = \
            self.window.app.assistants.get_file_id_by_idx(assistant, idx)

    def count_upload_attachments(self, attachments):
        """
        Count attachments for upload

        :param attachments: attachments list
        :return: number of files need to be uploaded
        :rtype: int
        """
        num = 0
        for id in list(attachments):
            attachment = attachments[id]
            if not attachment.send:
                num += 1  # increment uploaded files counter if file is not uploaded yet
        return num

    def import_files(self, assistant):
        """
        Import assistant files

        :param assistant: assistant
        """
        try:
            files = self.window.app.gpt_assistants.file_list(assistant.id)
            self.window.app.assistants.import_files(assistant, files)
            self.window.app.assistants.save()
            self.update()
            self.window.set_status("Imported files: " + str(len(files)))
        except Exception as e:
            print("Error importing assistant files")
            print(e)
            self.window.ui.dialogs.alert(str(e))

    def download_file(self, idx):
        """
        Download file

        :param idx: selected attachment index
        """
        id = self.window.config.get('assistant')
        if id is None or id == "":
            return
        assistant = self.window.app.assistants.get_by_id(id)
        if assistant is None:
            return

        # get attachment ID by index
        file_id = self.window.app.assistants.get_file_id_by_idx(assistant, idx)

        # download file
        self.window.controller.attachment.download(file_id)

    def sync_files(self, force=False):
        """
        Sync files with API

        :param force: force sync files
        """
        if not force:
            self.window.ui.dialogs.confirm('assistant_import_files', '',
                                           trans('confirm.assistant.import_files'))
            return

        id = self.window.config.get('assistant')
        if id is None or id == "":
            return
        assistant = self.window.app.assistants.get_by_id(id)
        if assistant is None:
            return
        try:
            self.import_files(assistant)
        except Exception as e:
            print(e)
            self.window.ui.dialogs.alert(str(e))

    def rename_file(self, idx):
        """
        Rename file

        :param idx: selected attachment index
        """
        id = self.window.config.get('assistant')
        if id is None or id == "":
            return
        assistant = self.window.app.assistants.get_by_id(id)
        if assistant is None:
            return

        # get attachment ID by index
        file_id = self.window.app.assistants.get_file_id_by_idx(assistant, idx)

        # get attachment object by ID
        data = self.window.app.assistants.get_file_by_id(assistant, file_id)
        if data is None:
            return

        # set dialog and show
        self.window.ui.dialog['rename'].id = 'attachment_uploaded'
        self.window.ui.dialog['rename'].input.setText(data['name'])
        self.window.ui.dialog['rename'].current = file_id
        self.window.ui.dialog['rename'].show()
        self.update()

    def update_file_name(self, file_id, name):
        """
        Rename uploaded remote file name

        :param file_id: file_id
        :param name: new name
        """
        id = self.window.config.get('assistant')
        if id is None or id == "":
            self.close_rename_file()
            return
        assistant = self.window.app.assistants.get_by_id(id)
        if assistant is None:
            self.close_rename_file()
            return
        self.window.app.assistants.rename_file(assistant, file_id, name)
        self.close_rename_file()

    def close_rename_file(self):
        """
        Close rename dialog
        """
        # close rename dialog and update attachments list
        self.window.ui.dialog['rename'].close()
        self.update()

    def clear_files(self, force=False):
        """
        Delete all files

        :param force: force clear files
        """
        if not force:
            self.window.ui.dialogs.confirm('attachments_uploaded.clear', -1,
                                           trans('attachments_uploaded.clear.confirm'))
            return

        id = self.window.config.get('assistant')
        if id is None or id == "":
            return

        # delete all files
        if self.window.app.assistants.has(id):
            assistant = self.window.app.assistants.get_by_id(id)
            for file_id in list(assistant.files):
                try:
                    self.window.app.gpt_assistants.file_delete(id, file_id)
                    assistant.delete_file(file_id)
                except Exception as e:
                    self.window.ui.dialogs.alert(str(e))

                # delete file
                if assistant.has_file(file_id):
                    assistant.delete_file(file_id)
                # delete attachment
                if assistant.has_attachment(file_id):
                    assistant.delete_attachment(file_id)

            self.window.app.assistants.save()
            self.update()

    def delete_file(self, idx, force=False):
        """
        Delete file

        :param idx: file idx
        :param force: force delete without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm('attachments_uploaded.delete', idx,
                                           trans('attachments_uploaded.delete.confirm'))
            return

        # get current assistant
        id = self.window.config.get('assistant')
        if id is None or id == "":
            return
        assistant = self.window.app.assistants.get_by_id(id)
        if assistant is None:
            return

        # get attachment ID by index
        file_id = self.window.app.assistants.get_file_id_by_idx(assistant, idx)

        # delete file in API
        try:
            self.window.app.gpt_assistants.file_delete(id, file_id)
        except Exception as e:
            self.window.ui.dialogs.alert(str(e))
            return  # do not delete locally if not deleted in API

        # delete locally
        if self.window.app.assistants.has(id):
            need_save = False
            # delete file
            if assistant.has_file(file_id):
                assistant.delete_file(file_id)
                need_save = True
            # delete attachment
            if assistant.has_attachment(file_id):
                assistant.delete_attachment(file_id)
                need_save = True
            # save assistants and update assistants list
            if need_save:
                self.window.app.assistants.save()
                self.update()

    def clear_attachments(self, assistant):
        """
        Clear attachments

        :param assistant: assistant object
        """
        assistant.clear_attachments()
        self.window.app.assistants.save()
        self.update()

    def upload_attachments(self, mode, attachments):
        """
        Upload attachments to assistant

        :param mode: mode
        :param attachments: attachments list
        :return: number of uploaded files
        :rtype: int
        """
        # get current chosen assistant
        assistant_id = self.window.config.get('assistant')
        if assistant_id is None:
            return 0
        assistant = self.window.app.assistants.get_by_id(assistant_id)

        num = 0
        # loop on attachments
        for id in list(attachments):
            attachment = attachments[id]
            old_id = attachment.id  # tmp id

            # check if not already uploaded (ignore already uploaded files)
            if not attachment.send:
                print("Uploading file: {}".format(attachment.path))
                # check if file exists
                if not os.path.exists(attachment.path):
                    continue

                # upload local attachment file and get new ID (file_id)
                new_id = self.window.app.gpt_assistants.file_upload(assistant_id, attachment.path)
                if new_id is not None:
                    # mark as already uploaded
                    attachment.send = True
                    attachment.id = new_id
                    attachment.remote = new_id

                    # replace old ID with new one
                    self.window.app.attachments.replace_id(mode, old_id, attachment)

                    # update assistant remote files list
                    assistant.files[new_id] = {
                        'id': new_id,
                        'name': attachment.name,
                        'path': attachment.path,
                    }

                    # update assistant attachments list
                    self.window.app.assistants.replace_attachment(assistant, attachment, old_id, new_id)
                    num += 1  # increment uploaded files counter

        # update assistants list
        self.window.app.assistants.save()

        # update attachments UI
        self.window.controller.attachment.update()

        # update uploaded list
        if num > 0:
            self.update_uploaded()  # update uploaded list UI

        return num

    def append_attachment(self, assistant, attachment):
        """
        Append attachment to assistant

        :param attachment: attachment
        :param assistant: assistant object
        """
        # get current chosen assistant
        assistant.add_attachment(attachment)  # append attachment
        self.window.app.assistants.save()  # save assistants

    def update_uploaded(self):
        """Update uploaded files list"""
        assistant_id = self.window.config.get('assistant')
        if assistant_id is None or assistant_id == "":
            return
        assistant = self.window.app.assistants.get_by_id(assistant_id)
        items = assistant.files
        self.window.ui.attachments_uploaded.update_list('attachments_uploaded', items)
        self.update_tab_label()

    def update_tab_label(self):
        """
        Update tab label (attachments uploaded)
        """
        assistant_id = self.window.config.get('assistant')
        if assistant_id is None or assistant_id == "":
            self.window.ui.tabs['input'].setTabText(2, trans('attachments_uploaded.tab'))
            return

        assistant = self.window.app.assistants.get_by_id(assistant_id)
        items = assistant.files
        num_files = len(items)
        suffix = ''

        # append num of files
        if num_files > 0:
            suffix = f' ({num_files})'
        self.window.ui.tabs['input'].setTabText(2, trans('attachments_uploaded.tab') + suffix)

    def handle_message_files(self, msg):
        """
        Handle (download) message files

        :param msg: message
        """
        num_downloaded = 0
        paths = []
        for file_id in msg.file_ids:
            path = self.window.controller.attachment.download(file_id)
            if path is not None:
                paths.append(path)
                num_downloaded += 1
        if num_downloaded > 0:
            # show alert with downloaded files
            msg = "Downloaded {} file(s): {}".format(num_downloaded, ", ".join(paths))
            self.window.ui.dialogs.alert(msg)
