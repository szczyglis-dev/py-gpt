#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

import os
from typing import Optional, Dict, List

from PySide6.QtWidgets import QApplication

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

        # get file by list index
        thread_id = self.window.core.config.get('assistant_thread')
        file_id = self.window.core.assistants.files.get_file_id_by_idx(idx, assistant.vector_store, thread_id)
        self.window.core.assistants.current_file = file_id

    def count_upload(
            self,
            attachments: Dict[str, AttachmentItem]
    ) -> int:
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

    def import_files(self, store_id: Optional[str] = None):
        """
        Import assistant files from API

        :param store_id: store ID
        """
        # run asynchronous
        self.window.update_status("Importing files...please wait...")
        self.window.core.gpt.assistants.importer.import_files(store_id)

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

        # get file by list index
        thread_id = self.window.core.config.get('assistant_thread')
        file_id = self.window.core.assistants.files.get_file_id_by_idx(idx, assistant.vector_store, thread_id)

        # download file
        self.window.controller.attachment.download(file_id)

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

        thread_id = self.window.core.config.get('assistant_thread')

        # get file by list index
        file = self.window.core.assistants.files.get_file_by_idx(idx, assistant.vector_store, thread_id)
        if file is None:
            return

        # set dialog and show
        self.window.ui.dialog['rename'].id = 'attachment_uploaded'
        self.window.ui.dialog['rename'].input.setText(file.name)
        self.window.ui.dialog['rename'].current = file.record_id
        self.window.ui.dialog['rename'].show()
        self.update()

    def rename_close(self):
        """Close rename dialog"""
        # close rename dialog and update attachments list
        self.window.ui.dialog['rename'].close()
        self.update()

    def update_name(self, record_id: str, name: str):
        """
        Rename uploaded remote file name

        :param record_id: file record ID
        :param name: new name
        """
        self.window.core.assistants.files.rename(
            record_id,
            name,
        )
        self.rename_close()

    def clear(self, force: bool = False):
        """
        Delete all files

        :param force: force clear files
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='attachments.uploaded.clear',
                id=-1,
                msg=trans('attachments_uploaded.clear.confirm'),
            )
            return

        id = self.window.core.config.get('assistant')
        if id is None or id == "":
            return

        # delete all files in current thread
        if self.window.core.assistants.has(id):
            assistant = self.window.core.assistants.get_by_id(id)
            thread_id = self.window.core.config.get('assistant_thread')
            items = self.window.core.assistants.files.get_by_store_or_thread(assistant.vector_store, thread_id)
            self.window.update_status(trans('status.sending'))
            QApplication.processEvents()

            for id in list(items.keys()):
                file = items[id]
                try:
                    self.window.core.assistants.files.delete(file)  # delete from DB, API and vector stores
                except Exception as e:
                    self.window.update_status(trans('status.error'))
                    self.window.ui.dialogs.alert(e)

            # update store status
            if assistant.vector_store:
                self.window.controller.assistant.store.refresh_by_store_id(assistant.vector_store)

            self.window.update_status(trans('status.deleted'))

        self.update()

    def delete(self, idx: int, force: bool = False):
        """
        Delete file

        :param idx: file idx
        :param force: force delete without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='attachments.uploaded.delete',
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

        # get file by list index
        thread_id = self.window.core.config.get('assistant_thread')
        file = self.window.core.assistants.files.get_file_by_idx(idx, assistant.vector_store, thread_id)
        if file is None:
            return

        # delete file in API
        self.window.update_status(trans('status.sending'))
        QApplication.processEvents()
        try:
            self.window.core.assistants.files.delete(file)  # delete from DB, API and vector stores

            # update store status
            if assistant.vector_store:
                self.window.controller.assistant.store.refresh_by_store_id(assistant.vector_store)

            self.window.update_status(trans('status.deleted'))
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(e)
            self.window.update_status(trans('status.error'))

        self.update()

    def clear_attachments(self, assistant: AssistantItem):
        """
        Clear attachments

        :param assistant: assistant object
        """
        assistant.clear_attachments()
        self.window.core.assistants.save()
        self.update()

    def upload(
            self,
            mode: str,
            attachments: Dict[str, AttachmentItem]
    ) -> int:
        """
        Upload attachments to assistant

        :param mode: work mode
        :param attachments: attachments dict
        :return: number of uploaded files
        """
        # get current chosen assistant
        assistant_id = self.window.core.config.get('assistant')
        thread_id = self.window.core.config.get('assistant_thread')
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
                # check if file exists
                if not os.path.exists(attachment.path):
                    continue

                # upload local attachment file and get new ID (file_id)
                new_id = self.window.core.gpt.store.upload(
                    attachment.path,
                )
                if new_id is not None:
                    # mark as already uploaded
                    attachment.send = True
                    attachment.id = new_id
                    attachment.remote = new_id

                    """
                    if assistant.vector_store is None or assistant.vector_store == "":
                        assistant.vector_store = self.window.core.gpt.store.create_store(
                            "thread-" + thread_id,
                        )
                    """

                    # add to vector store if defined in assistant, otherwise file will be added to thread store
                    if assistant.vector_store:
                        self.window.core.gpt.store.add_file(
                            assistant.vector_store,
                            new_id,
                        )

                    # replace old ID with new one
                    self.window.core.attachments.replace_id(
                        mode,
                        old_id,
                        attachment,
                    )

                    self.window.core.assistants.files.create(
                        assistant,
                        thread_id,
                        new_id,
                        attachment.name,
                        attachment.path,
                        os.path.getsize(attachment.path),
                    )

                    # update assistant attachments list
                    self.window.core.assistants.replace_attachment(
                        assistant,
                        attachment,
                        old_id,
                        new_id,
                    )
                    attachment.consumed = True
                    num += 1  # increment uploaded files counter

        # update assistants list
        self.window.core.assistants.save()

        # update attachments UI
        self.window.controller.attachment.update()

        # update uploaded list
        if num > 0:
            # update store status
            if assistant.vector_store:
                self.window.controller.assistant.store.refresh_by_store_id(assistant.vector_store)

            self.update_list()  # update uploaded list UI

        return num

    def append(
            self,
            assistant: AssistantItem,
            attachment: AttachmentItem
    ):
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
        thread_id = self.window.core.config.get('assistant_thread')
        if assistant_id is None or assistant_id == "":
            return
        assistant = self.window.core.assistants.get_by_id(assistant_id)
        if assistant is None:
            return
        items = self.window.core.assistants.files.get_by_store_or_thread(assistant.vector_store, thread_id)
        self.window.ui.chat.input.attachments_uploaded.update(items)
        self.update_tab()

    def update_tab(self):
        """Update tab label (attachments uploaded)"""
        assistant_id = self.window.core.config.get('assistant')
        thread_id = self.window.core.config.get('assistant_thread')
        if assistant_id is None or assistant_id == "":
            self.window.ui.tabs['input'].setTabText(2, trans('attachments_uploaded.tab'))
            return
        assistant = self.window.core.assistants.get_by_id(assistant_id)
        if assistant is None:
            return  # no assistant
        num_files = self.window.core.assistants.files.count_by_store_or_thread(assistant.vector_store, thread_id)
        suffix = ''
        # append num of files
        if num_files > 0:
            suffix = f' ({num_files})'
        self.window.ui.tabs['input'].setTabText(2, trans('attachments_uploaded.tab') + suffix)

    def handle_received_ids(
            self,
            ids: List[str],
            ext: Optional[str] = None
    ) -> list:
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
