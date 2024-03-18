#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.18 10:00:00                  #
# ================================================== #

class Video:
    def __init__(self, window=None):
        """
        Debug controller

        :param window: Window instance
        """
        self.window = window
        self.is_player = False  # logger window opened

    def update(self):
        """Update debug"""
        self.update_menu()

    def update_menu(self):
        """Update debug menu"""
        if self.is_player:
            self.window.ui.menu['video.player'].setChecked(True)
        else:
            self.window.ui.menu['video.player'].setChecked(False)

    def play(self, path: str):
        """
        Open and play video file

        :param path: video file path
        """
        self.window.ui.dialogs.open('video_player', width=800, height=600)
        self.window.video_player.force_resize()
        self.is_player = True
        self.update()
        self.window.video_player.open(path)

    def open_player(self):
        """Open player"""
        self.window.ui.dialogs.open('video_player', width=800, height=600)
        self.window.video_player.force_resize()
        self.is_player = True
        self.update()

    def close_player(self):
        """Close logger player"""
        self.on_close()
        self.window.ui.dialogs.close('video_player')
        self.is_player = False
        self.update()

    def on_close(self):
        """On player window close"""
        self.is_player = False
        self.update()
        self.window.video_player.on_close()

    def toggle_player(self):
        """Toggle player window"""
        if self.is_player:
            self.close_player()
        else:
            self.open_player()

    def show_hide_player(self, show: bool = True):
        """
        Show/hide player window

        :param show: show/hide
        """
        if show:
            self.open_player()
        else:
            self.close_player()
