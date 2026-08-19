#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.15 00:00:00                  #
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
        self.plugin.window.update_status("Please wait...")

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

    def get_volumes(self) -> dict:
        """Return data volume plus the application's temporary directory."""
        volumes = super().get_volumes()
        tmp_dir = self.plugin.window.core.config.get_user_dir("tmp")
        volumes[tmp_dir] = {
            "bind": "/pygpt_tmp",
            "mode": "rw",
        }
        return volumes

    def create_container(self, name: str):
        """Recreate an old container once if it does not have the tmp mount yet."""
        try:
            client = self.get_docker_client()
            container = client.containers.get(name)
            container.reload()
            has_tmp_mount = any(
                mount.get("Destination") == "/pygpt_tmp"
                for mount in container.attrs.get("Mounts", [])
            )
            if not has_tmp_mount:
                if container.status == "running":
                    container.stop()
                    container.wait()
                container.remove()
        except Exception:
            pass
        return super().create_container(name)
