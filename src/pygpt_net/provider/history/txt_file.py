#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.31 04:00:00                  #
# ================================================== #

import datetime
import os

from pygpt_net.item.ctx import CtxItem
from pygpt_net.provider.history.base import BaseProvider


class TxtFileProvider(BaseProvider):
    def __init__(self, window=None):
        super(TxtFileProvider, self).__init__(window)
        self.window = window
        self.id = "txt_file"
        self.type = "history"
        self.dir_name = 'history'

    def install(self):
        """
        Install provider data
        """
        history_dir = os.path.join(self.window.core.config.path, self.dir_name)
        if not os.path.exists(history_dir):
            os.mkdir(history_dir)

    def append(self, ctx: CtxItem, mode: str):
        """
        Append text to file

        :param ctx: CtxItem instance
        :param mode: mode (input | output)
        """
        text = ""
        if mode == "input":
            text = ctx.input
        elif mode == "output":
            text = ctx.output

        # check if text is empty
        if text is None or text.strip() == "":
            return

        path = os.path.join(self.window.core.config.path, self.dir_name)
        name = datetime.date.today().strftime("%Y_%m_%d") + ".txt"

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
                        prefix = datetime.datetime.now().strftime("%H:%M:%S") + ": "
                    file.write(prefix + text + "\n")
            except Exception as e:
                self.window.core.debug.log(e)
                print("Error appending to history: " + str(e))

    def truncate(self):
        """Delete all"""
        path = os.path.join(self.window.core.config.path, self.dir_name)
        try:
            if not os.path.exists(path):
                return
            for f in os.listdir(path):
                os.remove(os.path.join(path, f))
        except Exception as e:
            self.window.core.debug.log(e)
