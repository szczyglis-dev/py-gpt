# controller/remote_store/remote_store.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.05 17:00:00                  #
# ================================================== #

from typing import Optional, Union, Any, List

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog

from pygpt_net.utils import trans

class Batch:
    """
    Proxy for batch operations for a specific remote store provider used by Confirm router
    """

    def __init__(self, ctrl):
        self.ctrl = ctrl
        self.window = ctrl.window
        self.files_to_upload: List[str] = []

    # ---------- Starters (invoked by Confirm router) ----------

    def import_stores(self, force: bool = False):
        if not force:
            self.window.ui.dialogs.confirm(
                type=f'remote_store.import',
                id='',
                msg=trans('confirm.remote_store.import'),
            )
            return
        self.window.update_status("Importing stores...please wait...")
        self.ctrl._core_for(self._get_provider()).truncate()
        self._importer().import_vector_stores()

    def truncate_stores(self, force: bool = False):
        if not force:
            self.window.ui.dialogs.confirm(
                type=f'remote_store.truncate',
                id='',
                msg=trans('confirm.remote_store.truncate'),
            )
            return
        self.window.update_status("Removing stores...please wait...")
        QApplication.processEvents()
        self._importer().truncate_vector_stores()

    def refresh_stores(self, force: bool = False):
        if not force:
            self.window.ui.dialogs.confirm(
                type=f'remote_store.refresh',
                id='',
                msg=trans('confirm.remote_store.refresh'),
            )
            return
        self.window.update_status("Refreshing stores...please wait...")
        QApplication.processEvents()
        self._importer().refresh_vector_stores()

    def import_files_assistant_current(self, force: bool = False):
        """Import assistant files from API for current assistant"""
        id = self.window.core.config.get('assistant')
        if id is None or id == "":
            return
        if self.window.core.assistants.has(id):
            assistant = self.window.core.assistants.get_by_id(id)
            store_id = assistant.vector_store
            if store_id is None or store_id == "":
                self.window.ui.dialogs.alert(trans("dialog.remote_store.alert.assign"))
                return
            if not force:
                self.window.ui.dialogs.confirm(
                    type=f'remote_store.files.import.assistant.current',
                    id=store_id,
                    msg=trans('confirm.remote_store.import_files.store'),
                )
                return
            self.window.core.api.openai.store.importer.import_files(store_id) # for current assistant

    def import_files_assistant_all(self, force: bool = False):
        """Import assistant files from API for all assistants"""
        if not force:
            self.window.ui.dialogs.confirm(
                type=f'remote_store.files.import.assistant.all',
                id='',
                msg=trans('confirm.remote_store.import_files'),
            )
            return
        self.window.core.api.openai.store.importer.import_files()  # all

    def import_files(self, force: bool = False):
        if not force:
            self.window.ui.dialogs.confirm(
                type=f'remote_store.files.import.all',
                id='',
                msg=trans('confirm.remote_store.import_files'),
            )
            return
        self._importer().import_files()  # all

    def import_store_files(self, store_id: str, force: bool = False):
        if store_id is None:
            self.window.ui.dialogs.alert(trans("dialog.remote_store.alert.select"))
            return
        if not force:
            self.window.ui.dialogs.confirm(
                type=f'remote_store.files.import.store',
                id=store_id,
                msg=trans('confirm.remote_store.import_files.store'),
            )
            return
        self._importer().import_files(store_id)

    def truncate_files(self, force: bool = False):
        if not force:
            key = 'confirm.remote_store.files.truncate'
            self.window.ui.dialogs.confirm(
                type=f'remote_store.files.truncate',
                id='',
                msg=trans(key),
            )
            return
        self.window.update_status("Removing files...please wait...")
        QApplication.processEvents()
        self._importer().truncate_files()

    def truncate_store_files(self, store_id: Union[str, list], force: bool = False):
        if store_id is None:
            self.window.ui.dialogs.alert(trans("dialog.remote_store.alert.select"))
            return
        if not force:
            key = 'confirm.remote_store.files.truncate.store'
            self.window.ui.dialogs.confirm(
                type=f'remote_store.files.truncate.store',
                id=store_id,
                msg=trans(key),
            )
            return
        self.window.update_status("Removing files...please wait...")
        QApplication.processEvents()
        ids = store_id if isinstance(store_id, list) else [store_id]
        for sid in ids:
            self._importer().truncate_files(sid)

    def clear_stores(self, force: bool = False):
        if not force:
            self.window.ui.dialogs.confirm(
                type=f'remote_store.clear',
                id='',
                msg=trans('confirm.remote_store.clear'),
            )
            return
        self.window.update_status("Clearing stores...please wait...")
        QApplication.processEvents()
        self.ctrl._core_for(self._get_provider()).truncate()
        self.ctrl.update()
        self.ctrl.current = None
        self.ctrl.init()
        self.window.update_status("OK. All stores cleared.")
        if self._get_provider() == "openai":
            self.window.controller.assistant.files.update()

    def clear_files(self, force: bool = False):
        if not force:
            self.window.ui.dialogs.confirm(
                type=f'remote_store.files.clear.all',
                id='',
                msg=trans('confirm.assistant.files.clear'),
            )
            return
        self.window.update_status("Clearing documents...please wait...")
        QApplication.processEvents()
        self.ctrl._files_core_for(self._get_provider()).truncate_local()
        self.ctrl.update()
        self.window.update_status("OK. All documents cleared.")
        self.window.ui.dialogs.alert(trans("status.finished"))

    def clear_store_files(self, store_id: Optional[Union[str, list]] = None, force: bool = False):
        if store_id is None:
            self.window.ui.dialogs.alert(trans("dialog.remote_store.alert.select"))
            return
        if not force:
            self.window.ui.dialogs.confirm(
                type=f'remote_store.files.clear.store',
                id=store_id,
                msg=trans('confirm.assistant.files.clear'),
            )
            return
        self.window.update_status("Clearing store documents...please wait...")
        QApplication.processEvents()
        ids = store_id if isinstance(store_id, list) else [store_id]
        for sid in ids:
            self.ctrl._files_core_for(self._get_provider()).truncate_local(sid)
        self.ctrl.update()
        self.window.update_status("OK. Store documents cleared.")
        self.window.ui.dialogs.alert(trans("status.finished"))

    # ---------- Upload ----------

    def open_upload_files(self):
        if self.ctrl.current is None:
            self.window.ui.dialogs.alert(trans("dialog.remote_store.alert.select"))
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
                type=f"remote_store.files.upload",
                id=0,
                msg=msg,
            )

    def open_upload_dir(self):
        if self.ctrl.current is None:
            self.window.ui.dialogs.alert(trans("dialog.remote_store.alert.select"))
            return
        options = QFileDialog.Options()
        directory = QFileDialog.getExistingDirectory(self.window, "Select directory...", options=options)
        if directory:
            self.files_to_upload = self.window.core.filesystem.get_files_from_dir(directory)
        if self.files_to_upload:
            msg = ("Are you sure you want to upload {} file(s) from directory {}?".
                   format(len(self.files_to_upload), directory))
            self.window.ui.dialogs.confirm(
                type=f"remote_store.files.upload",
                id=0,
                msg=msg,
            )

    def upload(self, force: bool = False):
        if self.ctrl.current is None:
            self.window.ui.dialogs.alert(trans("dialog.remote_store.alert.select"))
            return
        self.window.update_status("Uploading files...please wait...")
        QApplication.processEvents()
        self._importer().upload_files(self.ctrl.current, self.files_to_upload)
        self.files_to_upload = []

    def refresh_delayed(self, ms: int = 1000):
        self.window.update_status("Refreshing status...")
        QTimer.singleShot(ms, lambda: self.ctrl.refresh_status())

    # ---------- Importer signal handlers (called by provider Importer) ----------

    def handle_refreshed_stores(self, num: int):
        self.ctrl.update()
        self.window.ui.dialogs.alert(trans("status.finished"))
        self.window.update_status("OK. All stores refreshed.")

    def handle_refreshed_stores_failed(self, error: Any):
        self.window.core.debug.log(error)
        self.ctrl.update()
        self.window.update_status("Error refreshing stores.")
        self.window.ui.dialogs.alert(error)

    def handle_imported_stores(self, num: int):
        self.ctrl.after_imported_stores(self._get_provider())
        self.ctrl.update()
        self.window.update_status("OK. Imported stores: " + str(num) + ".")

    def handle_imported_stores_failed(self, error: Any):
        self.window.core.debug.log(error)
        self.ctrl.update()
        self.window.update_status("Error importing stores.")
        self.window.ui.dialogs.alert(error)

    def handle_truncated_stores(self, num: int):
        # Clear local DB for provider
        core = self.ctrl._core_for(self._get_provider())
        core.truncate()
        self.ctrl.after_truncated_stores(self._get_provider())
        self.ctrl.update()
        self.ctrl.current = None
        self.ctrl.init()
        self.window.update_status("OK. Removed stores: " + str(num) + ".")
        self.window.ui.dialogs.alert(trans("status.finished"))

    def handle_truncated_stores_failed(self, error: Any):
        self.window.core.debug.log(error)
        self.ctrl.update()
        self.window.update_status("Error removing stores.")
        self.window.ui.dialogs.alert(error)

    def handle_imported_files(self, num: int):
        try:
            self.window.controller.assistant.files.update()
        except Exception:
            pass
        self.window.update_status("OK. Imported files: " + str(num) + ".")
        self.window.ui.dialogs.alert(trans("status.finished"))

    def handle_imported_files_failed(self, error: Any):
        self.window.core.debug.log(error)
        self.window.update_status("Error importing documents.")
        self.window.ui.dialogs.alert(error)

    def handle_truncated_files(self, store_id: Optional[str] = None, num: int = 0):
        self.window.update_status("OK. Truncated documents: " + str(num) + ".")
        try:
            if store_id is not None:
                self.ctrl.refresh_by_store_id_provider(self._get_provider(), store_id)
            else:
                self.refresh_delayed(1200)
        finally:
            self.window.ui.dialogs.alert(trans("status.finished"))

    def handle_truncated_files_failed(self, error: Any):
        self.window.core.debug.log(error)
        self.window.update_status("Error truncating documents.")
        self.window.ui.dialogs.alert(error)

    def handle_uploaded_files(self, num: int):
        try:
            self.window.controller.assistant.files.update()
        except Exception:
            pass
        self.window.update_status("OK. Uploaded files: " + str(num) + ".")
        self.window.ui.dialogs.alert("OK. Uploaded files: " + str(num) + ".")
        self.refresh_delayed(1500)

    def handle_uploaded_files_failed(self, error: Any):
        self.window.core.debug.log(error)
        self.refresh_delayed(1500)
        self.window.update_status("Error uploading files.")
        self.window.ui.dialogs.alert(error)

    # ---------- Internal ----------

    def _get_provider(self):
        return self.ctrl.provider_key

    def _importer(self):
        provider = self._get_provider()
        if (hasattr(self.window.core.api, provider)
                and hasattr(getattr(self.window.core.api, provider), 'store')
                and hasattr(getattr(self.window.core.api, provider).store, 'importer')):
            return getattr(self.window.core.api, provider).store.importer