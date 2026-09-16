#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.16 00:00:00                  #
# ================================================== #

"""Small Qt helpers that are safe to import during application bootstrap."""


def is_deleted_qt_object_error(exc: BaseException) -> bool:
    """Return True when PySide reports that the signal/QObject was deleted."""
    if not isinstance(exc, RuntimeError):
        return False
    msg = str(exc).lower()
    return (
        "signal source has been deleted" in msg
        or "internal c++ object" in msg and "already deleted" in msg
        or "wrapped c/c++ object" in msg and "has been deleted" in msg
        or "wrapped c/c++ object" in msg and "already deleted" in msg
    )


def safe_emit(source, signal_name: str, *args) -> bool:
    """Emit a Qt signal unless its QObject has already been destroyed.

    Only the well-known PySide deleted-object race is suppressed. Other
    RuntimeError instances are re-raised so genuine application errors are not
    hidden by this helper.
    """
    if source is None:
        return False
    try:
        signal = getattr(source, signal_name, None)
        emit = getattr(signal, "emit", None)
        if not callable(emit):
            return False
        emit(*args)
        return True
    except RuntimeError as exc:
        if is_deleted_qt_object_error(exc):
            return False
        raise
