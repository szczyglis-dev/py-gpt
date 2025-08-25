#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.25 18:00:00                  #
# ================================================== #

import os
import sys
import shutil
import subprocess

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

# QtDBus is optional and may not be available on all systems
try:
    from PySide6.QtDBus import QDBusInterface, QDBusConnection, QDBusMessage
    HAS_QT_DBUS = True
except Exception:
    HAS_QT_DBUS = False

IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

class Opener:
    # ===== public API =====
    @staticmethod
    def open_path(path: str, reveal: bool = False) -> bool:
        """
        Open file or directory in the system file manager or default application.

        :param path: Path to file or directory
        :param reveal: If True and path is a file, reveal it in the file manager
        :return: True if successful, False otherwise
        """
        p = os.path.abspath(path)

        if IS_WINDOWS:
            if reveal and os.path.isfile(p):
                return Opener._reveal_windows(p)
            if os.path.isdir(p):
                return Opener._open_dir_windows(p)
            return Opener._open_file_windows(p)

        if IS_MAC:
            if reveal and os.path.isfile(p):
                return Opener._reveal_mac(p)
            if os.path.isdir(p):
                return Opener._open_dir_mac(p)
            return Opener._open_file_mac(p)

        # Linux
        if reveal and os.path.isfile(p):
            if Opener._reveal_linux(p):
                return True
            # fallback:
            return Opener._open_dir_linux(os.path.dirname(p) or "/")
        if os.path.isdir(p):
            return Opener._open_dir_linux(p)
        return Opener._open_file_linux(p)

    # ===== Windows =====
    @staticmethod
    def _open_dir_windows(path: str) -> bool:
        """
        Open directory in Windows Explorer

        :param path: Path to directory
        :return: True if successful, False otherwise
        """
        try:
            os.startfile(path)
            return True
        except Exception:
            try:
                subprocess.Popen(["explorer", path])
                return True
            except Exception:
                return False

    @staticmethod
    def _reveal_windows(path: str) -> bool:
        """
        Reveal file in Windows Explorer

        :param path: Path to file
        :return: True if successful, False otherwise
        """
        try:
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            return True
        except Exception:
            return Opener._open_dir_windows(os.path.dirname(path) or "C:\\")

    @staticmethod
    def _open_file_windows(path: str) -> bool:
        """
        Open file with default application

        :param path: Path to file
        :return: True if successful, False otherwise
        """
        try:
            os.startfile(path)
            return True
        except Exception:
            # Qt
            return QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    # ===== macOS =====
    @staticmethod
    def _open_dir_mac(path: str) -> bool:
        """
        Open directory in Finder

        :param path: Path to directory
        :return: True if successful, False otherwise
        """
        try:
            subprocess.Popen(["open", path])
            return True
        except Exception:
            return QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    @staticmethod
    def _reveal_mac(path: str) -> bool:
        """
        Reveal file in Finder

        :param path: Path to file
        :return: True if successful, False otherwise
        """
        try:
            subprocess.Popen(["open", "-R", path])
            return True
        except Exception:
            return Opener._open_dir_mac(os.path.dirname(path) or "/")

    @staticmethod
    def _open_file_mac(path: str) -> bool:
        """
        Open file with default application

        :param path: Path to file
        :return: True if successful, False otherwise
        """
        try:
            subprocess.Popen(["open", path])
            return True
        except Exception:
            return QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    # ===== Linux =====
    @staticmethod
    def _fm_iface():
        """
        Get FileManager1 D-Bus interface if available

        :return: QDBusInterface or None
        """
        if not (IS_LINUX and HAS_QT_DBUS):
            return None
        bus = QDBusConnection.sessionBus()
        iface = QDBusInterface(
            "org.freedesktop.FileManager1",
            "/org/freedesktop/FileManager1",
            "org.freedesktop.FileManager1",
            bus,
        )
        return iface if iface.isValid() else None

    @staticmethod
    def _show_folders_dbus(paths):
        """
        Show folders using D-Bus FileManager1 interface

        :param paths: List of folder paths
        :return: True if successful, False otherwise
        """
        iface = Opener._fm_iface()
        if not iface:
            return False
        uris = [QUrl.fromLocalFile(p).toString() for p in paths]
        reply = iface.call("ShowFolders", uris, "")
        return reply.type() != QDBusMessage.ErrorMessage

    @staticmethod
    def _show_items_dbus(paths):
        """
        Show items using D-Bus FileManager1 interface

        :param paths: List of item paths
        :return: True if successful, False otherwise
        """
        iface = Opener._fm_iface()
        if not iface:
            return False
        uris = [QUrl.fromLocalFile(p).toString() for p in paths]
        reply = iface.call("ShowItems", uris, "")
        return reply.type() != QDBusMessage.ErrorMessage

    @staticmethod
    def _open_with_cli_linux(path):
        """
        Open path using common CLI tools (xdg-open, gio)

        :param path: Path to file or directory
        :return: True if successful, False otherwise
        """
        for cmd in (["xdg-open", path], ["gio", "open", path]):
            if shutil.which(cmd[0]):
                try:
                    subprocess.Popen(cmd)
                    return True
                except Exception:
                    pass
        return False

    @staticmethod
    def _open_dir_linux(path: str) -> bool:
        """
        Open directory in default file manager

        :param path: Path to directory
        :return: True if successful, False otherwise
        """
        if Opener._show_folders_dbus([path]):
            return True
        if QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            return True
        return Opener._open_with_cli_linux(path)

    @staticmethod
    def _reveal_linux(path: str) -> bool:
        """
        Reveal file in default file manager

        :param path: Path to file
        :return: True if successful, False otherwise
        """
        if Opener._show_items_dbus([path]):
            return True
        return False

    @staticmethod
    def _open_file_linux(path: str) -> bool:
        """
        Open file with default application

        :param path: Path to file
        :return: True if successful, False otherwise
        """
        if QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            return True
        return Opener._open_with_cli_linux(path)