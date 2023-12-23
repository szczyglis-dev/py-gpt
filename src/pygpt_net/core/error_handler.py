#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 05:00:00                  #
# ================================================== #

import os
import sys
import traceback
import logging
from pathlib import Path
from PySide6.QtCore import QtMsgType, qInstallMessageHandler

from .config import Config


class ErrorHandler:
    def __init__(self, window=None):
        """
        Error handler

        :param window: Window instance
        """
        self.window = window

    @staticmethod
    def init(level=logging.ERROR):
        """
        Initialize error handler
        """
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=str(Path(os.path.join(Path.home(), '.config', Config.CONFIG_DIR, 'error.log'))),
            filemode='a'
        )

        def qt_message_handler(mode, context, message):
            if mode == QtMsgType.QtDebugMsg:
                msg_type = 'DEBUG'
            elif mode == QtMsgType.QtInfoMsg:
                msg_type = 'INFO'
            elif mode == QtMsgType.QtWarningMsg:
                msg_type = 'WARNING'
            elif mode == QtMsgType.QtCriticalMsg:
                msg_type = 'CRITICAL'
            elif mode == QtMsgType.QtFatalMsg:
                msg_type = 'FATAL'
            else:
                msg_type = 'UNKNOWN'

            logging.log(getattr(logging, msg_type), f"{msg_type}: {message} (in {context.file}:{context.line})")

        qInstallMessageHandler(qt_message_handler)

        def handle_exception(exc_type, value, tb):
            logging.error("Uncaught exception:", exc_info=(exc_type, value, tb))
            traceback.print_exception(exc_type, value, tb)

        sys.excepthook = handle_exception

    def log(self, error):
        """
        Handle error

        :param error: error object
        """
        # if error is only string then log and print it
        if not isinstance(error, Exception):
            print("Error: {}".format(str(error)))
            data = f"MSG: {error}\n"
            print(data)
            logging.error(data)
            return

        etype, value, tb = sys.exc_info()
        traceback_details = traceback.extract_tb(tb)
        if len(traceback_details) >= 4:
            last_calls = traceback_details[-4:]
        else:
            last_calls = traceback_details
        formatted_traceback = ''.join(traceback.format_list(last_calls))
        data = f"Type: {etype.__name__}, MSG: " \
            f"{value}\n" \
            f"Traceback:\n{formatted_traceback}"

        logging.error(data)
        print("Error: {}".format(str(error)))
        print(data)
