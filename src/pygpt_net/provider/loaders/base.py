#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.04.17 01:00:00                  #
# ================================================== #

from llama_index.core.readers.base import BaseReader


class BaseLoader:
    def __init__(self, *args, **kwargs):
        self.window = None
        self.id = ""
        self.name = ""
        self.extensions = []
        self.type = ["file"]  # list of types: file, web
        self.instructions = []  # list of instructions for 'web_index' command for how to handle this type
        self.args = {}  # custom keyword arguments
        self.init_args = {}  # initial keyword arguments
        self.init_args_types = {}
        self.allow_compiled = True  # allow in compiled and Snap versions
        # This is required due to some readers may require Python environment to install additional packages

    def attach_window(self, window):
        """
        Attach window instance

        :param window: Window instance
        """
        self.window = window

    def set_args(self, args: dict):
        """
        Set loader initial keyword arguments

        :param args: keyword arguments dict
        """
        self.args = args

    def get_args(self):
        """
        Prepare keyword arguments for reader init method

        :return: keyword arguments dict
        """
        args = {}
        for key in self.init_args:
            args[key] = self.init_args[key]
            if key in self.args:
                args[key] = self.args[key]
        return args

    def prepare_args(self, **kwargs) -> dict:
        """
        Prepare arguments for reader load method

        :param kwargs: keyword arguments
        :return: args to pass to reader
        """
        return kwargs

    def get_external_id(self, args: dict = None) -> str:
        """
        Get unique web content identifier

        :param args: load_data args
        :return: unique content identifier
        """
        if "url" in args:
            return args.get("url")
        return ""

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        pass
