#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 00:00:00                  #
# ================================================== #

import os
from typing import Optional, Any

import docker
import io
import tarfile

from docker.errors import DockerException

class Docker:
    def __init__(self, plugin = None):
        self.plugin = plugin
        self.client = None
        self.container_name = "pygpt_container"
        self.image_name = "pygpt_image"
        self.initialized = False
        self.signals = None

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

    def create_docker_context(self, dockerfile: str) -> io.BytesIO:
        """
        Create a Docker context with the specified Dockerfile content.

        :param dockerfile: Dockerfile content.
        :return: Docker context.
        """
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            dockerfile_info = tarfile.TarInfo('Dockerfile')
            dockerfile_data = dockerfile.encode('utf-8')
            dockerfile_info.size = len(dockerfile_data)
            tar.addfile(dockerfile_info, io.BytesIO(dockerfile_data))
        tar_stream.seek(0)
        return tar_stream

    def is_image(self) -> bool:
        """
        Check if the Docker image exists.

        :return: True if the image exists.
        """
        client = self.get_docker_client()
        try:
            client.images.get(self.get_image_name())
            return True
        except docker.errors.ImageNotFound as e:
            print(e)
            return False

    def build_image(self):
        """Build the Docker image."""
        client = self.get_docker_client()
        context = self.create_docker_context(self.get_dockerfile())
        self.log("Please wait... Building the Docker image...")
        image, logs = client.images.build(
            fileobj=context,
            custom_context=True,
            rm=True,
            tag=self.get_image_name(),
        )
        for chunk in logs:
            if 'stream' in chunk:
                self.log(chunk['stream'].strip())

    def prepare_local_data_dir(self):
        """ Prepare the local data directory."""
        local_data_dir = self.get_local_data_dir()
        try:
            os.makedirs(local_data_dir)
        except FileExistsError:
            pass

    def get_docker_client(self) -> docker.DockerClient:
        """
        Get the Docker client.

        :return: Docker client.
        """
        return docker.from_env()

    def end(self, all: bool = False):
        """
        Stop all.

        :param all: Stop the container as well.
        """
        if all:
            self.stop_container(self.get_container_name())

    def stop_container(self, name: str):
        """
        Stop the Docker container.

        :param name: Container name.
        """
        client = self.get_docker_client()
        try:
            container = client.containers.get(name)
            container.stop()
            container.remove()
        except docker.errors.NotFound:
            self.log(f"Container '{name}' not found.")

    def create_container(self, name: str):
        """
        Create the Docker container.

        :param name: Container name.
        """
        client = self.get_docker_client()
        image_name = self.get_image_name()
        entrypoint = self.get_entrypoint()
        volumes = self.get_volumes()
        ports = self.get_ports()

        try:
            container = client.containers.get(name)
            container.reload()
            if container.status == 'running':
                pass
            else:
                print(f"Container '{name}' is not running. Starting it.")
                container.remove()
                container = client.containers.create(
                    image=image_name,
                    name=name,
                    volumes=volumes,
                    ports=ports,
                    tty=True,
                    stdin_open=True,
                    command=entrypoint,
                )
                container.start()
        except docker.errors.NotFound:
            print(f"Container '{name}' not found. Creating a new one.")
            container = client.containers.create(
                image=image_name,
                name=name,
                volumes=volumes,
                ports=ports,
                tty=True,
                stdin_open=True,
                command=entrypoint,
            )
            container.start()
        except Exception as e:
            self.log(f"Error creating container: {e}")

    def restart_container(self, name: str):
        """
        Restart the Docker container.

        :param name: Container name.
        """
        client = self.get_docker_client()
        image_name = self.get_image_name()
        entrypoint = self.get_entrypoint()
        volumes = self.get_volumes()
        ports = self.get_ports()

        try:
            container = client.containers.get(name)
            container.reload()
            status = container.status
            print(f"Container '{name}' status: {status}")

            if status == 'running':
                print(f"Stopping and starting container '{name}'...")
                container.stop()
                container.wait()
                container.reload()

            elif status == 'paused':
                print(f"Resuming and starting container '{name}'...")
                container.unpause()
                container.stop()
                container.wait()
                container.reload()

            elif status in ['exited', 'created']:
                print(f"Container '{name}' is in state '{status}'. Starting it.")

            elif status == 'restarting':
                print(f"Container '{name}' is restarting. Waiting...")
                container.wait()
                container.reload()

            elif status == 'removing':
                print(f"Container '{name}' is being removed. Waiting...")
                container.wait()
                container = None

            elif status == 'dead':
                print(f"Container '{name}' is dead. Removing and creating a new one.")
                container.remove()
                container = None

            else:
                print(f"Unknown container status: {status}. Removing and creating a new one.")
                container.remove()
                container = None

            if container:
                print(f"Starting container '{name}'...")
                try:
                    container.start()
                    container.reload()
                    if container.status != 'running':
                        print(f"Container '{name}' did not start correctly. Status: {container.status}")
                        print(f"Removing and creating a new container '{name}'...")
                        container.remove()
                        container = None
                except Exception as e:
                    print(f"Error starting container '{name}': {e}")
                    print(f"Removing and creating a new container '{name}'...")
                    container.remove()
                    container = None

            if not container:
                print(f"Creating a new container '{name}'...")
                container = client.containers.create(
                    image=image_name,
                    name=name,
                    volumes=volumes,
                    ports=ports,
                    tty=True,
                    stdin_open=True,
                    command=entrypoint,  # 'running'
                )
                container.start()
                container.reload()
                if container.status != 'running':
                    print(f"Container '{name}' did not start correctly. Status: {container.status}")
                else:
                    print(f"Container '{name}' started successfully.")

        except docker.errors.NotFound:
            print(f"Container '{name}' not found. Creating a new one.")
            container = client.containers.create(
                image=image_name,
                name=name,
                volumes=volumes,
                ports=ports,
                tty=True,
                stdin_open=True,
                command=entrypoint,  # 'running'
            )
            container.start()
            container.reload()
            if container.status != 'running':
                print(f"Container '{name}' did not start correctly. Status: {container.status}")
            else:
                print(f"Container '{name}' started successfully.")
        except Exception as e:
            print(f"Error restarting container '{name}': {e}")

    def restart(self):
        """Restart the Docker container."""
        self.restart_container(self.get_container_name())

    def get_volumes(self) -> dict:
        """
        Get the volumes mappings.

        :return: Volumes mappings.
        """
        workdir = self.get_local_data_dir()
        config = self.plugin.get_option_value('docker_volumes')
        data = {}
        for item in config:
            if item['enabled']:
                host_dir = item['host'].format(workdir=workdir)
                data[host_dir] = {
                    'bind': item['docker'],
                    'mode': 'rw',
                }
        return data

    def get_ports(self) -> dict:
        """
        Get the ports mappings.

        :return: Ports mappings.
        """
        config = self.plugin.get_option_value('docker_ports')
        data = {}
        for item in config:
            if item['enabled']:
                docker_port = item['docker']
                try:
                    host_port = int(item['host'])
                except ValueError:
                    print("WARNING: Invalid host port number: {}. "
                          "Please provide a valid port number as integer value".format(item['host']))
                    continue
                if "/" not in docker_port:
                    docker_port = f"{docker_port}/tcp"
                data[docker_port] = host_port
        return data

    def get_entrypoint(self) -> str:
        """
        Get the Docker entrypoint.

        :return: Docker entrypoint command.
        """
        return self.plugin.get_option_value('docker_entrypoint')

    def execute(self, cmd: str) -> Optional[bytes]:
        """
        Execute command in Docker container.

        :param cmd: Command to execute
        :return: Response
        """
        client = self.get_docker_client()
        name = self.get_container_name()

        # at first, check for image
        if not self.is_image():
            self.build_image()

        # run the container
        try:
            self.create_container(name)
            container = client.containers.get(name)
            result = container.exec_run(
                cmd,
                stdout=True,
                stderr=True,
            )
            tmp = result.output.decode("utf-8")
            response = tmp.encode("utf-8")
        except Exception as e:
            self.log(f"Error running container: {e}")
            response = str(e).encode("utf-8")
        return response

    def get_local_data_dir(self) -> str:
        """
        Get the local data directory.

        :return: Local data directory.
        """
        return self.plugin.window.core.config.get_user_dir("data")

    def is_docker_installed(self) -> bool:
        """
        Check if Docker is installed

        :return: True if installed
        """
        try:
            if self.client is None:
                client = docker.from_env()
                client.ping()
            return True
        except DockerException:
            return False

    def attach_signals(self, signals):
        """
        Attach signals

        :param signals: signals
        """
        self.signals = signals

    def log(self, msg: Any):
        """
        Log the message.

        :param msg: Message to log.
        """
        print(msg)

