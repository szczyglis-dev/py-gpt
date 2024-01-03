#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.02 22:00:00                  #
# ================================================== #

import os
import shutil


class Filesystem:
    def __init__(self, window=None):
        """
        Filesystem core

        :param window: Window instance
        """
        self.window = window

    def install(self):
        """Install provider data"""
        # output data directory
        data_dir = os.path.join(self.window.core.config.path, 'output')
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)

        # install custom css styles for override default styles
        css_dir = os.path.join(self.window.core.config.path, 'css')
        if not os.path.exists(css_dir):
            os.mkdir(css_dir)

        styles = [
            'style.css',
            'style.dark.css',
            'style.light.css',
            'markdown.css',
            'markdown.dark.css',
            'markdown.light.css',
        ]

        src_dir = os.path.join(self.window.core.config.get_app_path(), 'data', 'css')
        dst_dir = os.path.join(self.window.core.config.path, 'css')

        try:
            for style in styles:
                src = os.path.join(src_dir, style)
                dst = os.path.join(dst_dir, style)
                if not os.path.exists(dst) and os.path.exists(src):
                    shutil.copyfile(src, dst)
        except Exception as e:
            print("Error while installing css files: ", e)

