#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.25 21:00:00                  #
# ================================================== #


class AttachmentsDebug:
    def __init__(self, window=None):
        """
        Attachments debug

        :param window: Window instance
        """
        self.window = window
        self.id = 'attachments'

    def update(self):
        """Update debug window."""
        self.window.core.debug.begin(self.id)

        modes = ['chat', 'completion', 'img', 'vision', 'langchain', 'assistant']
        for mode in modes:
            self.window.core.debug.add(self.id, '[mode]', mode)
            attachments = self.window.core.attachments.get_all(mode)
            for key in list(attachments):
                prefix = "[{}] ".format(key)
                attachment = attachments[key]
                self.window.core.debug.add(self.id, prefix + 'ID', str(key))
                self.window.core.debug.add(self.id, 'id', str(attachment.id))
                self.window.core.debug.add(self.id, 'name', str(attachment.name))
                self.window.core.debug.add(self.id, 'path', str(attachment.path))
                self.window.core.debug.add(self.id, 'remote', str(attachment.remote))
                self.window.core.debug.add(self.id, 'send', str(attachment.send))

        self.window.core.debug.end(self.id)
