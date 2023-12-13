#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.13 14:00:00                  #
# ================================================== #

from urllib.request import urlopen, Request
from packaging.version import parse as parse_version
import os
import shutil
import json
import ssl
from .utils import trans


class Updater:
    def __init__(self, window=None):
        """
        Updater (patcher)

        :param window: main window
        """
        self.window = window
        self.base_config = {}
        self.base_config_loaded = False

    def check(self):
        """Checks for updates"""
        print("Checking for updates...")
        url = self.window.website + "/api/version?v=" + str(self.window.version)
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = Request(
                url=url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            response = urlopen(req, context=ctx, timeout=3)
            data_json = json.loads(response.read())
            newest_version = data_json["version"]
            newest_build = data_json["build"]

            # changelog
            changelog = ""
            if "changelog" in data_json:
                changelog = data_json["changelog"]

            parsed_newest_version = parse_version(newest_version)
            parsed_current_version = parse_version(self.window.version)
            if parsed_newest_version > parsed_current_version:
                self.show_version_dialog(newest_version, newest_build, changelog)
            else:
                print("No updates available")
        except Exception as e:
            print("Failed to check for updates")
            print(e)

    def show_version_dialog(self, version, build, changelog):
        """
        Displays new version dialog

        :param version: version number
        :param build: build date
        :param changelog: changelog
        """
        txt = trans('update.new_version') + ": " + str(version) + " (" + trans('update.released') + ": " + str(
            build) + ")"
        txt += "\n" + trans('update.current_version') + ": " + self.window.version
        self.window.dialog['update'].changelog.setPlainText(changelog)
        self.window.dialog['update'].message.setText(txt)
        self.window.ui.dialogs.open('update')

    def load_base_config(self):
        """
        Loads app config from JSON file
        """
        self.base_config = {}
        path = os.path.join(self.window.config.get_root_path(), 'data', 'config', 'config.json')
        if not os.path.exists(path):
            print("FATAL ERROR: {} not found!".format(path))
            return None
        try:
            f = open(path, "r", encoding="utf-8")
            self.base_config = json.load(f)
            self.base_config = dict(sorted(self.base_config.items(), key=lambda item: item[0]))  # sort by key
            f.close()
        except Exception as e:
            print(e)

    def get_base_config(self, option=None):
        """
        Returns base config option or whole config
        """
        if not self.base_config_loaded:
            self.load_base_config()
            self.base_config_loaded = True
        if option is None:
            return self.base_config
        elif option in self.base_config:
            return self.base_config[option]

    def patch(self):
        """Patch config files to current version"""
        try:
            self.patch_config()
            self.patch_models()
            self.patch_presets()
            # TODO: add context patcher
        except Exception as e:
            print("Failed to patch config files!")
            print(e)

    def patch_dir(self, dirname="", force=False):
        """
        Patches directory
        :param dirname: Directory name
        :param force: Force update
        """
        try:
            # dir
            dst_dir = os.path.join(self.window.config.path, dirname)
            src = os.path.join(self.window.config.get_root_path(), 'data', 'config', dirname)
            for file in os.listdir(src):
                src_file = os.path.join(src, file)
                dst_file = os.path.join(dst_dir, file)
                if not os.path.exists(dst_file) or force:
                    shutil.copyfile(src_file, dst_file)
        except Exception as e:
            print(e)

    def patch_file(self, filename="", force=False):
        """
        Patches file
        :param filename: File name
        :param force: Force update
        """
        try:
            # file
            dst = os.path.join(self.window.config.path, filename)
            if not os.path.exists(dst) or force:
                src = os.path.join(self.window.config.get_root_path(), 'data', 'config', filename)
                shutil.copyfile(src, dst)
        except Exception as e:
            print(e)

    def patch_models(self):
        """Migrates models to current version"""
        data = self.window.config.models
        version = "0.0.0"
        updated = False
        if '__meta__' in data and 'version' in data['__meta__']:
            version = data['__meta__']['version']
        old = parse_version(version)
        current = parse_version(self.window.version)
        if old < current:
            if old < parse_version("2.0.1"):
                self.patch_file('models.json', True)
                self.window.config.load_models()
                data = self.window.config.models
                updated = True
            if old < parse_version("0.9.1"):
                # apply meta only (not attached in 0.9.0)
                updated = True

        # update file
        if updated:
            data = dict(sorted(data.items()))
            self.window.config.models = data
            self.window.config.save_models()
            print("Migrated models.json.")

    def patch_presets(self):
        """Migrates presets to current version"""
        for k in self.window.config.presets:
            data = self.window.config.presets[k]
            version = "0.0.0"
            updated = False
            if '__meta__' in data and 'version' in data['__meta__']:
                version = data['__meta__']['version']
            old = parse_version(version)
            current = parse_version(self.window.version)
            if old < current:
                if old < parse_version("2.0.0"):
                    self.patch_file('presets', True)

            # update file
            if updated:
                data = dict(sorted(data.items()))
                self.window.config.presets[k] = data
                self.window.config.save_preset(k)
                print("Migrated presets.")

    def patch_config(self):
        """Migrates config to current version"""
        data = self.window.config.data
        version = "0.0.0"
        updated = False
        if '__meta__' in data and 'version' in data['__meta__']:
            version = data['__meta__']['version']
        old = parse_version(version)
        current = parse_version(self.window.version)
        if old < current:
            if old < parse_version("2.0.25"):
                if 'cmd.prompt' not in data:
                    data['cmd.prompt'] = self.get_base_config('cmd.prompt')
                if 'img_prompt' not in data:
                    data['img_prompt'] = self.get_base_config('img_prompt')
                if 'vision.capture.quality' not in data:
                    data['vision.capture.quality'] = 85
                if 'attachments_capture_clear' not in data:
                    data['attachments_capture_clear'] = True
                updated = True
            if old < parse_version("2.0.19"):
                if 'img_raw' not in data:
                    data['img_raw'] = True
                if not data['img_raw']:
                    data['img_raw'] = True
                updated = True
            if old < parse_version("2.0.16"):
                if 'vision.capture.idx' not in data:
                    data['vision.capture.idx'] = 0
                if 'img_raw' not in data:
                    data['img_raw'] = True
                if 'img_prompt_model' not in data:
                    data['img_prompt_model'] = "gpt-4-1106-preview"
                updated = True
            if old < parse_version("2.0.14"):
                if 'vision.capture.enabled' not in data:
                    data['vision.capture.enabled'] = True
                if 'vision.capture.auto' not in data:
                    data['vision.capture.auto'] = True
                if 'vision.capture.width' not in data:
                    data['vision.capture.width'] = 800
                if 'vision.capture.height' not in data:
                    data['vision.capture.height'] = 600
                updated = True
            if old < parse_version("2.0.13"):
                if 'layout.density' not in data:
                    data['layout.density'] = 0
                else:
                    if data['layout.density'] == -2:
                        data['layout.density'] = 0
                updated = True
            if old < parse_version("2.0.8"):
                if 'plugins' not in data:
                    data['plugins'] = {}
                if 'cmd_web_google' not in data['plugins']:
                    data['plugins']['cmd_web_google'] = {}
                data['plugins']['cmd_web_google']['prompt_summarize'] = "Summarize the English text in a maximum of 3 " \
                                                                        "paragraphs, trying to find the most " \
                                                                        "important content that can help answer the " \
                                                                        "following question: "
                data['plugins']['cmd_web_google']['chunk_size'] = 100000
                data['plugins']['cmd_web_google']['max_page_content_length'] = 0
                updated = True
            if old < parse_version("2.0.6"):
                if 'layout.density' not in data:
                    data['layout.density'] = -2
                updated = True
            if old < parse_version("2.0.1"):
                if 'send_mode' not in data:
                    data['send_mode'] = 1
                if 'send_shift_enter' in data:
                    del data['send_shift_enter']
                if 'font_size.input' not in data:
                    data['font_size.input'] = 11
                if 'font_size.ctx' not in data:
                    data['font_size.ctx'] = 9
                if 'ctx.auto_summary' not in data:
                    data['ctx.auto_summary'] = True
                if 'ctx.auto_summary.system' not in data:
                    data['ctx.auto_summary.system'] = "You are an expert in conversation summarization"
                if 'ctx.auto_summary.prompt' not in data:
                    data['ctx.auto_summary.prompt'] = "Summarize topic of this conversation in one sentence. Use best " \
                                                      "keywords to describe it. Summary must be in the same language " \
                                                      "as the conversation and it will be used for conversation title " \
                                                      "so it must be EXTREMELY SHORT and concise - use maximum 5 " \
                                                      "words: \n\nUser: {input}\nAI Assistant: {output}"
                updated = True
            if old < parse_version("2.0.0"):
                data['theme'] = 'dark_teal'  # force, because removed light themes!
                if 'cmd' not in data:
                    data['cmd'] = True
                if 'stream' not in data:
                    data['stream'] = True
                if 'attachments_send_clear' not in data:
                    data['attachments_send_clear'] = True
                if 'assistant' not in data:
                    data['assistant'] = None
                if 'assistant_thread' not in data:
                    data['assistant_thread'] = None
                updated = True
            if old < parse_version("0.9.6"):
                print("Migrating config from < 0.9.6...")
                data['debug'] = True  # enable debug by default
                updated = True
            if old < parse_version("0.9.4"):
                print("Migrating config from < 0.9.4...")
                if 'plugins' not in data:
                    data['plugins'] = {}
                if 'plugins_enabled' not in data:
                    data['plugins_enabled'] = {}
                updated = True
            if old < parse_version("0.9.2"):
                print("Migrating config from < 0.9.2...")
                keys_to_remove = ['ui.ctx.min_width',
                                  'ui.ctx.max_width',
                                  'ui.toolbox.min_width',
                                  'ui.toolbox.max_width',
                                  'ui.dialog.settings.width',
                                  'ui.dialog.settings.height',
                                  'ui.chatbox.font.color']
                for key in keys_to_remove:
                    if key in data:
                        del data[key]
                if 'theme' not in data:
                    data['theme'] = "dark_teal"
                updated = True

            if old < parse_version("0.9.1"):
                print("Migrating config from < 0.9.1...")
                keys_to_remove = ['user_id', 'custom']  # not needed anymore
                for key in keys_to_remove:
                    if key in data:
                        del data[key]
                keys_to_add = ['organization_key']
                for key in keys_to_add:
                    if key not in data:
                        data[key] = ""
                updated = True

        # update file
        if updated:
            data = dict(sorted(data.items()))
            self.window.config.data = data
            self.window.config.save()
            print("Migrated config.json.")
