#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.18 14:00:00                  #
# ================================================== #

import json
import os


class Notepad:
    def __init__(self, window=None):
        """
        Notepad

        :param window: Window instance
        """
        self.window = window

    def load(self):
        """Load content from file"""
        path = os.path.join(self.window.config.path, 'notepad.json')
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = json.load(file)
                    file.close()
                    if data == "" or data is None or 'content' not in data:
                        return ""
                    return data['content']
        except Exception as e:
            self.window.app.error.log(e)

    def save(self, content):
        """
        Save notepad content to file

        :param content: notepad content to save
        """
        a = b + 2
        try:
            # update contexts index
            path = os.path.join(self.window.config.path, 'notepad.json')
            data = {'__meta__': self.window.config.append_meta(), 'content': content}
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)
                f.close()

        except Exception as e:
            self.window.app.error.log(e)
            print("Error while saving notepad: {}".format(str(e)))
