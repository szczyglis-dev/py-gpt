#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.21 01:00:00                  #
# ================================================== #

import time
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel

from pygpt_net.core.debug.agent import AgentDebug
from pygpt_net.core.debug.agent_builder import AgentBuilderDebug
from pygpt_net.core.debug.assistants import AssistantsDebug
from pygpt_net.core.debug.attachments import AttachmentsDebug
from pygpt_net.core.debug.config import ConfigDebug
from pygpt_net.core.debug.context import ContextDebug
from pygpt_net.core.debug.db import DatabaseDebug
from pygpt_net.core.debug.events import EventsDebug
from pygpt_net.core.debug.indexes import IndexesDebug
from pygpt_net.core.debug.kernel import KernelDebug
from pygpt_net.core.debug.models import ModelsDebug
from pygpt_net.core.debug.plugins import PluginsDebug
from pygpt_net.core.debug.presets import PresetsDebug
from pygpt_net.core.debug.tabs import TabsDebug
from pygpt_net.core.debug.ui import UIDebug


class Debug:

    DBG_KEY, DBG_VALUE = range(2)

    def __init__(self, window=None):
        """
        Debugger handler

        :param window: Window instance
        """
        self.window = window

        # setup workers
        self.workers = {
            'agent': AgentDebug(self.window),
            'agent_builder': AgentBuilderDebug(self.window),
            'assistants': AssistantsDebug(self.window),
            'attachments': AttachmentsDebug(self.window),
            'config': ConfigDebug(self.window),
            'context': ContextDebug(self.window),
            'db': DatabaseDebug(self.window),
            'events': EventsDebug(self.window),
            'indexes': IndexesDebug(self.window),
            'kernel': KernelDebug(self.window),
            'models': ModelsDebug(self.window),
            'plugins': PluginsDebug(self.window),
            'presets': PresetsDebug(self.window),
            'tabs': TabsDebug(self.window),
            'ui': UIDebug(self.window)
        }

        self.is_realtime = False  # real-time data update

        # prepare debug ids
        self.ids = self.workers.keys()
        self.models = {}
        self.initialized = {}
        self.active = {}
        self.idx = {}
        self.counters = {}

        # prepare debug workers data
        for id in self.ids:
            self.models[id] = self.create_model(self.window)
            self.initialized[id] = False
            self.active[id] = False
            self.idx[id] = 0

    def refresh(self, id: str):
        """
        Refresh debug data

        :param id: debug id
        """
        if id in self.initialized:
            self.initialized[id] = False

    def begin(self, id: str):
        """
        Begin debug data

        :param id: debug id
        """
        if self.initialized[id] and not self.is_realtime:
            if self.is_active(id):
                return  # skip if already initialized and realtime disabled

        upd_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        self.window.ui.debug[id].last_update_label.setText(
            f"Last update: {upd_time}"
        )

        model = self.models.get(id, None)
        dialog = self.window.ui.debug[id]
        dialog.setModel(model)
        model.dataChanged.connect(dialog.on_data_begin)

        dialog.setUpdatesEnabled(False)
        if id not in self.counters or self.counters[id] != model.rowCount():
            model.removeRows(0, model.rowCount())
            self.initialized[id] = False
        self.idx[id] = 0

    def set_realtime(self, id: str, enabled: bool):
        """
        Set realtime mode

        :param id: debug id
        :param enabled: enable realtime
        """
        self.is_realtime = enabled

    def end(self, id: str):
        """
        End debug data

        :param id: debug id
        """
        dialog = self.window.ui.debug[id]
        self.counters[id] = self.idx[id]
        self.initialized[id] = True
        self.window.ui.debug[id].on_data_end()
        dialog.setUpdatesEnabled(True)

    def add(self, id: str, k: str, v: Any):
        """
        Append debug entry

        :param id: debug id
        :param k: key
        :param v: value
        """
        model = self.models.get(id, None)
        if self.initialized[id] is False:
            idx = model.rowCount()
            model.insertRow(idx)
            model.setData(model.index(idx, self.DBG_KEY), k)
            model.setData(model.index(idx, self.DBG_VALUE), v)
            self.idx[id] += 1
        else:
            for idx in range(0, model.rowCount()):
                self.idx[id] += 1
                if model.index(idx, self.DBG_KEY).data() == k:
                    if model.index(idx, self.DBG_VALUE).data() == v:
                        continue  # no changes, skip update
                    model.setData(model.index(idx, self.DBG_VALUE), v)
                    return

    def get_ids(self) -> list:
        """
        Get debug workers ids

        :return: list of ids
        """
        return list(self.ids)

    def get_workers(self) -> dict:
        """
        Get debug workers

        :return: dict of workers
        """
        return self.workers

    def update_worker(self, id: str):
        """
        Update debug worker

        :param id: debug id
        """
        if id in self.workers:
            self.workers[id].update()

    def is_active(self, id: str) -> bool:
        """
        Check if debug window is active

        :param id: debug id
        :return: True if active
        """
        if id not in self.active:
            return False
        return self.active[id]

    def show(self, id: str):
        """
        Activate debug window

        :param id: debug id
        """
        if id not in self.active:
            return
        self.active[id] = True
        self.window.ui.dialogs.open(f"debug.{id}", width=800, height=600)

    def hide(self, id: str):
        """
        Deactivate debug window

        :param id: debug id
        """
        if id not in self.active:
            return
        self.active[id] = False
        self.window.ui.dialogs.close(f"debug.{id}")

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create list model

        :param parent: parent widget
        :return: model instance
        """
        model = QStandardItemModel(0, 2, parent)
        model.setHeaderData(self.DBG_KEY, Qt.Horizontal, "Key")
        model.setHeaderData(self.DBG_VALUE, Qt.Horizontal, "Value")
        return model
