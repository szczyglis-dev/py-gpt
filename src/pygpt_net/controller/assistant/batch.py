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

from typing import Optional, Any

from PySide6.QtWidgets import QApplication, QFileDialog

from pygpt_net.utils import trans


class Batch:
    def __init__(self, window=None):
        """
        Assistants batch controller

        :param window: Window instance
        """
        self.window = window
        self.files_to_upload = []

    def import_assistants(self, force: bool = False):
        """
        Import all remote assistants from API

        :param force: if true, imports without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.import',
                id='',
                msg=trans('confirm.assistant.import'),
            )
            return

        # run asynchronous
        self.window.update_status("Importing assistants...please wait...")
        self.window.core.gpt.assistants.importer.import_assistants()

    def import_stores(self, force: bool = False):
        """
        Import vector stores from API

        :param force: if true, imports without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.store.import',
                id='',
                msg=trans('confirm.assistant.store.import'),
            )
            return
        # run asynchronous
        self.window.update_status("Importing vector stores...please wait...")
        self.window.core.assistants.store.truncate()  # clear all stores
        self.window.core.gpt.assistants.importer.import_vector_stores()
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()

    def import_files_current(self):
        """Import files from API"""
        id = self.window.core.config.get('assistant')
        if id is None or id == "":
            return
        if self.window.core.assistants.has(id):
            assistant = self.window.core.assistants.get_by_id(id)
            store_id = assistant.vector_store
            if store_id is None or store_id == "":
                self.window.ui.dialogs.alert(trans("dialog.assistant.store.alert.assign"))
                return
            self.import_store_files(store_id)

    def import_files(self, force: bool = False):
        """
        Sync files with API (all)

        :param force: force sync files
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.files.import.all',
                id='',
                msg=trans('confirm.assistant.import_files'),
            )
            return
        try:
            self.window.controller.assistant.files.import_files()  # all
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(e)

    def import_store_files(
            self,
            store_id: str,
            force: bool = False
    ):
        """
        Sync files with API (store)

        :param store_id: vector store ID
        :param force: force sync files
        """
        if store_id is None:
            self.window.ui.dialogs.alert(trans("dialog.assistant.store.alert.select"))
            return

        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.files.import.store',
                id=store_id,
                msg=trans('confirm.assistant.import_files.store'),
            )
            return
        try:
            self.window.controller.assistant.files.import_files(store_id)  # by store
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(e)

    def truncate_files(self, force: bool = False):
        """
        Truncate all files in API

        :param force: if True, imports without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.files.truncate',
                id='',
                msg=trans('confirm.assistant.files.truncate'),
            )
            return
        # run asynchronous
        self.window.update_status("Removing files...please wait...")
        QApplication.processEvents()
        self.window.core.gpt.assistants.importer.truncate_files()  # remove all files from API

    def truncate_store_files_by_idx(self, idx: int, force: bool = False):
        """
        Truncate all files in API (store)

        :param idx: store index
        :param force: if True, imports without confirmation
        """
        store_id = self.window.controller.assistant.store.get_by_tab_idx(idx)
        self.truncate_store_files(store_id, force)

    def truncate_store_files(self, store_id: str, force: bool = False):
        """
        Truncate all files in API (store)

        :param store_id: store ID
        :param force: if True, imports without confirmation
        """
        if store_id is None:
            self.window.ui.dialogs.alert(trans("dialog.assistant.store.alert.select"))
            return

        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.files.truncate.store',
                id=store_id,
                msg=trans('confirm.assistant.files.truncate.store'),
            )
            return
        # run asynchronous
        self.window.update_status("Removing files...please wait...")
        QApplication.processEvents()
        self.window.core.gpt.assistants.importer.truncate_files(store_id)  # remove all files from API

    def clear_store_files_by_idx(
            self,
            idx: int,
            force: bool = False
    ):
        """
        Clear files (store, local only)

        :param idx: store index
        :param force: if True, clears without confirmation
        """
        store_id = self.window.controller.assistant.store.get_by_tab_idx(idx)
        self.clear_store_files(store_id, force)

    def clear_store_files(
            self,
            store_id: Optional[str] = None,
            force: bool = False
    ):
        """
        Clear files (store, local only)

        :param store_id: store ID
        :param force: if True, clears without confirmation
        """
        if store_id is None:
            self.window.ui.dialogs.alert(trans("dialog.assistant.store.alert.select"))
            return

        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.files.clear.store',
                id=store_id,
                msg=trans('confirm.assistant.files.clear'),
            )
            return
        self.window.update_status("Clearing store files...please wait...")
        QApplication.processEvents()
        self.window.core.assistants.files.truncate_local(store_id)  # clear files local
        self.window.controller.assistant.files.update()
        self.window.update_status("OK. All store files cleared.")
        self.window.ui.dialogs.alert(trans("status.finished"))

    def clear_files(self, force: bool = False):
        """
        Clear files (all, local only)

        :param force: if True, clears without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.files.clear.all',
                id='',
                msg=trans('confirm.assistant.files.clear'),
            )
            return
        self.window.update_status("Clearing files...please wait...")
        QApplication.processEvents()
        self.window.core.assistants.files.truncate_local()  # clear files local
        self.window.controller.assistant.files.update()
        self.window.update_status("OK. All files cleared.")
        self.window.ui.dialogs.alert(trans("status.finished"))

    def clear_stores(self, force: bool = False):
        """
        Clear vector stores (local only)

        :param force: if True, clears without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.store.clear',
                id='',
                msg=trans('confirm.assistant.store.clear'),
            )
            return
        self.window.update_status("Clearing vector stores...please wait...")
        QApplication.processEvents()
        self.window.core.assistants.store.truncate()  # clear all stores
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()
        self.window.update_status("OK. All stores cleared.")
        self.window.controller.assistant.store.current = None
        self.window.controller.assistant.store.init()

    def truncate_stores(self, force: bool = False):
        """
        Truncate vector stores in API

        :param force: if True, truncates without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.store.truncate',
                id='',
                msg=trans('confirm.assistant.store.truncate'),
            )
            return
        # run asynchronous
        self.window.update_status("Removing vector stores...please wait...")
        QApplication.processEvents()
        self.window.core.assistants.store.truncate()  # clear all stores
        self.window.core.gpt.assistants.importer.truncate_vector_stores()
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()
        self.window.controller.assistant.store.current = None
        self.window.controller.assistant.store.init()

    def refresh_stores(self, force: bool = False):
        """
        Refresh all vector stores

        :param force: if True, refresh without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.store.refresh',
                id='',
                msg=trans('confirm.assistant.store.refresh'),
            )
            return
        self.window.update_status("Refreshing vector stores...please wait...")
        QApplication.processEvents()
        self.window.core.gpt.assistants.importer.refresh_vector_stores()

    def handle_imported_assistants(self, num: int):
        """
        Handle imported assistants

        :param num: number of imported assistants
        """
        self.window.controller.assistant.update()
        self.window.controller.assistant.store.update()
        self.window.controller.assistant.files.update()
        self.window.update_status("OK. Imported assistants: " + str(num) + ".")
        self.window.ui.dialogs.alert(trans("status.finished"))

    def handle_imported_assistants_failed(self, error: Any):
        """
        Handle error on importing assistants

        :param error: error message
        """
        self.window.core.debug.log(error)
        print("Error importing assistants")
        self.window.controller.assistant.update()
        self.window.update_status("Error importing assistants.")
        self.window.ui.dialogs.alert(error)

    def handle_refreshed_stores(self, num: int):
        """
        Handle refreshed stores

        :param num: number of refreshed files
        """
        self.window.controller.assistant.store.update_current()
        self.window.controller.assistant.store.update()
        self.window.ui.dialogs.alert(trans("status.finished"))
        self.window.update_status("OK. All stores refreshed.")

    def handle_refreshed_stores_failed(self, error: Any):
        """
        Handle error on refreshing stores

        :param error: error message
        """
        self.window.core.debug.log(error)
        print("Error refreshing stores", error)
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()
        self.window.update_status("Error refreshing stores.")
        self.window.ui.dialogs.alert(error)

    def handle_imported_stores(self, num: int):
        """
        Handle imported stores

        :param num: number of imported files
        """
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()
        self.window.update_status("OK. Imported stores: " + str(num) + ".")
        # alert on files import after stores
        # self.window.ui.dialogs.alert(trans("status.finished"))

    def handle_imported_stores_failed(self, error: Any):
        """
        Handle error on importing stores

        :param error: error message
        """
        self.window.core.debug.log(error)
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()
        print("Error importing stores", error)
        self.window.update_status("Error importing stores.")
        self.window.ui.dialogs.alert(error)

    def handle_truncated_stores(self, num: int):
        """
        Handle truncated stores

        :param num: number of removed files
        """
        self.window.core.assistants.store.truncate()
        self.remove_all_stores_from_assistants()
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()
        self.window.controller.assistant.store.current = None
        self.window.controller.assistant.store.init()
        self.window.update_status("OK. Removed stores: " + str(num) + ".")
        self.window.ui.dialogs.alert(trans("status.finished"))

    def handle_truncated_stores_failed(self, error: Any):
        """
        Handle error on truncating stores

        :param error: error message
        """
        self.window.core.debug.log(error)
        print("Error removing stores", error)
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()
        self.window.update_status("Error removing stores.")
        self.window.ui.dialogs.alert(error)

    def handle_imported_files(self, num: int):
        """
        Handle imported files

        :param num: number of imported files
        """
        self.window.controller.assistant.files.update()
        self.window.update_status("OK. Imported files: " + str(num) + ".")
        self.window.ui.dialogs.alert(trans("status.finished"))

    def handle_imported_files_failed(self, error: Any):
        """
        Handle error on importing files

        :param error: error message
        """
        self.window.core.debug.log(error)
        self.window.controller.assistant.files.update()
        print("Error importing files")
        self.window.update_status("Error importing files.")
        self.window.ui.dialogs.alert(error)

    def handle_truncated_files(
            self,
            store_id: Optional[str] = None,
            num: int = 0
    ):
        """
        Handle truncated (in API) files

        :param store_id: vector store ID
        :param num: number of truncated files
        """
        self.window.update_status("OK. Truncated files: " + str(num) + ".")
        if store_id is not None:
            self.window.controller.assistant.store.refresh_by_store_id(store_id)
        self.window.controller.assistant.files.update()
        self.window.ui.dialogs.alert(trans("status.finished"))

    def handle_truncated_files_failed(self, error: Any):
        """
        Handle error on truncated files

        :param error: error message
        """
        self.window.core.debug.log(error)
        print("Error truncating files")
        self.window.controller.assistant.files.update()
        self.window.update_status("Error truncating files.")
        self.window.ui.dialogs.alert(error)

    def remove_store_from_assistants(self, store_id: str):
        """
        Remove vector store from all assistants after store deletion

        :param store_id: vector store ID
        """
        for id in list(self.window.core.assistants.items.keys()):
            assistant = self.window.core.assistants.get_by_id(id)
            if assistant is not None:
                if assistant.vector_store == store_id:
                    assistant.vector_store = None  # remove from assistant

        self.window.core.assistants.save()
        self.window.core.assistants.files.on_store_deleted(store_id)  # remove from files

    def remove_all_stores_from_assistants(self):
        """Remove all vector stores from all assistants"""
        for id in list(self.window.core.assistants.items.keys()):
            assistant = self.window.core.assistants.get_by_id(id)
            if assistant is not None:
                assistant.vector_store = None

        self.window.core.assistants.save()
        self.window.core.assistants.files.on_all_stores_deleted()  # remove all from files

    def open_upload_files(self):
        """Open upload files dialog"""
        if self.window.controller.assistant.store.current is None:
            self.window.ui.dialogs.alert("Please select vector store first.")
            return

        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(
            self.window,
            "Select file(s)...",
            "",
            "All Files (*)",
            options=options
        )
        if files:
            self.files_to_upload = files

        if self.files_to_upload:
            msg = "Are you sure you want to upload {} file(s)?".format(len(self.files_to_upload))
            self.window.ui.dialogs.confirm(
                type="assistant.files.upload",
                id=0,
                msg=msg,
            )

    def open_upload_dir(self):
        """Open upload files dialog"""
        if self.window.controller.assistant.store.current is None:
            self.window.ui.dialogs.alert("Please select vector store first.")
            return

        options = QFileDialog.Options()
        directory = QFileDialog.getExistingDirectory(
            self.window,
            "Select directory...",
            options=options
        )
        if directory:
            self.files_to_upload = self.window.core.filesystem.get_files_from_dir(directory)

        if self.files_to_upload:
            msg = ("Are you sure you want to upload {} file(s) from directory {}?".
                   format(len(self.files_to_upload), directory))
            self.window.ui.dialogs.confirm(
                type="assistant.files.upload",
                id=0,
                msg=msg,
            )

    def upload(self, force: bool = False):
        """
        Upload files to vector store

        :param force: if true, uploads without confirmation
        """
        if self.window.controller.assistant.store.current is None:
            self.window.ui.dialogs.alert(trans("dialog.assistant.store.alert.select"))
            return

        store_id = self.window.controller.assistant.store.current
        self.window.update_status("Uploading files...please wait...")
        QApplication.processEvents()
        self.window.core.gpt.assistants.importer.upload_files(store_id, self.files_to_upload)
        self.files_to_upload = []  # clear files

    def handle_uploaded_files(self, num: int):
        """
        Handle uploaded files

        :param num: number of uploaded files
        """
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.refresh_status()
        self.window.update_status("OK. Uploaded files: " + str(num) + ".")
        self.window.ui.dialogs.alert("OK. Uploaded files: " + str(num) + ".")

    def handle_uploaded_files_failed(self, error: Any):
        """
        Handle error on uploading files

        :param error: error message
        """
        self.window.core.debug.log(error)
        print("Error uploading files")
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.refresh_status()
        self.window.update_status("Error uploading files.")
        self.window.ui.dialogs.alert(error)

    def handle_status_change(self, mode: str, msg: str):
        """
        Handle status change

        :param mode: status mode
        :param msg: status message
        """
        self.window.update_status(msg)