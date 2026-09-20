#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# ================================================== #

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from .web_link import WebLinkResolver


class Url:
    def __init__(self, window=None):
        """Filesystem URL handler."""
        self.window = window
        self.resolver = WebLinkResolver(window)

    def handle(self, url: QUrl, ctx=None):
        """Handle URL, bridge action or local file."""
        link = self.resolver.resolve(url, ctx=ctx)
        if not link.original:
            return

        # All bridge parsing/unwrapping is centralized in WebLinkResolver.
        if link.is_bridge:
            action = link.bridge_action
            if action == "open_find":
                try:
                    pid = int(link.bridge_payload)
                except (TypeError, ValueError):
                    return
                if pid in self.window.ui.nodes['output']:
                    self.window.ui.nodes['output'][pid].find_open()
                return
            if action == "escape":
                self.window.controller.access.on_escape()
                return
            if action == "focus":
                pid = self.window.controller.ui.tabs.get_current_pid()
                if pid in self.window.ui.nodes['output']:
                    self.window.ui.nodes['output'][pid].on_focus_js()
                return
            if action == "play_video":
                target = link.local_path or link.target or link.bridge_payload
                if target:
                    self.window.controller.media.play_video(target)
                return
            if action == "open_image":
                target = link.local_path or link.target or link.bridge_payload
                if target:
                    self.window.tools.get("viewer").open_preview(target)
                return
            if action == "download":
                if link.local_path:
                    self.window.controller.files.download_local(link.local_path)
                elif link.target:
                    # Keep remote bridge targets inside the regular URL flow;
                    # never leak bridge://... to the OS/browser.
                    self.window.controller.dialogs.info.open_url(link.target)
                return
            return

        target = link.target or link.original
        scheme = QUrl(target, QUrl.TolerantMode).scheme().lower()

        if scheme == 'extra-delete':
            id_ = target.split(':')[1]
            self.window.controller.ctx.extra.delete_item(int(id_))
            return
        if scheme == 'extra-delete-chain':
            try:
                payload = target.split(':', 1)[1]
                start_id, end_id = payload.split(',', 1)
                self.window.controller.ctx.extra.delete_item_chain(int(start_id), int(end_id))
            except (IndexError, TypeError, ValueError):
                pass
            return
        if scheme == 'extra-edit':
            id_ = target.split(':')[1]
            self.window.controller.ctx.extra.edit_item(int(id_))
            return
        if scheme == 'extra-copy':
            id_ = target.split(':')[1]
            self.window.controller.ctx.extra.copy_item(int(id_))
            return
        if scheme == 'extra-replay':
            id_ = target.split(':')[1]
            self.window.controller.ctx.extra.replay_item(int(id_))
            return
        if scheme == 'extra-audio-read':
            id_ = target.split(':')[1]
            self.window.controller.ctx.extra.audio_read_item(int(id_))
            return
        if scheme == 'extra-code-copy':
            id_ = target.split(':')[1]
            self.window.controller.ctx.extra.copy_code_block(int(id_))
            return

        if link.kind == "local" and link.local_path:
            self.window.controller.files.open(link.local_path)
            return
        if link.kind == "web":
            self.window.controller.dialogs.info.open_url(link.target)
            return
        if link.can_open_external and link.target:
            QDesktopServices.openUrl(QUrl(link.target, QUrl.TolerantMode))
