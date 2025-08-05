#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.05 00:00:00                  #
# ================================================== #
import gc
import os
import sys
import threading
import time
import traceback
import logging

from pathlib import Path
from typing import Any, Tuple

import psutil

from pygpt_net.config import Config
from pygpt_net.core.types.console import Color

class Debug:
    def __init__(self, window=None):
        """
        Debug core

        :param window: Window instance
        """
        self.window = window
        self.pause_idx = 1

    @staticmethod
    def init(level: int = logging.ERROR):
        """
        Initialize logger and error handler

        :param level: log level (default: ERROR)
        """
        if not Config.prepare_workdir():
            os.makedirs(Config.prepare_workdir())

        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename=str(Path(os.path.join(Config.prepare_workdir(), 'app.log'))),
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

    def update_logger_path(self):
        """Update log file path"""
        path = os.path.join(Config.prepare_workdir(), 'app.log')
        level = self.get_log_level()
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
        file_handler = logging.FileHandler(filename=Path(path), mode='a', encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.setLevel(level)
        logger.addHandler(file_handler)

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

    def info(self, message: Any = None, console: bool = True):
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

    def debug(self, message: Any = None, console: bool = True):
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

    def warning(self, message: Any = None, console: bool = True):
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

    def error(self, message: Any = None, console: bool = True):
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

    def log(self, message: Any = None, level: int = logging.ERROR, console: bool = True):
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
                is_sys, data = self.parse_exception(message)
                msg = "Exception: {}".format(str(message))
                if not is_sys:
                    msg += "\n{}".format(data)
                logger.log(level, msg, exc_info=is_sys)
                if self.has_level(level) and console and data:
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
                # append thread ID
                thread_suffix = ""
                if not threading.current_thread() is threading.main_thread():
                    thread_suffix = " [THREAD: {}]".format(threading.current_thread().ident)
                self.window.logger_message.emit(str(message) + thread_suffix)
        except Exception as e:
            pass

    def parse_exception(self, e: Any = None, limit: int = 4) -> Tuple[bool, str]:
        """
        Parse exception traceback

        :param e: exception
        :param limit: limit of traceback
        :return: sys error, parsed exception as string
        """
        is_sys = False
        type_name = ""
        etype, value, tb = sys.exc_info()  # from sys by default
        if etype is None and e is not None:
            tb = e.__traceback__  # from exception
            type_name = type(e).__name__
            value = str(e)
        else:
            if etype is not None:
                is_sys = True
                type_name = etype.__name__

        # traceback
        traceback_details = traceback.extract_tb(tb)
        if len(traceback_details) >= limit:
            last_calls = traceback_details[-limit:]
        else:
            last_calls = traceback_details
        formatted_traceback = ""
        if last_calls:
            formatted_traceback = "".join(traceback.format_list(last_calls))

        # parse data
        data = ""
        if type_name:
            data += "Type: {}".format(type_name)
        if value:
            data += "Message: {}".format(value)
        if formatted_traceback:
            data += "\nTraceback: {}".format(formatted_traceback)

        return is_sys, data

    def parse_alert(self, msg: Any) -> str:
        """
        Parse alert message

        :param msg: message to parse
        :return: parsed message
        """
        if isinstance(msg, Exception):
            is_sys, data = self.parse_exception(msg)
            return "Exception: {}\n{}".format(str(msg), data)
        return str(msg)

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

    def add(self, id: str, k: str, v: Any):
        """
        Append debug entry (debug window)

        :param id: debug id
        :param k: key
        :param v: value
        """
        self.window.controller.dialogs.debug.add(id, k, v)

    def print_memory_usage(self, label=""):
        """
        Print memory usage of the current process

        :param label: label for memory usage
        """
        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / (1024 * 1024)
        print(f"{label} Memory Usage: {mem_mb:.2f} MB")

    def mem(self, label: str = ""):
        """
        Print memory usage and collect garbage

        :param label: label for memory usage
        """
        print("------------------------------------")
        print(f"{Color.BOLD}{label} Memory Usage{Color.ENDC}")
        print("------------------------------------")

        self.print_memory_usage(label)

        from pympler import asizeof  # pip install pympler

        total_bytes = asizeof.asizeof(self.window.controller.chat.render.web_renderer.pids)
        total_mb = total_bytes / (1024 * 1024)
        print(f"PIDS: {total_mb:.4f} MB")

        total_bytes = asizeof.asizeof(self.window.core.ctx.meta)
        total_mb = total_bytes / (1024 * 1024)
        print(f"CTX META: {total_mb:.4f} MB")

        total_bytes = asizeof.asizeof(self.window.core.ctx.get_items())
        total_mb = total_bytes / (1024 * 1024)
        print(f"CTX ITEMS: {total_mb:.4f} MB")

        unreachable_objects = gc.collect()
        print(f"[GC] Unreachable: {unreachable_objects}")
        """
        all_objects = gc.get_objects()
        print(f"[GC] Tracked: {len(all_objects)}")
        """

    def pause(self, *args):
        """
        Pause execution

        Pause execution and print traceback.

        :param args: objects to dump
        """
        dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        thread_info = "[MAIN THREAD]" if threading.current_thread() is threading.main_thread() \
            else f"[THREAD: {threading.current_thread().ident}]"
        print(f"\n{Color.FAIL}{Color.BOLD}<DEBUG: PAUSED> #{self.pause_idx} {dt}{Color.ENDC}")
        print(f"\n{Color.BOLD}{thread_info}{Color.ENDC}")
        print("------------------------------>")
        self.pause_idx += 1

        # dump args
        for index, arg in enumerate(args):
            print(f"\n{Color.BOLD}Dump {index + 1}:{Color.ENDC}")
            print(f"{Color.BOLD}Type: {type(arg)}{Color.ENDC}")
            print(arg)

        if args:
            print("\n\n")

        traceback.print_stack()

        input(f"<------------------------------\n\n{Color.OKGREEN}Paused. Press Enter to continue...{Color.ENDC}")
        print(f"------------------------------\n{Color.OKGREEN}{Color.BOLD}<RESUMED>{Color.ENDC}\n")
