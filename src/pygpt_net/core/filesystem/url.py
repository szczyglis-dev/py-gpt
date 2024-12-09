#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.09 03:00:00                  #
# ================================================== #

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

class Url:
    def __init__(self, window=None):
        """
        Filesystem URL handler

        :param window: Window instance
        """
        self.window = window

    def handle(self,  url: QUrl):
        """
        Handle URL

        :param url: url
        """
        extra_schemes = [
            'extra-audio-read',
            'extra-code-copy',
            'extra-copy',
            'extra-delete',
            'extra-edit',
            'extra-join',
            'extra-replay',
        ]

        # JS bridge
        if url.toString().startswith('bridge://open_find'):
            pid = int(url.toString().split(':')[2])
            if pid in self.window.ui.nodes['output']:
                self.window.ui.nodes['output'][pid].find_open()
            return
        elif url.toString() == 'bridge://escape':
            self.window.controller.access.on_escape()
            return
        elif url.toString() == 'bridge://focus':
            pid = self.window.controller.ui.tabs.get_current_pid()
            if pid in self.window.ui.nodes['output']:
                self.window.ui.nodes['output'][pid].on_focus_js()

        # -------------

        # local file
        if not url.scheme().startswith('http') and url.scheme() not in extra_schemes:
            self.window.controller.files.open(url.toLocalFile())

        # extra actions
        elif url.scheme() == 'extra-delete':  # ctx item delete
            id = url.toString().split(':')[1]
            self.window.controller.ctx.extra.delete_item(int(id))
        elif url.scheme() == 'extra-edit':  # ctx item edit
            id = url.toString().split(':')[1]
            self.window.controller.ctx.extra.edit_item(int(id))
        elif url.scheme() == 'extra-copy':  # ctx item copy
            id = url.toString().split(':')[1]
            self.window.controller.ctx.extra.copy_item(int(id))
        elif url.scheme() == 'extra-replay':  # ctx regen response
            id = url.toString().split(':')[1]
            self.window.controller.ctx.extra.replay_item(int(id))
        elif url.scheme() == 'extra-audio-read':  # ctx audio read
            id = url.toString().split(':')[1]
            self.window.controller.ctx.extra.audio_read_item(int(id))
        elif url.scheme() == 'extra-join':  # ctx join
            id = url.toString().split(':')[1]
            self.window.controller.ctx.extra.join_item(int(id))
        elif url.scheme() == 'extra-code-copy':  # copy code block
            id = url.toString().split(':')[1]
            self.window.controller.ctx.extra.copy_code_block(int(id))

        else:
            # external link
            QDesktopServices.openUrl(url)
