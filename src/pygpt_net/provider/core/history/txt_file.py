#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.19 05:00:00                  #
# ================================================== #

import datetime
import os

from pygpt_net.item.ctx import CtxItem
from pygpt_net.provider.core.history.base import BaseProvider
from .patch import Patch


class TxtFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(TxtFileProvider, self).__init__(window)
        self.window = window
        self.patcher = Patch(window)
        self.id = "txt_file"
        self.type = "history"

    def install(self):
        """
        Install provider data
        """
        history_dir = self.window.core.config.get_user_dir('history')
        if not os.path.exists(history_dir):
            os.mkdir(history_dir)

    def append(self, ctx: CtxItem, mode: str):
        """
        Append text to file

        :param ctx: CtxItem instance
        :param mode: mode (input | output)
        """
        text = ""
        ts = 0
        if mode == "input":
            text = ctx.input
            ts = ctx.input_timestamp
        elif mode == "output":
            text = ctx.output
            ts = ctx.output_timestamp

        # check if text is empty
        if text is None or text.strip() == "":
            return

        path = self.window.core.config.get_user_dir('history')
        name = datetime.datetime.fromtimestamp(ts).strftime("%Y_%m_%d") + ".txt"

        # check directory
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except Exception as e:
                self.window.core.debug.log(e)
                print("Error creating history directory: " + str(e))

        # append to file
        if os.path.exists(path):
            f = os.path.join(path, name)
            try:
                with open(f, 'a', encoding="utf-8") as file:
                    prefix = ""
                    if self.window.core.config.get('store_history_time'):
                        prefix = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S") + ": "
                    file.write(prefix + text + "\n")
            except Exception as e:
                self.window.core.debug.log(e)
                print("Error appending to history: " + str(e))

    def truncate(self):
        """Delete all"""
        path = self.window.core.config.get_user_dir('history')
        try:
            if not os.path.exists(path):
                return
            for f in os.listdir(path):
                os.remove(os.path.join(path, f))
        except Exception as e:
            self.window.core.debug.log(e)
