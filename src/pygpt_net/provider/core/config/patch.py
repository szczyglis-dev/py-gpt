#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.30 22:00:00                  #
# ================================================== #

import copy
import os

from packaging.version import parse as parse_version, Version

# old patches moved here
from .patches.patch_before_2_6_42 import Patch as PatchBefore2_6_42


class Patch:
    def __init__(self, window=None):
        self.window = window

    def execute(self, version: Version) -> bool:
        """
        Migrate config to current app version

        :param version: current app version
        :return: True if migrated
        """
        data = self.window.core.config.all()
        cfg_get_base = self.window.core.config.get_base
        remove_plugin_config = self.window.core.config.remove_plugin_config
        patch_css = self.window.core.updater.patch_css
        current = "0.0.0"
        updated = False
        is_old = False

        # get version of config file
        if '__meta__' in data and 'version' in data['__meta__']:
            current = data['__meta__']['version']
        old = parse_version(current)

        # check if config file is older than current app version
        if old < version:

            is_old = True

            # --------------------------------------------
            # previous patches for versions before 2.6.42
            if old < parse_version("2.6.42"):
                patcher = PatchBefore2_6_42(self.window)
                data, updated, _ = patcher.execute(version)
            # --------------------------------------------

            # < 2.6.43
            if old < parse_version("2.6.43"):
                print("Migrating config from < 2.6.43...")
                # li div margin
                patch_css('web-chatgpt.css', True)
                patch_css('web-chatgpt_wide.css', True)
                patch_css('web-blocks.css', True)
                updated = True

            # < 2.6.44
            if old < parse_version("2.6.44"):
                print("Migrating config from < 2.6.44...")
                if "render.code_syntax.stream_n_line" not in data:
                    data["render.code_syntax.stream_n_line"] = 25
                if "render.code_syntax.stream_n_chars" not in data:
                    data["render.code_syntax.stream_n_chars"] = 5000
                if "render.code_syntax.disabled" not in data:
                    data["render.code_syntax.disabled"] = False
                if "render.msg.user.collapse.px" not in data:
                    data["render.msg.user.collapse.px"] = 1500
                updated = True

            # < 2.6.46
            if old < parse_version("2.6.46"):
                print("Migrating config from < 2.6.46...")
                # output stream margin-top: 0
                patch_css('web-chatgpt.css', True)
                patch_css('web-chatgpt_wide.css', True)
                patch_css('web-blocks.css', True)
                patch_css('style.dark.css', True)
                patch_css('web-blocks.light.css', True)
                patch_css('web-chatgpt.light.css', True)
                patch_css('web-chatgpt_wide.light.css', True)
                updated = True

            # < 2.6.48
            if old < parse_version("2.6.48"):
                print("Migrating config from < 2.6.48...")
                # reformat
                patch_css('web-chatgpt.css', True)
                patch_css('web-chatgpt_wide.css', True)
                patch_css('web-blocks.css', True)
                updated = True

            # < 2.6.51
            if old < parse_version("2.6.51"):
                print("Migrating config from < 2.6.51...")
                # calendar css
                patch_css('style.dark.css', True)
                updated = True

            # < 2.6.53
            if old < parse_version("2.6.53"):
                print("Migrating config from < 2.6.53...")
                if "remote_tools.global.web_search" not in data:
                    data["remote_tools.global.web_search"] = True
                updated = True

            # < 2.6.56
            if old < parse_version("2.6.56"):
                print("Migrating config from < 2.6.56...")
                # copy btn header
                patch_css('web-chatgpt.css', True)
                patch_css('web-chatgpt_wide.css', True)
                patch_css('web-blocks.css', True)
                patch_css('web-blocks.light.css', True)
                patch_css('web-chatgpt.light.css', True)
                patch_css('web-chatgpt_wide.light.css', True)
                patch_css('web-blocks.dark.css', True)
                patch_css('web-chatgpt.dark.css', True)
                patch_css('web-chatgpt_wide.dark.css', True)
                patch_css('web-blocks.darkest.css', True)
                patch_css('web-chatgpt.darkest.css', True)
                patch_css('web-chatgpt_wide.darkest.css', True)
                updated = True

            # < 2.6.57
            if old < parse_version("2.6.57"):
                print("Migrating config from < 2.6.57...")
                remove_plugin_config("cmd_web", "max_open_urls")
                remove_plugin_config("cmd_web", "cmd.web_url_open")
                remove_plugin_config("cmd_web", "cmd.web_url_raw")
                remove_plugin_config("cmd_web", "cmd.web_extract_links")
                remove_plugin_config("cmd_web", "cmd.web_extract_images")
                if "api_proxy.enabled" not in data:
                    data["api_proxy.enabled"] = False
                if "api_proxy" in data and data["api_proxy"]:
                    data["api_proxy.enabled"] = True
                updated = True

            # < 2.6.58
            if old < parse_version("2.6.58"):
                print("Migrating config from < 2.6.58...")
                if "ctx.urls.internal" not in data:
                    data["ctx.urls.internal"] = False
                updated = True

            # < 2.6.61
            if old < parse_version("2.6.61"):
                print("Migrating config from < 2.6.61...")
                if "presets.drag_and_drop.enabled" not in data:
                    data["presets.drag_and_drop.enabled"] = True
                if "presets_order" not in data:
                    data["presets_order"] = {}
                updated = True

            # < 2.6.62
            if old < parse_version("2.6.62"):
                print("Migrating config from < 2.6.62...")
                # add: node editor css
                patch_css('style.light.css', True)
                patch_css('style.dark.css', True)
                updated = True

            # < 2.6.65
            if old < parse_version("2.6.65"):
                print("Migrating config from < 2.6.65...")
                # add: status bar css
                patch_css('style.light.css', True)
                patch_css('style.dark.css', True)
                updated = True

            # < 2.6.66
            if old < parse_version("2.6.66"):
                print("Migrating config from < 2.6.66...")
                if "img_mode" not in data:
                    data["img_mode"] = "image"
                updated = True

            # < 2.7.0
            if old < parse_version("2.7.0"):
                print("Migrating config from < 2.7.0...")
                # add: combo boxes css
                patch_css('style.light.css', True)
                patch_css('style.dark.css', True)
                updated = True

            # < 2.7.1
            if old < parse_version("2.7.1"):
                print("Migrating config from < 2.7.1...")
                # update: combo boxes css
                patch_css('style.light.css', True)
                patch_css('style.dark.css', True)
                updated = True

            # < 2.7.2
            if old < parse_version("2.7.2"):
                print("Migrating config from < 2.7.2...")
                # fix: combo boxes css width
                patch_css('style.light.css', True)
                patch_css('style.dark.css', True)
                updated = True

            # < 2.7.3
            if old < parse_version("2.7.3"):
                print("Migrating config from < 2.7.3...")
                if "video.remix" not in data:
                    data["video.remix"] = False
                if "img.remix" not in data:
                    data["img.remix"] = False
                updated = True

        # update file
        migrated = False
        if updated:
            data = dict(sorted(data.items()))
            self.window.core.config.data = data
            self.window.core.config.save()
            migrated = True

        # check for any missing config keys if versions mismatch
        if is_old:
            if self.window.core.updater.post_check_config():
                migrated = True

        return migrated
