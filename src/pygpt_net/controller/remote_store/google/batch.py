#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 20:00:00                  #
# ================================================== #

from typing import Optional, Any, Union

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog, QApplication

from pygpt_net.utils import trans


class Batch:
    def __init__(self, window=None):
        """
        File Search stores batch controller (Google)

        :param window: Window instance
        """
        self.window = window
        self.files_to_upload = []

    def import_stores(self, force: bool = False):
        """
        Import File Search stores

        :param force: if true, imports without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='remote_store.google.import',
                id='',
                msg=trans('confirm.remote_store.import'),
            )
            return
        self.window.update_status("Importing File Search stores...please wait...")
        self.window.core.remote_store.google.truncate()
        self.window.core.api.google.store.importer.import_vector_stores()
        self.window.controller.remote_store.google.update()

    def import_files(self, force: bool = False):
        """
        Sync documents with API (all)
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='remote_store.google.files.import.all',
                id='',
                msg=trans('confirm.remote_store.import_files'),
            )
            return
        try:
            self.window.core.api.google.store.importer.import_files()  # all
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(e)

    def import_store_files(self, store_id: str, force: bool = False):
        """
        Sync documents with API (store)

        :param store_id: store name ('fileSearchStores/...').
        """
        if store_id is None:
            self.window.ui.dialogs.alert(trans("dialog.remote_store.alert.select"))
            return

        if not force:
            self.window.ui.dialogs.confirm(
                type='remote_store.google.files.import.store',
                id=store_id,
                msg=trans('confirm.remote_store.import_files.store'),
            )
            return
        try:
            self.window.core.api.google.store.importer.import_files(store_id)  # by store
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(e)

    def truncate_files(self, force: bool = False):
        """
        Truncate all documents in API
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='remote_store.google.files.truncate',
                id='',
                msg=trans('confirm.remote_store.openai.files.truncate'),  # reuse same translation key
            )
            return
        self.window.update_status("Removing documents...please wait...")
        QApplication.processEvents()
        self.window.core.api.google.store.importer.truncate_files()

    def truncate_store_files_by_idx(self, idx: Union[int, list], force: bool = False):
        """
        Truncate all documents in API (store)
        """
        store_ids = []
        ids = idx if isinstance(idx, list) else [idx]
        for i in ids:
            store_id = self.window.controller.remote_store.google.get_by_tab_idx(i)
            store_ids.append(store_id)
        self.truncate_store_files(store_ids, force)

    def truncate_store_files(self, store_id: Union[str, list], force: bool = False):
        """
        Truncate all documents in API (store)
        """
        if store_id is None:
            self.window.ui.dialogs.alert(trans("dialog.remote_store.alert.select"))
            return

        if not force:
            self.window.ui.dialogs.confirm(
                type='remote_store.google.files.truncate.store',
                id=store_id,
                msg=trans('confirm.remote_store.openai.files.truncate.store'),
            )
            return
        self.window.update_status("Removing documents...please wait...")
        QApplication.processEvents()
        ids = store_id if isinstance(store_id, list) else [store_id]
        for sid in ids:
            self.window.core.api.google.store.importer.truncate_files(sid)

    def clear_store_files_by_idx(self, idx: Union[int, list], force: bool = False):
        """
        Clear documents (store, local only)
        """
        store_ids = []
        ids = idx if isinstance(idx, list) else [idx]
        for i in ids:
            store_id = self.window.controller.remote_store.google.get_by_tab_idx(i)
            store_ids.append(store_id)
        self.clear_store_files(store_ids, force)

    def clear_store_files(self, store_id: Optional[Union[str, list]] = None, force: bool = False):
        """
        Clear documents (store, local only)
        """
        if store_id is None:
            self.window.ui.dialogs.alert(trans("dialog.remote_store.alert.select"))
            return

        if not force:
            self.window.ui.dialogs.confirm(
                type='remote_store.google.files.clear.store',
                id=store_id,
                msg=trans('confirm.assistant.files.clear'),
            )
            return
        self.window.update_status("Clearing store documents...please wait...")
        QApplication.processEvents()

        ids = store_id if isinstance(store_id, list) else [store_id]
        for sid in ids:
            self.window.core.remote_store.google.files.truncate_local(sid)

        # Immediate UI refresh from local DB
        try:
            self.window.controller.remote_store.google.update_files_list()
        except Exception:
            pass

        self.window.update_status("OK. Store documents cleared.")
        self.window.ui.dialogs.alert(trans("status.finished"))

    def clear_files(self, force: bool = False):
        """
        Clear documents (all, local only)
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='remote_store.google.files.clear.all',
                id='',
                msg=trans('confirm.assistant.files.clear'),
            )
            return
        self.window.update_status("Clearing documents...please wait...")
        QApplication.processEvents()
        self.window.core.remote_store.google.files.truncate_local()
        self.window.update_status("OK. All documents cleared.")
        self.window.ui.dialogs.alert(trans("status.finished"))

    def clear_stores(self, force: bool = False):
        """
        Clear File Search stores (local only)
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='remote_store.google.clear',
                id='',
                msg=trans('confirm.remote_store.clear'),
            )
            return
        self.window.update_status("Clearing File Search stores...please wait...")
        QApplication.processEvents()
        self.window.core.remote_store.google.truncate()
        self.window.controller.remote_store.google.update()
        self.window.update_status("OK. All stores cleared.")
        self.window.controller.remote_store.google.current = None
        self.window.controller.remote_store.google.init()

    def truncate_stores(self, force: bool = False):
        """
        Truncate File Search stores in API
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='remote_store.google.truncate',
                id='',
                msg=trans('confirm.remote_store.truncate'),
            )
            return
        self.window.update_status("Removing File Search stores...please wait...")
        QApplication.processEvents()
        self.window.core.remote_store.google.truncate()
        self.window.core.api.google.store.importer.truncate_vector_stores()
        self.window.controller.remote_store.google.update()
        self.window.controller.remote_store.google.current = None
        self.window.controller.remote_store.google.init()

    def refresh_stores(self, force: bool = False):
        """
        Refresh all File Search stores
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='remote_store.google.refresh',
                id='',
                msg=trans('confirm.remote_store.refresh'),
            )
            return
        self.window.update_status("Refreshing File Search stores...please wait...")
        QApplication.processEvents()
        self.window.core.api.google.store.importer.refresh_vector_stores()

    def handle_refreshed_stores(self, num: int):
        self.window.controller.remote_store.google.update_current()
        self.window.controller.remote_store.google.update()
        self.window.ui.dialogs.alert(trans("status.finished"))
        self.window.update_status("OK. All stores refreshed.")

    def handle_refreshed_stores_failed(self, error: Any):
        self.window.core.debug.log(error)
        print("Error refreshing stores", error)
        self.window.controller.remote_store.google.update()
        self.window.update_status("Error refreshing stores.")
        self.window.ui.dialogs.alert(error)

    def handle_imported_stores(self, num: int):
        self.window.controller.remote_store.google.update()
        self.window.update_status("OK. Imported stores: " + str(num) + ".")

    def handle_imported_stores_failed(self, error: Any):
        self.window.core.debug.log(error)
        self.window.controller.remote_store.google.update()
        print("Error importing stores", error)
        self.window.update_status("Error importing stores.")
        self.window.ui.dialogs.alert(error)

    def handle_truncated_stores(self, num: int):
        """
        Handle truncated stores

        :param num: number of removed files
        """
        self.window.core.remote_store.google.truncate()
        self.window.controller.remote_store.google.update()
        self.window.controller.remote_store.google.current = None
        self.window.controller.remote_store.google.init()
        self.window.update_status("OK. Removed stores: " + str(num) + ".")
        self.window.ui.dialogs.alert(trans("status.finished"))

    def handle_truncated_stores_failed(self, error: Any):
        """
        Handle error on truncating stores

        :param error: error message
        """
        self.window.core.debug.log(error)
        print("Error removing stores", error)
        self.window.controller.remote_store.google.update()
        self.window.update_status("Error removing stores.")
        self.window.ui.dialogs.alert(error)

    def handle_imported_files(self, num: int):
        self.window.update_status("OK. Imported documents: " + str(num) + ".")
        self.window.ui.dialogs.alert(trans("status.finished"))

    def handle_imported_files_failed(self, error: Any):
        self.window.core.debug.log(error)
        print("Error importing documents")
        self.window.update_status("Error importing documents.")
        self.window.ui.dialogs.alert(error)

    def handle_truncated_files(self, store_id: Optional[str] = None, num: int = 0):
        self.window.update_status("OK. Truncated documents: " + str(num) + ".")
        # Immediate UI refresh of files panel (local DB is already truncated)
        try:
            self.window.controller.remote_store.google.update_files_list()
        except Exception:
            pass

        # Refresh remote status to update counts and bytes
        if store_id is not None:
            self.window.controller.remote_store.google.refresh_by_store_id(store_id)
        else:
            self.refresh_delayed(1200)
        self.window.ui.dialogs.alert(trans("status.finished"))

    def handle_truncated_files_failed(self, error: Any):
        self.window.core.debug.log(error)
        print("Error truncating documents")
        self.window.update_status("Error truncating documents.")
        self.window.ui.dialogs.alert(error)

    def open_upload_files(self):
        """Open upload files dialog"""
        if self.window.controller.remote_store.google.current is None:
            self.window.ui.dialogs.alert("Please select File Search store first.")
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
                type="remote_store.google.files.upload",
                id=0,
                msg=msg,
            )

    def open_upload_dir(self):
        """Open upload directory dialog"""
        if self.window.controller.remote_store.google.current is None:
            self.window.ui.dialogs.alert("Please select File Search store first.")
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
                type="remote_store.google.files.upload",
                id=0,
                msg=msg,
            )

    def refresh_delayed(self, ms: int = 1000):
        self.window.update_status("Refreshing status...")
        QTimer.singleShot(ms, lambda: self.window.controller.remote_store.google.refresh_status())

    def upload(self, force: bool = False):
        """Upload files to File Search store"""
        if self.window.controller.remote_store.google.current is None:
            self.window.ui.dialogs.alert(trans("dialog.remote_store.alert.select"))
            return

        store_id = self.window.controller.remote_store.google.current
        self.window.update_status("Uploading files...please wait...")
        QApplication.processEvents()
        self.window.core.api.google.store.importer.upload_files(store_id, self.files_to_upload)
        self.files_to_upload = []

    def handle_uploaded_files(self, num: int):
        self.window.update_status("OK. Uploaded files: " + str(num) + ".")
        self.window.ui.dialogs.alert("OK. Uploaded files: " + str(num) + ".")
        self.refresh_delayed(1500)

    def handle_uploaded_files_failed(self, error: Any):
        self.window.core.debug.log(error)
        print("Error uploading files")
        self.refresh_delayed(1500)
        self.window.update_status("Error uploading files.")
        self.window.ui.dialogs.alert(error)