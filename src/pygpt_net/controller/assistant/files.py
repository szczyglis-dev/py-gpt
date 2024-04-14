#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.14 21:00:00                  #
# ================================================== #

import os

from pygpt_net.item.assistant import AssistantItem
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Files:
    def __init__(self, window=None):
        """
        Assistants files controller

        :param window: Window instance
        """
        self.window = window

    def update(self):
        """Update assistants files list"""
        self.update_list()

    def select(self, idx: int):
        """
        Select file

        :param idx: index of file
        """
        id = self.window.core.config.get('assistant')
        if id is None or id == "":
            return
        assistant = self.window.core.assistants.get_by_id(id)
        if assistant is None:
            return
        self.window.core.assistants.current_file = \
            self.window.core.assistants.get_file_id_by_idx(assistant, idx)

    def count_upload(self, attachments: dict) -> int:
        """
        Count attachments for upload

        :param attachments: attachments dict
        :return: number of files need to be uploaded
        """
        num = 0
        for id in list(attachments):
            attachment = attachments[id]
            if not attachment.send:
                num += 1  # increment uploaded files counter if file is not uploaded yet
        return num

    def import_files(self, assistant: AssistantItem):
        """
        Import assistant files from API

        :param assistant: assistant
        """
        # run asynchronous
        self.window.ui.status("Importing files...please wait...")
        self.window.core.gpt.assistants.importer.import_files(assistant)

    def handle_imported_files(self, num: int):
        """
        Handle imported files

        :param num: number of imported files
        """
        self.window.ui.status("OK. Imported files: " + str(num) + ".")
        self.update()

    def handle_imported_files_failed(self, error: any):
        """
        Handle error on importing files

        :param error: error message
        """
        self.window.core.debug.log(error)
        print("Error importing files")
        self.window.ui.dialogs.alert(error)
        self.update()

    def download(self, idx: int):
        """
        Download file

        :param idx: selected attachment index
        """
        id = self.window.core.config.get('assistant')
        if id is None or id == "":
            return
        assistant = self.window.core.assistants.get_by_id(id)
        if assistant is None:
            return

        # get attachment ID by index
        file_id = self.window.core.assistants.get_file_id_by_idx(assistant, idx)

        # download file
        self.window.controller.attachment.download(file_id)

    def sync(self, force: bool = False):
        """
        Sync files with API

        :param force: force sync files
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant_import_files',
                id='',
                msg=trans('confirm.assistant.import_files'),
            )
            return

        id = self.window.core.config.get('assistant')
        if id is None or id == "":
            return
        assistant = self.window.core.assistants.get_by_id(id)
        if assistant is None:
            return
        try:
            self.import_files(assistant)
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(e)

    def rename(self, idx: int):
        """
        Rename file

        :param idx: selected attachment index
        """
        id = self.window.core.config.get('assistant')
        if id is None or id == "":
            return
        assistant = self.window.core.assistants.get_by_id(id)
        if assistant is None:
            return

        # get attachment ID by index
        file_id = self.window.core.assistants.get_file_id_by_idx(assistant, idx)

        # get attachment object by ID
        data = self.window.core.assistants.get_file_by_id(assistant, file_id)
        if data is None:
            return

        # set dialog and show
        self.window.ui.dialog['rename'].id = 'attachment_uploaded'
        self.window.ui.dialog['rename'].input.setText(data['name'])
        self.window.ui.dialog['rename'].current = file_id
        self.window.ui.dialog['rename'].show()
        self.update()

    def rename_close(self):
        """Close rename dialog"""
        # close rename dialog and update attachments list
        self.window.ui.dialog['rename'].close()
        self.update()

    def update_name(self, file_id: str, name: str):
        """
        Rename uploaded remote file name

        :param file_id: file_id
        :param name: new name
        """
        id = self.window.core.config.get('assistant')
        if id is None or id == "":
            self.rename_close()
            return
        assistant = self.window.core.assistants.get_by_id(id)
        if assistant is None:
            self.rename_close()
            return
        self.window.core.assistants.rename_file(
            assistant,
            file_id,
            name,
        )
        self.rename_close()

    def clear_files(self, force: bool = False):
        """
        Delete all files

        :param force: force clear files
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='attachments_uploaded.clear',
                id=-1,
                msg=trans('attachments_uploaded.clear.confirm'),
            )
            return

        id = self.window.core.config.get('assistant')
        if id is None or id == "":
            return

        # delete all files
        if self.window.core.assistants.has(id):
            assistant = self.window.core.assistants.get_by_id(id)
            for file_id in list(assistant.files):
                try:
                    self.window.core.gpt.assistants.file_delete(id, file_id)
                    assistant.delete_file(file_id)
                except Exception as e:
                    self.window.ui.dialogs.alert(e)

                # delete file
                if assistant.has_file(file_id):
                    assistant.delete_file(file_id)
                # delete attachment
                if assistant.has_attachment(file_id):
                    assistant.delete_attachment(file_id)

            self.window.core.assistants.save()
            self.update()

    def delete(self, idx: int, force: bool = False):
        """
        Delete file

        :param idx: file idx
        :param force: force delete without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='attachments_uploaded.delete',
                id=idx,
                msg=trans('attachments_uploaded.delete.confirm'),
            )
            return

        # get current assistant
        id = self.window.core.config.get('assistant')
        if id is None or id == "":
            return
        assistant = self.window.core.assistants.get_by_id(id)
        if assistant is None:
            return

        # get attachment ID by index
        file_id = self.window.core.assistants.get_file_id_by_idx(assistant, idx)

        # delete file in API
        try:
            self.window.core.gpt.assistants.file_delete(id, file_id)
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(e)
            return  # do not delete locally if not deleted in API

        # delete locally
        if self.window.core.assistants.has(id):
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
                self.window.core.assistants.save()
                self.update()

    def clear_attachments(self, assistant: AssistantItem):
        """
        Clear attachments

        :param assistant: assistant object
        """
        assistant.clear_attachments()
        self.window.core.assistants.save()
        self.update()

    def upload(self, mode: str, attachments: dict) -> int:
        """
        Upload attachments to assistant

        :param mode: mode
        :param attachments: attachments dict
        :return: number of uploaded files
        """
        # get current chosen assistant
        assistant_id = self.window.core.config.get('assistant')
        if assistant_id is None:
            return 0
        assistant = self.window.core.assistants.get_by_id(assistant_id)

        num = 0
        # loop on attachments
        for id in list(attachments):
            attachment = attachments[id]
            old_id = attachment.id  # tmp id

            # check if not already uploaded (ignore already uploaded files)
            if not attachment.send:
                msg = "Uploading file: {}".format(attachment.path)
                self.window.core.debug.info(msg, False)
                print(msg)
                # check if file exists
                if not os.path.exists(attachment.path):
                    continue

                # upload local attachment file and get new ID (file_id)
                new_id = self.window.core.gpt.assistants.file_upload(
                    assistant_id,
                    attachment.path,
                )
                if new_id is not None:
                    # mark as already uploaded
                    attachment.send = True
                    attachment.id = new_id
                    attachment.remote = new_id

                    # replace old ID with new one
                    self.window.core.attachments.replace_id(
                        mode,
                        old_id,
                        attachment,
                    )

                    # update assistant remote files list
                    assistant.files[new_id] = {
                        'id': new_id,
                        'name': attachment.name,
                        'path': attachment.path,
                        'size': os.path.getsize(attachment.path),
                    }

                    # update assistant attachments list
                    self.window.core.assistants.replace_attachment(
                        assistant,
                        attachment,
                        old_id,
                        new_id,
                    )
                    num += 1  # increment uploaded files counter

        # update assistants list
        self.window.core.assistants.save()

        # update attachments UI
        self.window.controller.attachment.update()

        # update uploaded list
        if num > 0:
            self.update_list()  # update uploaded list UI

        return num

    def append(self, assistant: AssistantItem, attachment: AttachmentItem):
        """
        Append attachment to assistant

        :param assistant: assistant object
        :param attachment: attachment object
        """
        # get current chosen assistant
        assistant.add_attachment(attachment)  # append attachment
        self.window.core.assistants.save()  # save assistants

    def update_list(self):
        """Update uploaded files list"""
        assistant_id = self.window.core.config.get('assistant')
        if assistant_id is None or assistant_id == "":
            return
        assistant = self.window.core.assistants.get_by_id(assistant_id)
        if assistant is None:
            return

        items = assistant.files
        self.window.ui.chat.input.attachments_uploaded.update(items)
        self.update_tab()

    def update_tab(self):
        """Update tab label (attachments uploaded)"""
        assistant_id = self.window.core.config.get('assistant')
        if assistant_id is None or assistant_id == "":
            self.window.ui.tabs['input'].setTabText(2, trans('attachments_uploaded.tab'))
            return

        assistant = self.window.core.assistants.get_by_id(assistant_id)
        if assistant is None:
            return  # no assistant

        items = assistant.files
        num_files = len(items)
        suffix = ''

        # append num of files
        if num_files > 0:
            suffix = f' ({num_files})'
        self.window.ui.tabs['input'].setTabText(2, trans('attachments_uploaded.tab') + suffix)

    def handle_received_ids(self, ids: list, ext: str = None) -> list:
        """
        Handle (download) received message files

        :param ids: list of file IDs
        :param ext: file extension to add (optional)
        :return: downloaded files paths
        """
        num_downloaded = 0
        paths = []
        for file_id in ids:
            self.log("Downloading file: {}".format(file_id))
            path = self.window.controller.attachment.download(file_id, ext=ext)
            if path is not None:
                paths.append(path)
                num_downloaded += 1

        if num_downloaded > 0:
            pass
            # show alert with downloaded files
            # msg = "Downloaded {} file(s): {}".format(num_downloaded, ", ".join(paths))
            # self.window.ui.dialogs.alert(msg)

        return paths

    def is_log(self) -> bool:
        """
        Check if logging is enabled

        :return: bool
        """
        if self.window.core.config.has('log.assistants') \
                and self.window.core.config.get('log.assistants'):
            return True
        return False

    def log(self, msg: str):
        """
        Log message

        :param msg: message
        """
        if self.is_log():
            self.window.core.debug.info(msg, True)
