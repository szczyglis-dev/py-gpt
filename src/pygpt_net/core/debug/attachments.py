#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.14 20:00:00                  #
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
        debug = self.window.core.debug
        modes = self.window.core.modes
        attachments_core = self.window.core.attachments

        debug.begin(self.id)

        for mode in modes.all:
            debug.add(self.id, f'[{mode}]', '')
            attachments = attachments_core.get_all(mode)
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
                    'type': attachment.type,
                    'consumed': attachment.consumed,
                    'extra': attachment.extra,
                }
                debug.add(self.id, attachment.name, str(data))

        debug.end(self.id)
