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

from typing import Any

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
        self.window.core.api.openai.assistants.importer.import_assistants()

    def handle_imported_assistants(self, num: int):
        """
        Handle imported assistants

        :param num: number of imported assistants
        """
        self.window.controller.assistant.update()
        self.window.controller.remote_store.update()
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
        self.window.core.remote_store.openai.files.on_store_deleted(store_id)  # remove from files

    def remove_all_stores_from_assistants(self):
        """Remove all vector stores from all assistants"""
        for id in list(self.window.core.assistants.items.keys()):
            assistant = self.window.core.assistants.get_by_id(id)
            if assistant is not None:
                assistant.vector_store = None

        self.window.core.assistants.save()
        self.window.core.remote_store.openai.files.on_all_stores_deleted()  # remove all from files

    def handle_status_change(self, mode: str, msg: str):
        """
        Handle status change

        :param mode: status mode
        :param msg: status message
        """
        self.window.update_status(msg)