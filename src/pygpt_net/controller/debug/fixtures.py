#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.12 20:00:00                  #
# ================================================== #

import os
from typing import Iterable

from pygpt_net.core.fixtures.stream.generator import FakeOpenAIStream
from pygpt_net.item.ctx import CtxItem


class Fixtures:
    def __init__(self, window=None):
        """
        Fixtures controller

        :param window: Window instance
        """
        self.window = window
        self.enabled = {
            "stream": False,
        }

    def is_enabled(self, name: str) -> bool:
        """
        Check if fixture is enabled by name

        :param name: fixture name
        """
        return self.enabled.get(name, False)

    def enable(self, name: str):
        """
        Enable fixture by name

        :param name: fixture name
        """
        if name in self.enabled:
            self.enabled[name] = True

    def disable(self, name: str):
        """
        Disable fixture by name

        :param name: fixture name
        e"""
        if name in self.enabled:
            self.enabled[name] = False

    def toggle(self, name: str):
        """
        Toggle fixture by name

        :param name: fixture name
        """
        if name in self.enabled:
            self.enabled[name] = not self.enabled[name]

    def toggle_from_menu(self, name: str):
        """
        Toggle fake stream debug

        :param name: fixture name
        """
        k = f"debug.fixtures.{name}"
        if k not in self.window.ui.menu:
            return
        value = self.window.ui.menu[k].isChecked()
        self.enable("stream") if value else self.disable("stream")
        self.window.controller.debug.update()  # update menu

    def get_stream_generator(self, ctx: CtxItem) -> Iterable:
        """
        Get fake stream generator

        :param ctx: context item
        :return: stream generator
        """
        ctx.use_responses_api = False
        path = os.path.join(self.window.core.config.get_app_path(), "data", "fixtures", "fake_stream.txt")
        return FakeOpenAIStream(code_path=path).stream(
            api="raw",
            chunk="code",
        )

    def setup(self):
        """Set up fixtures"""
        pass

    def update(self):
        """Update fixtures"""
        pass

    def reload(self):
        """Reload fixtures"""
        pass