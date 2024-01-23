#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.01.22 18:00:00                  #
# ================================================== #

from llama_index import (
    VectorStoreIndex,
    ServiceContext,
)


class BaseStore:
    def __init__(self, *args, **kwargs):
        """
        Base vector store provider

        :param args: args
        :param kwargs: kwargs
        """
        self.window = kwargs.get('window', None)
        self.id = None

    def attach(self, window=None):
        """
        Attach window instance

        :param window: Window instance
        """
        self.window = window

    def exists(self, id: str = None) -> bool:
        """
        Check if index with id exists

        :param id: index name
        :return: True if exists
        """
        pass

    def create(self, id: str):
        """
        Create empty index

        :param id: index name
        """
        pass

    def get(self, id: str, service_context: ServiceContext = None) -> VectorStoreIndex:
        """
        Get index instance

        :param id: index name
        :param service_context: Service context
        :return: index instance
        """
        pass

    def store(self, id: str, index: VectorStoreIndex = None):
        """
        Store/persist index

        :param id: index name
        :param index: index instance
        """
        pass

    def remove(self, id: str) -> bool:
        """
        Truncate index

        :param id: index name
        :return: True if success
        """
        pass
