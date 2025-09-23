#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.24 23:00:00                  #
# ================================================== #

from __future__ import annotations
from typing import Protocol, Optional, Any


class Logger(Protocol):
    """Minimal logger protocol used across the flow core."""
    def debug(self, msg: str, **kwargs: Any) -> None: ...
    def info(self, msg: str, **kwargs: Any) -> None: ...
    def warning(self, msg: str, **kwargs: Any) -> None: ...
    def error(self, msg: str, **kwargs: Any) -> None: ...


class NullLogger:
    """No-op logger."""
    def debug(self, msg: str, **kwargs: Any) -> None: pass
    def info(self, msg: str, **kwargs: Any) -> None: pass
    def warning(self, msg: str, **kwargs: Any) -> None: pass
    def error(self, msg: str, **kwargs: Any) -> None: pass


class StdLogger:
    """Simple stdout logger; can be replaced by external one from your app."""
    def __init__(self, prefix: str = "[flow]"):
        self.prefix = prefix

    def _fmt(self, level: str, msg: str) -> str:
        return f"{self.prefix} {level.upper()}: {msg}"

    def debug(self, msg: str, **kwargs: Any) -> None:
        print(self._fmt("debug", msg))

    def info(self, msg: str, **kwargs: Any) -> None:
        print(self._fmt("info", msg))

    def warning(self, msg: str, **kwargs: Any) -> None:
        print(self._fmt("warning", msg))

    def error(self, msg: str, **kwargs: Any) -> None:
        print(self._fmt("error", msg))