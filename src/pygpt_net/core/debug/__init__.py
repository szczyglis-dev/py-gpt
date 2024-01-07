#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.07 06:00:00                  #
# ================================================== #

import os
import sys
import traceback
import logging

from pathlib import Path

from pygpt_net.config import Config


class Debug:
    def __init__(self, window=None):
        """
        Debug core

        :param window: Window instance
        """
        self.window = window

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

    def begin(self, id):
        """
        Begin debug data

        :param id: debug id
        """
        self.window.controller.dialogs.debug.begin(id)

    def end(self, id):
        """
        End debug data

        :param id: debug id
        """
        self.window.controller.dialogs.debug.end(id)

    def add(self, id, k, v):
        """
        Append debug entry

        :param id: debug id
        :param k: key
        :param v: value
        """
        self.window.controller.dialogs.debug.add(id, k, v)
