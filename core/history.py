#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Created Date: 2023.04.09 20:00:00                  #
# ================================================== #

import datetime
import os


class History:
    DIRNAME = "history"

    def __init__(self, config):
        """
        History

        :param config: Config
        """
        self.config = config

        if not self.config.initialized:
            self.config.init()

        self.path = os.path.join(self.config.path, self.DIRNAME)

    def save(self, text):
        """
        Save text to history

        :param text: Text
        """
        name = datetime.date.today().strftime("%Y_%m_%d") + ".txt"
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        if os.path.exists(self.path):
            f = os.path.join(self.path, name)
            with open(f, 'a', encoding="utf-8") as file:
                prefix = ""
                if self.config.data['store_history_time']:
                    prefix = datetime.datetime.now().strftime("%H:%M:%S") + ": "
                file.write(prefix + text + "\n")
                file.close()
