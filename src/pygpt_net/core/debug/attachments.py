#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.05 12:00:00                  #
# ================================================== #
import os


class AttachmentsDebug:
    def __init__(self, window=None):
        """
        Attachments debug

        :param window: main window object
        """
        self.window = window
        self.id = 'attachments'

    def update(self):
        """Updates debug window."""
        self.window.debugger.begin(self.id)

        path = os.path.join(self.window.config.path, '', self.window.controller.attachment.attachments.config_file)
        self.window.debugger.add(self.id, 'File', path)

        modes = ['chat', 'completion', 'img', 'vision', 'langchain', 'assistant']
        for mode in modes:
            self.window.debugger.add(self.id, '[mode]', mode)
            attachments = self.window.controller.attachment.attachments.get_all(mode)
            for key in attachments:
                prefix = "[{}] ".format(key)
                attachment = attachments[key]
                self.window.debugger.add(self.id, prefix + 'ID', str(key))
                self.window.debugger.add(self.id, 'id', str(attachment.id))
                self.window.debugger.add(self.id, 'name', str(attachment.name))
                self.window.debugger.add(self.id, 'path', str(attachment.path))
                self.window.debugger.add(self.id, 'remote', str(attachment.remote))
                self.window.debugger.add(self.id, 'send', str(attachment.send))

        self.window.debugger.end(self.id)
