#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.22 02:00:00                  #
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
    def init(level: int = logging.ERROR):
        """
        Initialize error handler

        :param level: log level (default: ERROR)
        """
        if not os.path.exists(os.path.join(Path.home(), '.config', Config.CONFIG_DIR)):
            os.makedirs(os.path.join(Path.home(), '.config', Config.CONFIG_DIR))

        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=str(Path(os.path.join(Path.home(), '.config', Config.CONFIG_DIR, 'app.log'))),
            filemode='a',
            encoding='utf-8',
        )

        def handle_exception(exc_type, value, tb):
            """
            Handle uncaught exception

            :param exc_type: exception type
            :param value: exception value
            :param tb: traceback
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

    def switch_log_level(self, level: int):
        """
        Set log level

        :param level: log level
        """
        logging.getLogger().setLevel(level)

    def get_log_level(self) -> int:
        """
        Get log level

        :return: log level
        """
        return logging.getLogger().getEffectiveLevel()

    def get_log_level_name(self) -> str:
        """
        Get current log level name

        :return: log level name
        """
        return self.get_log_level_name_by_id(
            self.get_log_level()
        )

    def get_log_level_name_by_id(self, id: int) -> str:
        """
        Get log level name by id

        :param id: log level id
        :return: log level name
        """
        if id == logging.ERROR:
            return "error"
        elif id == logging.WARNING:
            return "warning"
        elif id == logging.INFO:
            return "info"
        elif id == logging.DEBUG:
            return "debug"
        else:
            return "unknown"

    def info(self, message: any = None, console: bool = True):
        """
        Handle info message

        :param message: message to log
        :param console: print to console

        """
        self.log(
            message,
            logging.INFO,
            console=console,
        )

    def debug(self, message: any = None, console: bool = True):
        """
        Handle debug message

        :param message: message to log
        :param console: print to console
        """
        self.log(
            message,
            logging.DEBUG,
            console=console,
        )

    def warning(self, message: any = None, console: bool = True):
        """
        Handle warning message

        :param message: message to log
        :param console: print to console
        """
        self.log(
            message,
            logging.WARNING,
            console=console,
        )

    def error(self, message: any = None, console: bool = True):
        """
        Handle error message

        :param message: message to log
        :param console: print to console
        """
        self.log(
            message,
            logging.ERROR,
            console=console,
        )

    def log(self, message: any = None, level: int = logging.ERROR, console: bool = True):
        """
        Handle logger message (by level), default level is ERROR

        :param message: message to log
        :param level: logging level (default: ERROR)
        :param console: print to console if True
        """
        if message is None:
            return

        logger = logging.getLogger()

        try:
            # string message
            if isinstance(message, str):
                logger.log(level, message)
                if self.has_level(level) and console:
                    print(message)

            # exception
            elif isinstance(message, Exception):
                data = self.parse_exception()
                msg = "Exception: {}".format(str(message))
                logger.log(level, msg, exc_info=True)
                if self.has_level(level) and console:
                    print(data)

            # other messages
            else:
                logger.log(level, message)
                if self.has_level(level) and console:
                    print(message)
        except Exception as e:
            pass

        try:
            # send to logger window
            if self.window is not None:
                self.window.logger_message.emit(message)
        except Exception as e:
            pass

    def parse_exception(self, limit: int = 4) -> str:
        """
        Parse exception traceback

        :param limit: limit of traceback
        :return: parsed exception as string
        """
        etype, value, tb = sys.exc_info()
        traceback_details = traceback.extract_tb(tb)
        if len(traceback_details) >= limit:
            last_calls = traceback_details[-limit:]
        else:
            last_calls = traceback_details
        formatted_traceback = ''.join(traceback.format_list(last_calls))
        data = f"Type: {etype.__name__}, Message: " \
               f"{value}\n" \
               f"Traceback:\n{formatted_traceback}"
        return data

    def has_level(self, level: int) -> bool:
        """
        Check if logging level is enabled

        :param level: logging level
        :return: True if enabled
        """
        return level >= logging.getLogger().getEffectiveLevel()

    def enabled(self) -> bool:
        """
        Check if debug is enabled

        :return: True if enabled
        """
        if self.window is not None and self.window.controller.debug.logger_enabled():
            return True
        if self.has_level(logging.DEBUG):
            return True
        return False

    def begin(self, id: str):
        """
        Begin debug data (debug window)

        :param id: debug id
        """
        self.window.controller.dialogs.debug.begin(id)

    def end(self, id: str):
        """
        End debug data (debug window)

        :param id: debug id
        """
        self.window.controller.dialogs.debug.end(id)

    def add(self, id: str, k: str, v: any):
        """
        Append debug entry (debug window)

        :param id: debug id
        :param k: key
        :param v: value
        """
        self.window.controller.dialogs.debug.add(id, k, v)
