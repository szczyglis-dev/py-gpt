#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.28 21:00:00                  #
# ================================================== #

import os
import sys
import traceback
import logging

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import QHeaderView

from pygpt_net.config import Config

from .assistants import AssistantsDebug
from .attachments import AttachmentsDebug
from .config import ConfigDebug
from .context import ContextDebug
from .models import ModelsDebug
from .plugins import PluginsDebug
from .presets import PresetsDebug
from .ui import UIDebug


class CustomQtMsgType:
    QtDebugMsg = logging.DEBUG
    QtInfoMsg = logging.INFO
    QtWarningMsg = logging.WARNING
    QtCriticalMsg = logging.ERROR
    QtFatalMsg = logging.CRITICAL


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
        self.workers['assistants'] = AssistantsDebug(self.window)
        self.workers['attachments'] = AttachmentsDebug(self.window)
        self.workers['config'] = ConfigDebug(self.window)
        self.workers['context'] = ContextDebug(self.window)
        self.workers['models'] = ModelsDebug(self.window)
        self.workers['plugins'] = PluginsDebug(self.window)
        self.workers['presets'] = PresetsDebug(self.window)
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

    @staticmethod
    def init(level=logging.ERROR):
        """
        Initialize error handler
        """
        if not os.path.exists(os.path.join(Path.home(), '.config', Config.CONFIG_DIR)):
            os.makedirs(os.path.join(Path.home(), '.config', Config.CONFIG_DIR))

        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=str(Path(os.path.join(Path.home(), '.config', Config.CONFIG_DIR, 'error.log'))),
            filemode='a'
        )

        def handle_exception(exc_type, value, tb):
            """
            Handle uncaught exception
            """
            logger = logging.getLogger()
            if not hasattr(logging, '_is_handling_exception'):
                logging._is_handling_exception = True
                logger.error("Uncaught exception:", exc_info=(exc_type, value, tb))
                traceback.print_exception(exc_type, value, tb)
                del logging._is_handling_exception  # remove flag when done
            else:
                traceback.print_exception(exc_type, value, tb)

        sys.excepthook = handle_exception

    def log(self, message=None, level=logging.ERROR):
        """
        Handle logging

        :param message: message to log
        :param level: logging level
        """
        if message is None:
            return

        logger = logging.getLogger()

        try:
            # string message
            if isinstance(message, str):
                print("Log: {}".format(message))
                logger.log(level, message)
            # exception message
            elif isinstance(message, Exception):
                etype, value, tb = sys.exc_info()
                traceback_details = traceback.extract_tb(tb)
                if len(traceback_details) >= 4:
                    last_calls = traceback_details[-4:]
                else:
                    last_calls = traceback_details
                formatted_traceback = ''.join(traceback.format_list(last_calls))
                data = f"Type: {etype.__name__}, Message: " \
                       f"{value}\n" \
                       f"Traceback:\n{formatted_traceback}"
                logger.error(data)
                logger.log(level, "Exception: {}".format(str(message)), exc_info=True)
                print(data)
            else:
                # any other messages
                print("Log: {}".format(message))
                logger.log(level, message)
        except Exception as e:
            pass

    def on_update(self, all=False):
        """
        Update debug windows

        :param all: update all debug windows
        """
        # not_realtime = ['context']
        not_realtime = []
        for id in self.workers:
            if id in self.active and self.active[id]:
                if all or id not in not_realtime:
                    self.workers[id].update()

    def begin(self, id):
        """
        Begin debug data

        :param id: debug id
        """
        self.window.ui.debug[id].setModel(self.models[id])

        # set header
        self.window.ui.debug[id].header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.window.ui.debug[id].header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.window.ui.debug[id].header().setStretchLastSection(False)

        if id not in self.counters or self.counters[id] != self.models[id].rowCount():
            self.models[id].removeRows(0, self.models[id].rowCount())
            self.initialized[id] = False
        self.idx[id] = 0

    def end(self, id):
        """
        End debug data

        :param id: debug id
        """
        self.counters[id] = self.idx[id]
        self.initialized[id] = True

    def add(self, id, k, v):
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

    def create_model(self, parent):
        """
        Create list model

        :param parent: parent widget
        :return: model instance
        :rtype: QStandardItemModel
        """
        model = QStandardItemModel(0, 2, parent)
        model.setHeaderData(self.DBG_KEY, Qt.Horizontal, "Key")
        model.setHeaderData(self.DBG_VALUE, Qt.Horizontal, "Value")
        return model
