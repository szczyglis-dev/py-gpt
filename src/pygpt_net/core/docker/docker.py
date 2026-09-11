#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.04 14:55:00                  #
# ================================================== #

from typing import Optional, Any, Tuple
import os
import platform
import io
import tarfile
import textwrap


def _normalize_dockerfile(value: str) -> str:
    """Return a stable representation used to compare editable Dockerfiles."""
    if not isinstance(value, str):
        return ""
    value = textwrap.dedent(value).strip()
    return "\n".join(line.rstrip() for line in value.splitlines())


def migrate_default_dockerfile(plugin, option_name: str, legacy_default: str, new_default: str) -> bool:
    """
    Upgrade an unchanged stock Dockerfile without overwriting user customizations.

    :return: True when the option was migrated.
    """
    current = plugin.get_option_value(option_name)
    if _normalize_dockerfile(current) != _normalize_dockerfile(legacy_default):
        return False

    plugin.options[option_name]["value"] = new_default

    window = getattr(plugin, "window", None)
    if window is not None:
        cfg = window.core.config
        cfg.update_plugin_config(plugin.id, option_name, new_default)
        cfg.save()
    return True


def get_sandbox_user_ids() -> Tuple[int, int]:
    """Return UID/GID used by stock sandbox images.

    On Linux the IDs are matched to the desktop user so files created in bind
    mounts keep the correct host ownership. Docker Desktop on macOS/Windows
    handles bind-mount ownership through its VM/filesharing layer, so a stable
    unprivileged fallback is used there.
    """
    if platform.system() == "Linux" and hasattr(os, "getuid") and hasattr(os, "getgid"):
        uid = os.getuid()
        gid = os.getgid()
        if uid > 0 and gid > 0:
            return uid, gid
    return 1000, 1000

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
        import docker.errors as errors
        client = self.get_docker_client()
        try:
            client.images.get(self.get_image_name())
            return True
        except errors.ImageNotFound as e:
            print(e)
            return False

    def build_image(self):
        """Build the Docker image."""
        client = self.get_docker_client()
        context = self.create_docker_context(self.get_dockerfile())
        uid, gid = get_sandbox_user_ids()
        self.log("Please wait... Building the Docker image...")
        image, logs = client.images.build(
            fileobj=context,
            custom_context=True,
            rm=True,
            tag=self.get_image_name(),
            buildargs={
                "PYGPT_UID": str(uid),
                "PYGPT_GID": str(gid),
            },
        )
        for chunk in logs:
            if 'stream' in chunk:
                self.log(chunk['stream'].strip())

    def prepare_local_data_dir(self, ctx=None):
        """ Prepare the local data directory."""
        local_data_dir = self.get_local_data_dir(ctx=ctx)
        try:
            os.makedirs(local_data_dir)
        except FileExistsError:
            pass

    def get_docker_client(self):
        """
        Get the Docker client.

        :return: Docker client.
        """
        import docker
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
        import docker.errors as errors
        client = self.get_docker_client()
        try:
            container = client.containers.get(name)
            container.stop()
            container.remove()
        except errors.NotFound:
            self.log(f"Container '{name}' not found.")

    def create_container(self, name: str, ctx=None):
        """
        Create the Docker container.

        :param name: Container name.
        """
        import docker.errors as errors
        client = self.get_docker_client()
        image_name = self.get_image_name()
        entrypoint = self.get_entrypoint()
        volumes = self.get_volumes(ctx=ctx)
        ports = self.get_ports()
        labels = self.get_container_labels(ctx=ctx)
        user = self.get_container_user()

        try:
            container = client.containers.get(name)
            container.reload()
            current_mode = container.attrs.get("Config", {}).get("Labels", {}) or {}
            if any(current_mode.get(key) != value for key, value in labels.items()):
                if container.status == 'running':
                    container.stop()
                    container.wait()
                container.remove()
                raise errors.NotFound("Sandbox runtime mapping changed")
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
                    labels=labels,
                    **({"user": user} if user else {}),
                )
                container.start()
        except errors.NotFound:
            print(f"Container '{name}' not found. Creating a new one.")
            container = client.containers.create(
                image=image_name,
                name=name,
                volumes=volumes,
                ports=ports,
                tty=True,
                stdin_open=True,
                command=entrypoint,
                labels=labels,
                **({"user": user} if user else {}),
            )
            container.start()
        except Exception as e:
            self.log(f"Error creating container: {e}")

    def restart_container(self, name: str, ctx=None):
        """
        Restart the Docker container.

        :param name: Container name.
        """
        import docker.errors as errors
        client = self.get_docker_client()
        image_name = self.get_image_name()
        entrypoint = self.get_entrypoint()
        volumes = self.get_volumes(ctx=ctx)
        ports = self.get_ports()
        labels = self.get_container_labels(ctx=ctx)
        user = self.get_container_user()

        try:
            container = client.containers.get(name)
            container.reload()
            current_mode = container.attrs.get("Config", {}).get("Labels", {}) or {}
            if any(current_mode.get(key) != value for key, value in labels.items()):
                print(f"Container '{name}' sandbox runtime mapping changed. Recreating it.")
                if container.status == 'running':
                    container.stop()
                    container.wait()
                container.remove()
                container = None

            if container is None:
                status = None
            else:
                status = container.status
                print(f"Container '{name}' status: {status}")

            if status is None:
                pass

            elif status == 'running':
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
                    labels=labels,
                    **({"user": user} if user else {}),
                )
                container.start()
                container.reload()
                if container.status != 'running':
                    print(f"Container '{name}' did not start correctly. Status: {container.status}")
                else:
                    print(f"Container '{name}' started successfully.")

        except errors.NotFound:
            print(f"Container '{name}' not found. Creating a new one.")
            container = client.containers.create(
                image=image_name,
                name=name,
                volumes=volumes,
                ports=ports,
                tty=True,
                stdin_open=True,
                command=entrypoint,  # 'running'
                labels=labels,
                **({"user": user} if user else {}),
            )
            container.start()
            container.reload()
            if container.status != 'running':
                print(f"Container '{name}' did not start correctly. Status: {container.status}")
            else:
                print(f"Container '{name}' started successfully.")
        except Exception as e:
            print(f"Error restarting container '{name}': {e}")

    def restart(self, ctx=None):
        """Restart the Docker container."""
        self.restart_container(self.get_container_name(), ctx=ctx)

    def get_volumes(self, ctx=None) -> dict:
        """
        Get the volumes mappings.

        :return: Volumes mappings.
        """
        workdir = self.get_local_data_dir(ctx=ctx)
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

    def get_run_as_root(self) -> bool:
        """Return whether the sandbox should explicitly run as root."""
        options = getattr(self.plugin, "options", {}) or {}
        if "docker_run_as_root" not in options:
            return False
        return bool(self.plugin.get_option_value("docker_run_as_root"))

    def get_container_user(self) -> Optional[str]:
        """Return an explicit Docker user override, if required."""
        if self.get_run_as_root():
            return "0:0"
        return None

    def get_container_labels(self, ctx=None) -> dict:
        """Labels used to detect a sandbox user-mode change."""
        return {
            "pygpt.run_as_root": "true" if self.get_run_as_root() else "false",
            "pygpt.data_dir": os.path.normcase(os.path.realpath(self.get_local_data_dir(ctx=ctx))),
        }

    def execute(self, cmd: str, ctx=None) -> Optional[bytes]:
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
            self.create_container(name, ctx=ctx)
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

    def get_local_data_dir(self, ctx=None) -> str:
        """
        Get the local data directory.

        :return: Local data directory.
        """
        return self.plugin.window.core.filesystem.get_data_dir(ctx=ctx)

    def is_docker_installed(self) -> bool:
        """
        Check if Docker is installed

        :return: True if installed
        """
        import docker
        from docker.errors import DockerException
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
        self.plugin.window.update_status(msg)

