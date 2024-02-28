#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.27 22:00:00                  #
# ================================================== #

from llama_index.core.readers.base import BaseReader


class BaseLoader:
    def __init__(self, *args, **kwargs):
        self.id = ""
        self.name = ""
        self.extensions = []
        self.type = ["file"]  # list of types: file, web
        self.instructions = []  # list of instructions for 'web_index' command for how to handle this type
        self.args = {}  # custom keyword arguments
        self.init_args = {}  # initial keyword arguments

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

    def get(self) -> BaseReader:
        """
        Get reader instance

        :return: Data reader instance
        """
        pass
