#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.27 10:00:00                  #
# ================================================== #


from PySide6.QtWidgets import QApplication

from pygpt_net.utils import trans


class Batch:
    def __init__(self, window=None):
        """
        Assistants batch controller

        :param window: Window instance
        """
        self.window = window

    def import_assistants(self, force: bool = False):
        """
        Import all remote assistants from API

        :param force: if true, imports without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant_import',
                id='',
                msg=trans('confirm.assistant.import'),
            )
            return

        # run asynchronous
        self.window.ui.status("Importing assistants...please wait...")
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
        self.window.ui.status("Importing vector stores...please wait...")
        self.window.core.assistants.store.truncate()  # clear all stores
        self.window.core.gpt.assistants.importer.import_vector_stores()
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()

    def import_files(self, force: bool = False):
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
            self.window.controller.assistant.import_files(assistant)
        except Exception as e:
            self.window.core.debug.log(e)
            self.window.ui.dialogs.alert(e)

    def truncate_files(self, force: bool = False):
        """
        Truncate all files in API

        :param force: if true, imports without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.files.truncate',
                id='',
                msg=trans('confirm.assistant.files.truncate'),
            )
            return
        # run asynchronous
        self.window.ui.status("Removing files...please wait...")
        QApplication.processEvents()
        self.window.core.gpt.assistants.importer.truncate_files()  # remove all files from API

    def clear_files(self, force: bool = False):
        """
        Clear files (local only)

        :param force: if true, clears without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.files.clear',
                id='',
                msg=trans('confirm.assistant.files.clear'),
            )
            return
        self.window.ui.status("Clearing files...please wait...")
        self.window.core.assistants.files.truncate_local()  # clear files local
        self.window.controller.assistant.files.update()
        self.window.ui.status("OK. All files cleared.")
        self.window.ui.dialogs.alert(trans("status.finished"))

    def clear_stores(self, force: bool = False):
        """
        Clear vector stores (local only)

        :param force: if true, clears without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.store.clear',
                id='',
                msg=trans('confirm.assistant.store.clear'),
            )
            return
        self.window.ui.status("Clearing vector stores...please wait...")
        self.window.core.assistants.store.truncate()  # clear all stores
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()
        self.window.ui.status("OK. All stores cleared.")
        self.window.controller.assistant.store.current = None
        self.window.controller.assistant.store.init()

    def truncate_stores(self, force: bool = False):
        """
        Truncate vector stores in API

        :param force: if true, truncates without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.store.truncate',
                id='',
                msg=trans('confirm.assistant.store.truncate'),
            )
            return
        # run asynchronous
        self.window.ui.status("Removing vector stores...please wait...")
        self.window.core.assistants.store.truncate()  # clear all stores
        self.window.core.gpt.assistants.importer.truncate_vector_stores()
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()
        self.window.controller.assistant.store.current = None
        self.window.controller.assistant.store.init()

    def refresh_stores(self, force: bool = False):
        """
        Refresh all vector stores

        :param force: if true, refresh without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='assistant.store.refresh',
                id='',
                msg=trans('confirm.assistant.store.refresh'),
            )
            return
        self.window.ui.status("Refreshing vector stores...please wait...")
        QApplication.processEvents()
        self.window.core.gpt.assistants.importer.refresh_vector_stores()

    def handle_imported_assistants(self, num: int):
        """
        Handle imported assistants

        :param num: number of imported assistants
        """
        self.window.ui.status("OK. Imported assistants: " + str(num) + ".")
        self.window.controller.assistant.update()
        self.window.controller.assistant.store.update()
        self.window.controller.assistant.files.update()

    def handle_imported_assistants_failed(self, error: any):
        """
        Handle error on importing assistants

        :param error: error message
        """
        self.window.core.debug.log(error)
        print("Error importing assistants")
        self.window.ui.status("Error importing assistants.")
        self.window.ui.dialogs.alert(error)
        self.window.controller.assistant.update()

    def handle_refreshed_stores(self, num: int):
        """
        Handle refreshed stores

        :param num: number of refreshed files
        """
        self.window.controller.assistant.store.update_current()
        self.window.controller.assistant.store.update()
        self.window.ui.dialogs.alert(trans("status.finished"))
        self.window.ui.status("OK. All stores refreshed.")

    def handle_refreshed_stores_failed(self, error: any):
        """
        Handle error on refreshing stores

        :param error: error message
        """
        self.window.core.debug.log(error)
        print("Error refreshing stores", error)
        self.window.ui.status("Error refreshing stores.")
        self.window.ui.dialogs.alert(error)
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()

    def handle_imported_stores(self, num: int):
        """
        Handle imported stores

        :param num: number of imported files
        """
        self.window.ui.status("OK. Imported stores: " + str(num) + ".")
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()
        self.window.ui.dialogs.alert(trans("status.finished"))

    def handle_imported_stores_failed(self, error: any):
        """
        Handle error on importing stores

        :param error: error message
        """
        self.window.core.debug.log(error)
        print("Error importing stores", error)
        self.window.ui.status("Error importing stores.")
        self.window.ui.dialogs.alert(error)
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()

    def handle_truncated_stores(self, num: int):
        """
        Handle truncated stores

        :param num: number of removed files
        """
        self.window.core.assistants.store.truncate()
        self.remove_all_stores_from_assistants()
        self.window.ui.status("OK. Removed stores: " + str(num) + ".")
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()
        self.window.controller.assistant.store.current = None
        self.window.controller.assistant.store.init()
        self.window.ui.dialogs.alert(trans("status.finished"))

    def handle_truncated_stores_failed(self, error: any):
        """
        Handle error on truncating stores

        :param error: error message
        """
        self.window.core.debug.log(error)
        print("Error removing stores", error)
        self.window.ui.status("Error removing stores.")
        self.window.ui.dialogs.alert(error)
        self.window.controller.assistant.files.update()
        self.window.controller.assistant.store.update()

    def handle_imported_files(self, num: int):
        """
        Handle imported files

        :param num: number of imported files
        """
        self.window.ui.status("OK. Imported files: " + str(num) + ".")
        self.window.controller.assistant.files.update()
        self.window.ui.dialogs.alert(trans("status.finished"))

    def handle_imported_files_failed(self, error: any):
        """
        Handle error on importing files

        :param error: error message
        """
        self.window.core.debug.log(error)
        print("Error importing files")
        self.window.ui.status("Error importing files.")
        self.window.ui.dialogs.alert(error)
        self.window.controller.assistant.files.update()

    def handle_truncated_files(self, num: int):
        """
        Handle truncated (in API) files

        :param num: number of truncated files
        """
        self.window.ui.status("OK. Truncated files: " + str(num) + ".")
        self.window.controller.assistant.files.update()
        self.window.ui.dialogs.alert(trans("status.finished"))

    def handle_truncated_files_failed(self, error: any):
        """
        Handle error on truncated files

        :param error: error message
        """
        self.window.core.debug.log(error)
        print("Error truncating files")
        self.window.ui.status("Error truncating files.")
        self.window.ui.dialogs.alert(error)
        self.window.controller.assistant.files.update()

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