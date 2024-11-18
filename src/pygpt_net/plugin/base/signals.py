#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.16 05:00:00                  #
# ================================================== #

from PySide6.QtCore import QObject, Signal

class BaseSignals(QObject):
    finished = Signal(object, object, dict)  # response dict, ctx, extra_data
    finished_more = Signal(list, object, dict)  # responses list, ctx, extra_data
    debug = Signal(object)
    destroyed = Signal()
    error = Signal(object)
    log = Signal(object)
    started = Signal()
    status = Signal(object)
    stopped = Signal()
