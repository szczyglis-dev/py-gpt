#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 22:00:00                  #
# ================================================== #

import datetime
import os.path
import shutil
from typing import Dict

from PySide6.QtGui import QAction, QIcon

from pygpt_net.tools.base import BaseTool
from pygpt_net.tools.media_player.ui.dialogs import VideoPlayer
from PySide6.QtWidgets import QMessageBox, QFileDialog

from pygpt_net.utils import trans

import pygpt_net.icons_rc


class MediaPlayer(BaseTool):
    def __init__(self, *args, **kwargs):
        """
        Media player

        :param window: Window instance
        """
        super(MediaPlayer, self).__init__(*args, **kwargs)
        self.id = "player"
        self.opened = False
        self.dialog = None

    def setup(self):
        """Setup media player"""
        if self.window.core.config.has("video.player.path"):
            path = self.window.core.config.get("video.player.path")
            if path:
                path = self.window.core.filesystem.to_workdir(path)
                if os.path.exists(path):
                    self.window.video_player.set_path(path)
        if self.window.core.config.has("video.player.volume"):
            self.window.video_player.adjust_volume(self.window.core.config.get("video.player.volume"))
        if self.window.core.config.has("video.player.volume.mute"):
            self.window.video_player.set_muted(self.window.core.config.get("video.player.volume.mute"))
        self.window.video_player.update()  # update player volume, slider, etc.

    def update(self):
        """Update menu"""
        self.update_menu()

    def update_menu(self):
        """Update menu"""
        """
        if self.opened:
            self.window.ui.menu['tools.media.player'].setChecked(True)
        else:
            self.window.ui.menu['tools.media.player'].setChecked(False)
        """

    def store_path(self, path: str):
        """
        Store current video path

        :param path: video file path
        """
        path = self.window.core.filesystem.make_local(path)
        self.window.core.config.set("video.player.path", path)

    def play(self, path: str):
        """
        Open and play video file

        :param path: video file path
        """
        self.window.ui.dialogs.open('video_player', width=800, height=600)
        self.window.video_player.force_resize()
        self.opened = True
        self.update()
        self.window.video_player.open(path)

    def open_file(self):
        """Open video file"""
        self.window.video_player.open_file()

    def grab_frame(self) -> str:
        """
        Grab frame

        :return: frame path
        """
        now = datetime.datetime.now()
        dt = now.strftime("%Y-%m-%d_%H-%M-%S")
        name = 'cap-' + dt
        path = os.path.join(self.window.controller.painter.common.get_capture_dir(), name + '.png')
        # TODO: implement grab screenshot
        return path

    def save_as_file(self):
        """Save video as file"""
        path = self.window.video_player.path
        if not path:
            QMessageBox.warning(self.window.video_player, "Save Error", "No video loaded.")
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self.window.video_player,
            "Save video As",
            path,
            "Video Files (*.mp4 *.avi *.mkv)",
        )
        if save_path and save_path != path:
            try:
                shutil.copy2(path, save_path)
                QMessageBox.information(
                    self.window.video_player,
                    "OK",
                    f"Video saved to: {save_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self.window.video_player,
                    "Error",
                    f"An error occurred while saving the video: {e}"
                )
    def open(self):
        """Open player window"""
        self.window.ui.dialogs.open('video_player', width=800, height=600)
        self.window.video_player.force_resize()
        self.opened = True
        self.update()

    def close(self):
        """Close player window"""
        self.on_close()
        self.window.ui.dialogs.close('video_player')
        self.opened = False
        self.update()

    def on_close(self):
        """On player window close"""
        self.opened = False
        self.update()
        self.window.video_player.on_close()

    def toggle(self):
        """Toggle player window"""
        if self.opened:
            self.close()
        else:
            self.open()

    def show_hide(self, show: bool = True):
        """
        Show/hide player window

        :param show: show/hide
        """
        if show:
            self.open()
        else:
            self.close()

    def setup_menu(self) -> Dict[str, QAction]:
        """
        Setup main menu

        :return dict with menu actions
        """
        actions = {}
        actions["media.player"] = QAction(
            QIcon(":/icons/video.svg"),
            trans("menu.tools.media.player"),
            self.window,
            checkable=False,
        )
        actions["media.player"].triggered.connect(
            lambda: self.toggle()
        )
        return actions

    def setup_dialogs(self):
        """Setup dialogs (static)"""
        self.dialog = VideoPlayer(self.window)
        self.dialog.setup()

    def get_lang_mappings(self) -> Dict[str, Dict]:
        """
        Get language mappings

        :return: dict with language mappings
        """
        return {
            'menu.text': {
                'tools.media.player': 'menu.tools.media.player',
            }
        }