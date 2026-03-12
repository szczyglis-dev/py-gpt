#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : PYGPT Contributors                   #
# Updated Date: 2026.03.11 00:00:00                  #
# ================================================== #

import os
import glob
import shutil
import subprocess
import platform
import webbrowser

from PySide6.QtCore import Slot

from pygpt_net.plugin.base.worker import BaseWorker
from pygpt_net.utils import normalize_text


class Worker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.args = args
        self.kwargs = kwargs
        self.cmds = None
        self.ctx = None

    @Slot()
    def run(self):
        """Run worker."""
        try:
            for item in self.cmds:
                response = None

                if item["cmd"] == "app_launch":
                    response = self.cmd_app_launch(item)

                elif item["cmd"] == "app_close":
                    response = self.cmd_app_close(item)

                elif item["cmd"] == "app_list_running":
                    response = self.cmd_app_list_running(item)

                elif item["cmd"] == "app_open_url":
                    response = self.cmd_app_open_url(item)

                elif item["cmd"] == "app_list_installed":
                    response = self.cmd_app_list_installed(item)

                elif item["cmd"] == "media_play_pause":
                    response = self.cmd_media_key(item, "play_pause")

                elif item["cmd"] == "media_next_track":
                    response = self.cmd_media_key(item, "next_track")

                elif item["cmd"] == "media_prev_track":
                    response = self.cmd_media_key(item, "prev_track")

                elif item["cmd"] == "volume_set":
                    response = self.cmd_volume_set(item)

                elif item["cmd"] == "volume_mute_toggle":
                    response = self.cmd_media_key(item, "mute")

                if response is not None:
                    self.reply(response)

        except Exception as e:
            self.error(e)
        finally:
            self.cleanup()

    def cmd_app_launch(self, item: dict) -> dict:
        """
        Launch an application

        :param item: command item
        :return: response dict
        """
        app_name = normalize_text(self.get_param(item, "app_name", "").strip())
        app_args = self.get_param(item, "args", "")

        if not app_name:
            return self.make_response(item, "Error: app_name is required")

        # Check custom aliases first
        aliases = self.plugin.get_option_value("custom_app_aliases")
        resolved = None
        if isinstance(aliases, dict):
            for alias, target in aliases.items():
                if normalize_text(alias) == app_name:
                    resolved = target
                    break

        # Try Start Menu shortcuts
        if resolved is None and platform.system() == "Windows":
            resolved = self.find_start_menu_shortcut(app_name)

        # Try finding in PATH
        if resolved is None:
            found_in_path = shutil.which(app_name)
            if found_in_path:
                resolved = found_in_path

        # Try common executable patterns on Windows
        if resolved is None and platform.system() == "Windows":
            resolved = self.find_windows_app(app_name)

        if resolved is None:
            return self.make_response(
                item,
                "Could not find application '{}'. "
                "Try adding it to custom app aliases in plugin settings.".format(app_name)
            )

        try:
            cmd_parts = [resolved]
            if app_args:
                cmd_parts.extend(app_args.split())

            if platform.system() == "Windows":
                subprocess.Popen(
                    cmd_parts,
                    shell=False,
                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                subprocess.Popen(cmd_parts, start_new_session=True)

            self.log("Launched: {}".format(resolved))
            return self.make_response(item, "Launched '{}' successfully".format(app_name))

        except Exception as e:
            # Fallback: try os.startfile on Windows
            if platform.system() == "Windows":
                try:
                    os.startfile(resolved)
                    return self.make_response(item, "Launched '{}' successfully".format(app_name))
                except Exception:
                    pass
            return self.make_response(item, "Failed to launch '{}': {}".format(app_name, str(e)))

    def cmd_app_close(self, item: dict) -> dict:
        """
        Close a running application

        :param item: command item
        :return: response dict
        """
        app_name = normalize_text(self.get_param(item, "app_name", "").strip())
        if not app_name:
            return self.make_response(item, "Error: app_name is required")

        if platform.system() != "Windows":
            return self.make_response(item, "app_close is only supported on Windows")

        # Map common names to process names
        process_map = {
            "chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "notepad": "notepad.exe",
            "explorer": "explorer.exe",
            "spotify": "Spotify.exe",
            "vscode": "Code.exe",
            "code": "Code.exe",
        }

        process_name = process_map.get(app_name, app_name)
        if not process_name.endswith(".exe"):
            process_name += ".exe"

        try:
            result = subprocess.run(
                ["taskkill", "/F", "/IM", process_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return self.make_response(item, "Closed '{}'".format(app_name))
            else:
                return self.make_response(
                    item,
                    "Could not close '{}': {}".format(app_name, result.stderr.strip())
                )
        except Exception as e:
            return self.make_response(item, "Error closing '{}': {}".format(app_name, str(e)))

    def cmd_app_list_running(self, item: dict) -> dict:
        """
        List running applications with visible windows

        :param item: command item
        :return: response dict
        """
        if platform.system() != "Windows":
            return self.make_response(item, "app_list_running is only supported on Windows")

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            windows = []

            WNDENUMPROC = ctypes.WINFUNCTYPE(
                wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
            )

            def enum_callback(hwnd, lparam):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buf, length + 1)
                        title = buf.value.strip()
                        if title:
                            windows.append(title)
                return True

            user32.EnumWindows(WNDENUMPROC(enum_callback), 0)

            # Deduplicate and limit
            seen = set()
            unique = []
            for w in windows:
                if w not in seen:
                    seen.add(w)
                    unique.append(w)

            result_text = "Running windows ({}):\n".format(len(unique))
            for w in unique[:50]:  # limit to 50
                result_text += "- {}\n".format(w)

            return self.make_response(item, result_text)

        except Exception as e:
            return self.make_response(item, "Error listing windows: {}".format(str(e)))

    def cmd_app_open_url(self, item: dict) -> dict:
        """
        Open a URL in the default browser

        :param item: command item
        :return: response dict
        """
        url = self.get_param(item, "url", "").strip()
        if not url:
            return self.make_response(item, "Error: url is required")

        # Add scheme if missing
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://{}".format(url)

        try:
            webbrowser.open(url)
            return self.make_response(item, "Opened URL: {}".format(url))
        except Exception as e:
            return self.make_response(item, "Error opening URL: {}".format(str(e)))

    def cmd_app_list_installed(self, item: dict) -> dict:
        """
        List installed applications

        :param item: command item
        :return: response dict
        """
        name_filter = normalize_text(self.get_param(item, "filter", "").strip())
        apps = []

        # From custom aliases
        aliases = self.plugin.get_option_value("custom_app_aliases")
        if isinstance(aliases, dict):
            for alias, target in aliases.items():
                if not name_filter or name_filter in normalize_text(alias):
                    apps.append("{} -> {}".format(alias, target))

        # From Start Menu
        if platform.system() == "Windows" and self.plugin.get_option_value("scan_start_menu"):
            start_menu_apps = self.scan_start_menu()
            for app_label, app_path in start_menu_apps:
                if not name_filter or name_filter in normalize_text(app_label):
                    apps.append("{} [Start Menu]".format(app_label))

        if not apps:
            return self.make_response(item, "No applications found matching '{}'".format(name_filter))

        # Deduplicate and sort
        apps = sorted(set(apps))[:100]

        result_text = "Installed applications ({}):\n".format(len(apps))
        for app in apps:
            result_text += "- {}\n".format(app)

        return self.make_response(item, result_text)

    def cmd_media_key(self, item: dict, action: str) -> dict:
        """
        Send a media key press

        :param item: command item
        :param action: media action
        :return: response dict
        """
        if platform.system() != "Windows":
            return self.make_response(item, "Media keys are only supported on Windows")

        try:
            import ctypes

            user32 = ctypes.windll.user32

            # Virtual key codes for media keys
            VK_MEDIA = {
                "play_pause": 0xB3,
                "next_track": 0xB0,
                "prev_track": 0xB1,
                "mute": 0xAD,
            }

            vk = VK_MEDIA.get(action)
            if vk is None:
                return self.make_response(item, "Unknown media action: {}".format(action))

            # Simulate key press and release
            KEYEVENTF_EXTENDEDKEY = 0x0001
            KEYEVENTF_KEYUP = 0x0002

            user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY, 0)
            user32.keybd_event(vk, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)

            action_labels = {
                "play_pause": "Toggled play/pause",
                "next_track": "Skipped to next track",
                "prev_track": "Went to previous track",
                "mute": "Toggled mute",
            }

            return self.make_response(item, action_labels.get(action, "Done"))

        except Exception as e:
            return self.make_response(item, "Error sending media key: {}".format(str(e)))

    def cmd_volume_set(self, item: dict) -> dict:
        """
        Set system volume level

        :param item: command item
        :return: response dict
        """
        level = self.get_param(item, "level", 50)

        try:
            level = int(level)
            level = max(0, min(100, level))
        except (ValueError, TypeError):
            return self.make_response(item, "Error: volume level must be a number 0-100")

        if platform.system() != "Windows":
            return self.make_response(item, "Volume control is only supported on Windows")

        try:
            from pycaw.pycaw import AudioUtilities

            devices = AudioUtilities.GetSpeakers()
            volume = devices.EndpointVolume

            # pycaw uses scalar volume (0.0 to 1.0)
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)

            return self.make_response(item, "Volume set to {}%".format(level))

        except ImportError:
            # Fallback: use nircmd if available
            nircmd = shutil.which("nircmd")
            if nircmd:
                try:
                    # nircmd uses 0-65535 range
                    nircmd_level = int(level * 65535 / 100)
                    subprocess.run(
                        [nircmd, "setsysvolume", str(nircmd_level)],
                        timeout=5,
                    )
                    return self.make_response(item, "Volume set to {}%".format(level))
                except Exception as e:
                    return self.make_response(item, "Error setting volume: {}".format(str(e)))

            return self.make_response(
                item,
                "Volume control requires 'pycaw' package. Install with: pip install pycaw"
            )

        except Exception as e:
            return self.make_response(item, "Error setting volume: {}".format(str(e)))

    # --- Helpers ---

    def find_start_menu_shortcut(self, app_name: str):
        """
        Find application shortcut in Windows Start Menu

        :param app_name: application name to find
        :return: path to shortcut or None
        """
        shortcuts = self.scan_start_menu()
        app_name_norm = normalize_text(app_name)

        # Exact match first
        for label, path in shortcuts:
            if normalize_text(label) == app_name_norm:
                return path

        # Partial match
        for label, path in shortcuts:
            if app_name_norm in normalize_text(label):
                return path

        return None

    def scan_start_menu(self):
        """
        Scan Windows Start Menu directories for .lnk shortcuts

        :return: list of (label, path) tuples
        """
        results = []
        start_menu_dirs = []

        # Common Start Menu paths
        appdata = os.environ.get("APPDATA", "")
        programdata = os.environ.get("PROGRAMDATA", "")

        if appdata:
            start_menu_dirs.append(
                os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs")
            )
        if programdata:
            start_menu_dirs.append(
                os.path.join(programdata, "Microsoft", "Windows", "Start Menu", "Programs")
            )

        for start_dir in start_menu_dirs:
            if not os.path.isdir(start_dir):
                continue

            for lnk_path in glob.glob(
                os.path.join(start_dir, "**", "*.lnk"), recursive=True
            ):
                label = os.path.splitext(os.path.basename(lnk_path))[0]
                results.append((label, lnk_path))

        return results

    def find_windows_app(self, app_name: str):
        """
        Try to find an application on Windows by common paths

        :param app_name: application name
        :return: executable path or None
        """
        common_paths = {
            "chrome": [
                os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
            ],
            "firefox": [
                os.path.join(os.environ.get("PROGRAMFILES", ""), "Mozilla Firefox", "firefox.exe"),
                os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Mozilla Firefox", "firefox.exe"),
            ],
            "spotify": [
                os.path.join(os.environ.get("APPDATA", ""), "Spotify", "Spotify.exe"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WindowsApps", "Spotify.exe"),
            ],
            "vscode": [
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Microsoft VS Code", "Code.exe"),
            ],
            "code": [
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Microsoft VS Code", "Code.exe"),
            ],
        }

        paths = common_paths.get(app_name.lower(), [])
        for path in paths:
            if path and os.path.isfile(path):
                return path

        return None
