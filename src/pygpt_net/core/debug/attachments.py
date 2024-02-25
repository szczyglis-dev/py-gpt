#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.25 22:00:00                  #
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

        modes = ['chat', 'completion', 'img', 'vision', 'langchain', 'assistant', 'llama_index', 'agent']
        for mode in modes:
            self.window.core.debug.add(self.id, '[' + mode + ']', '')
            attachments = self.window.core.attachments.get_all(mode)
            for key in list(attachments):
                attachment = attachments[key]
                data = {
                    'path': attachment.path,
                    'id': attachment.id,
                    'name': attachment.name,
                    'remote': attachment.remote,
                    'send': attachment.send,
                    'key': key,
                    'mode': mode,
                }
                self.window.core.debug.add(self.id, attachment.name, str(data))

        self.window.core.debug.end(self.id)
