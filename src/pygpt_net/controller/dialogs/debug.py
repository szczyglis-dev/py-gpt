#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.05 23:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel

from pygpt_net.core.debug.agent import AgentDebug
from pygpt_net.core.debug.assistants import AssistantsDebug
from pygpt_net.core.debug.attachments import AttachmentsDebug
from pygpt_net.core.debug.config import ConfigDebug
from pygpt_net.core.debug.context import ContextDebug
from pygpt_net.core.debug.db import DatabaseDebug
from pygpt_net.core.debug.events import EventsDebug
from pygpt_net.core.debug.indexes import IndexesDebug
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
        self.workers = {}
        self.workers['agent'] = AgentDebug(self.window)
        self.workers['assistants'] = AssistantsDebug(self.window)
        self.workers['attachments'] = AttachmentsDebug(self.window)
        self.workers['config'] = ConfigDebug(self.window)
        self.workers['context'] = ContextDebug(self.window)
        self.workers['db'] = DatabaseDebug(self.window)
        self.workers['events'] = EventsDebug(self.window)
        self.workers['indexes'] = IndexesDebug(self.window)
        self.workers['models'] = ModelsDebug(self.window)
        self.workers['plugins'] = PluginsDebug(self.window)
        self.workers['presets'] = PresetsDebug(self.window)
        self.workers['tabs'] = TabsDebug(self.window)
        self.workers['ui'] = UIDebug(self.window)

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

    def begin(self, id: str):
        """
        Begin debug data

        :param id: debug id
        """
        self.window.ui.debug[id].setModel(self.models[id])
        self.models[id].dataChanged.connect(self.window.ui.debug[id].on_data_begin)

        if id not in self.counters or self.counters[id] != self.models[id].rowCount():
            self.models[id].removeRows(0, self.models[id].rowCount())
            self.initialized[id] = False
        self.idx[id] = 0

    def end(self, id: str):
        """
        End debug data

        :param id: debug id
        """
        self.counters[id] = self.idx[id]
        self.initialized[id] = True
        self.window.ui.debug[id].on_data_end()

    def add(self, id: str, k: str, v: any):
        """
        Append debug entry

        :param id: debug id
        :param k: key
        :param v: value
        """
        if self.initialized[id] is False:
            idx = self.models[id].rowCount()
            self.models[id].insertRow(idx)
            self.models[id].setData(self.models[id].index(idx, self.DBG_KEY), k)
            self.models[id].setData(self.models[id].index(idx, self.DBG_VALUE), v)
        else:
            for idx in range(0, self.models[id].rowCount()):
                if self.models[id].index(idx, self.DBG_KEY).data() == k:
                    self.models[id].setData(self.models[id].index(idx, self.DBG_VALUE), v)
                    self.idx[id] += 1
                    return
        self.idx[id] += 1

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
        self.window.ui.dialogs.open('debug.' + id, width=800, height=600)

    def hide(self, id: str):
        """
        Deactivate debug window

        :param id: debug id
        """
        if id not in self.active:
            return
        self.active[id] = False
        self.window.ui.dialogs.close('debug.' + id)

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
