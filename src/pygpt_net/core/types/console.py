#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 16:40:00                  #
# ================================================== #

import os
import sys


def _ansi_enabled() -> bool:
    """Return True when ANSI escape sequences can be safely written to stdout.

    Unix terminals normally support ANSI directly. On Windows, explicitly
    enable Virtual Terminal Processing for the current console. If stdout is
    redirected or the host console does not support VT sequences, return False
    so callers get plain text instead of visible ``[1m`` escape fragments.
    """
    try:
        if not sys.stdout or not sys.stdout.isatty():
            return False
    except Exception:
        return False

    if os.name != "nt":
        return True

    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
        kernel32.GetStdHandle.restype = wintypes.HANDLE
        kernel32.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel32.GetConsoleMode.restype = wintypes.BOOL
        kernel32.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel32.SetConsoleMode.restype = wintypes.BOOL

        STD_OUTPUT_HANDLE = ctypes.c_uint32(-11).value
        stdout_handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        if not stdout_handle:
            return False

        mode = wintypes.DWORD()
        if not kernel32.GetConsoleMode(stdout_handle, ctypes.byref(mode)):
            return False

        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        if mode.value & ENABLE_VIRTUAL_TERMINAL_PROCESSING:
            return True
        return bool(kernel32.SetConsoleMode(
            stdout_handle,
            mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING,
        ))
    except Exception:
        return False


_ANSI = _ansi_enabled()


class Color:
    BOLD = '\033[1m' if _ANSI else ''
    ENDC = '\033[0m' if _ANSI else ''
    FAIL = '\033[91m' if _ANSI else ''
    HEADER = '\033[95m' if _ANSI else ''
    OKBLUE = '\033[94m' if _ANSI else ''
    OKCYAN = '\033[96m' if _ANSI else ''
    OKGREEN = '\033[92m' if _ANSI else ''
    UNDERLINE = '\033[4m' if _ANSI else ''
    WARNING = '\033[93m' if _ANSI else ''
