#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 08:00:00                  #
# ================================================== #

import json
import os
import uuid


class Assistants:
    def __init__(self, config=None):
        """
        Assistants

        :param config: config object
        """
        self.config = config

    def get_by_idx(self, idx):
        """
        Returns assistant by index

        :param idx: index
        :param mode: mode
        :return: assistant ID
        """
        assistants = self.get_all()
        return list(assistants.keys())[idx]

    def get_by_id(self, id):
        """
        Returns assistant by ID

        :param id: ID
        :return: assistant
        """
        assistants = self.get_all()
        return assistants[id]

    def get_all(self):
        """
        Returns assistants

        :return: assistants dict
        """
        return self.config.assistants

    def rename_file(self, assistant_id, file_id, name):
        """
        Renames uploaded remote file name

        :param assistant_id: assistant_id
        :param file_id: file_id
        :param name: new name
        """
        assistant = self.get_by_id(assistant_id)
        if assistant is None:
            return
        files = assistant['files']
        if file_id in files:
            files[file_id]['name'] = name
            self.config.save_assistants()
