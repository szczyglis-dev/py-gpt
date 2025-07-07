#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

import datetime
import os
from typing import List

from pygpt_net.item.ctx import CtxItem
from pygpt_net.provider.core.history.txt_file import TxtFileProvider


class History:

    def __init__(self, window):
        """
        History core

        :param window: Window instance
        """
        self.window = window
        self.provider = TxtFileProvider(window)
        self.path = None

    def install(self):
        """Install provider data"""
        self.provider.install()

    def append(self, ctx: CtxItem, mode: str):
        """
        Append text to history

        :param ctx: CtxItem instance
        :param mode: mode (input | output)
        """
        self.provider.append(ctx, mode)

    def truncate(self):
        """Truncate history"""
        # delete all txt history files from history dir
        self.provider.truncate()

    def remove_items(self, items: List[CtxItem]):
        """
        Remove items from history (txt files)

        :param items: list of ctx items to remove
        """
        path = self.window.core.config.get_user_dir('history')
        if not os.path.exists(path):
            return
        for item in items:
            self.remove_entry(item.input, item.input_timestamp)
            self.remove_entry(item.output, item.output_timestamp)

    def remove_entry(self, text: str, ts: int):
        """
        Remove ctx item text from history

        :param text: text to remove from txt file
        :param ts: timestamp from ctx
        """
        if text is None or text.strip() == "":
            return

        # remove entry from txt file in history dir
        dir = self.window.core.config.get_user_dir('history')
        filename = datetime.datetime.fromtimestamp(ts).strftime("%Y_%m_%d") + ".txt"
        prefix = datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S") + ": "
        path = os.path.join(dir, filename)
        if not os.path.exists(path):
            return
        try:
            data = prefix + text
            with open(path, "r", encoding="utf-8") as f:
                txt = f.read()
                content = txt.replace(data.strip() + "\n", "")
                if content == txt:  # if nothing was removed (timestamp mismatch or missing)
                    # try without prefix
                    content = content.replace(text.strip() + "\n", "")
            if content.strip() == "":
                os.remove(path)  # remove file if empty
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content.strip() + "\n")
        except Exception as e:
            print(e)
