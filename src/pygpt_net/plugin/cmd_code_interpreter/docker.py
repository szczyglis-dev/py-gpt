#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 17:00:00                  #
# ================================================== #

from pygpt_net.core.docker import Docker as BaseDocker
from pygpt_net.core.docker.builder import Builder


class Docker(BaseDocker):
    def __init__(self, plugin = None):
        super(Docker, self).__init__(plugin)
        self.plugin = plugin
        self.initialized = False
        self.signals = None
        self.builder = Builder(self.plugin)
        self.builder.docker = self

    def build(self):
        """Run image build"""
        self.builder.build_image()

    def build_and_restart(self):
        """Run image build and restart container"""
        self.builder.build_image(restart=True)

    def get_dockerfile(self) -> str:
        """
        Get the Dockerfile

        :return: Dockerfile.
        """
        return self.plugin.get_option_value('dockerfile')

    def get_image_name(self) -> str:
        """
        Get the image name

        :return: Image name.
        """
        return self.plugin.get_option_value('image_name')

    def get_container_name(self) -> str:
        """
        Get the container name

        :return: Container name.
        """
        return self.plugin.get_option_value('container_name')

    def get_local_data_dir(self) -> str:
        """
        Get the local data directory.

        :return: Local data directory.
        """
        return self.plugin.window.core.config.get_user_dir("data")