#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 22:00:00                  #
# ================================================== #

import json
import os


class Notepad:
    def __init__(self, config=None):
        """
        Notepad

        :param config: config object
        """
        self.config = config

    def load(self):
        """Loads content from file"""
        path = os.path.join(self.config.path, 'notepad.json')
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding="utf-8") as file:
                    data = json.load(file)
                    file.close()
                    if data == "" or data is None or 'content' not in data:
                        return ""
                    return data['content']
        except Exception as e:
            print(e)

    def save(self, content):
        """
        Saves notepad content to file
        """
        try:
            # update contexts index
            path = os.path.join(self.config.path, 'notepad.json')
            data = {'__meta__': self.config.append_meta(), 'content': content}
            dump = json.dumps(data, indent=4)
            with open(path, 'w', encoding="utf-8") as f:
                f.write(dump)
                f.close()

        except Exception as e:
            print("Error while saving notepad: {}".format(str(e)))
