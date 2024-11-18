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

import os
import json
import re
import docker
import io
import tarfile

from jupyter_client import BlockingKernelClient
from docker.errors import DockerException

class IPythonInterpreter:
    def __init__(self, plugin = None):
        self.plugin = plugin
        self.kernel_file = ".interpreter.kernel.json"
        self.client = None
        self.container_name = "pygpt_ipython_kernel_container"
        self.image_name = "pygpt_ipython_kernel"
        self.initialized = False
        self.key = "19749810-8febfa748186a01da2f7b28c"
        self.bind_address = "0.0.0.0"
        self.conn_address = "127.0.0.1"
        self.ports = {
            "shell": 5555,
            "iopub": 5556,
            "stdin": 5557,
            "control": 5558,
            "hb": 5559,
        }
        self.signals = None

    def get_dockerfile(self) -> str:
        """
        Get the Dockerfile for the IPython kernel container.

        :return: Dockerfile.
        """
        return self.plugin.get_option_value('ipython_dockerfile')

    def get_key(self) -> str:
        """
        Get the key for the IPython kernel.

        :return: Key.
        """
        return self.plugin.get_option_value('ipython_session_key')

    def get_image_name(self) -> str:
        """
        Get the image name for the IPython kernel.

        :return: Image name.
        """
        return self.plugin.get_option_value('ipython_image_name')

    def get_container_name(self) -> str:
        """
        Get the container name for the IPython kernel.

        :return: Container name.
        """
        return self.plugin.get_option_value('ipython_container_name')

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

    def is_image(self):
        """Check if the Docker image for the IPython kernel exists."""
        client = self.get_docker_client()
        try:
            client.images.get(self.get_image_name())
            return True
        except docker.errors.ImageNotFound:
            return False

    def build_image(self):
        """Build the Docker image for the IPython kernel."""
        client = self.get_docker_client()
        context = self.create_docker_context(self.get_dockerfile())
        self.log("Please wait... Building the Docker image...")
        image, logs = client.images.build(
            fileobj=context,
            custom_context=True,
            rm=True,
            tag=self.image_name,
        )
        for chunk in logs:
            if 'stream' in chunk:
                self.log(chunk['stream'].strip())

    def init(self, force: bool = False):
        """
        Initialize the IPython kernel client.

        :param force: Force reinitialization.
        """
        if self.initialized and not force:
            return
        self.prepare_local_data_dir()
        self.start_container(self.get_container_name())
        self.prepare_conn()
        self.client = BlockingKernelClient(connection_file=self.get_kernel_file_path())
        self.client.load_connection_file()
        self.client.start_channels()
        self.client.wait_for_ready()
        self.log("Connected to IPython kernel.")
        self.initialized = True
        self.log("IPython kernel is ready.")

    def prepare_local_data_dir(self):
        """
        Prepare the local data directory.
        """
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

    def prepare_conn(self):
        """Prepare the connection file."""
        ports = self.get_ports()
        conn = {
            "shell_port": ports["shell"],
            "iopub_port": ports["iopub"],
            "stdin_port": ports["stdin"],
            "control_port": ports["control"],
            "hb_port": ports["hb"],
            "ip": self.get_conn_address(),
            "key": self.get_key(),
            "transport": "tcp",
            "signature_scheme": "hmac-sha256"
        }
        with open(self.get_kernel_file_path(), "w") as f:
            json.dump(conn, f)

    def process_message(self, msg: dict) -> str:
        """
        Process the message from the IPython kernel.

        :param msg: Message from the IPython kernel.
        :return: Processed message.
        """
        msg_type = msg['msg_type']
        content = msg['content']
        if msg_type == 'stream':
            # standard output and error
            return content['text']
        elif msg_type == 'display_data':
            # display data
            data = content['data']
            if 'text/plain' in data:
                return data['text/plain']
        elif msg_type == 'execute_result':
            # execution result
            data = content['data']
            if 'text/plain' in data:
                return data['text/plain']
        elif msg_type == 'error':
            # execution errors
            return "Error executing code:" + "\n".join(content['traceback'])
        return ""

    def end(self, all: bool = False):
        """
        Stop the IPython kernel.

        :param all: Stop the container as well.
        """
        self.client.stop_channels()  # stop the client
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

    def run_container(self, name: str) -> bool:
        """
        Run the Docker container.

        :param name: Container name.
        :return: True if the container was started successfully, False otherwise.
        """
        client = self.get_docker_client()
        ports = self.get_ports()
        # at first, check for image
        if not self.is_image():
            self.build_image()

        # run the container
        try:
            local_data_dir = self.get_local_data_dir()
            client.containers.run(
                self.get_image_name(),
                name=name,
                ports={
                    '5555/tcp': ports['shell'],
                    '5556/tcp': ports['iopub'],
                    '5557/tcp': ports['stdin'],
                    '5558/tcp': ports['control'],
                    '5559/tcp': ports['hb'],
                },
                # bind /data directory in container to the local data directory
                volumes={
                    local_data_dir: {
                        'bind': '/data',
                        'mode': 'rw',
                    }
                },
                detach=True,
            )
            return True
        except docker.errors.APIError as e:
            self.log(f"Error running container: {e}")
            return False

    def start_container(self, name: str):
        """
        Start the Docker container.

        :param name: Container name.
        """
        client = self.get_docker_client()
        try:
            client.containers.get(name)
        except docker.errors.NotFound:
            self.log(f"Container '{name}' not found. Creating new one...")
            self.log(f"Creating a new container: '{name}'...")
            self.run_container(name)
            self.log("Container has been started.")

    def restart_container(self, name: str):
        """
        Restart the Docker container.

        :param name: Container name.
        """
        client = self.get_docker_client()
        try:
            container = client.containers.get(name)
            self.log(f"Stopping container '{name}'...")
            container.stop()
            container.remove()
            self.log(f"Container '{name}' has been stopped and removed.")
        except docker.errors.NotFound:
            self.log(f"Container '{name}' not found. Nothing stopped.")

        self.log(f"Creating a new container: '{name}'...")
        self.run_container(name)
        self.log("Container has been started.")

    def get_conn_address(self) -> str:
        """
        Get the connection address.

        :return: Connection address.
        """
        return self.plugin.get_option_value('ipython_conn_addr')

    def get_bind_address(self) -> str:
        """
        Get the bind address.

        :return: Bind address.
        """
        return self.bind_address

    def get_ports(self) -> dict:
        """
        Get the ports.

        :return: Ports.
        """
        ports = {}
        ports['shell'] = self.plugin.get_option_value('ipython_port_shell')
        ports['iopub'] = self.plugin.get_option_value('ipython_port_iopub')
        ports['stdin'] = self.plugin.get_option_value('ipython_port_stdin')
        ports['control'] = self.plugin.get_option_value('ipython_port_control')
        ports['hb'] = self.plugin.get_option_value('ipython_port_hb')
        return ports

    def get_kernel_file_path(self) -> str:
        """
        Get the kernel file path.

        :return: Kernel file path.
        """
        return os.path.join(self.plugin.window.core.config.get_user_dir("data"), self.kernel_file)

    def get_local_data_dir(self) -> str:
        """
        Get the local data directory.

        :return: Local data directory.
        """
        return os.path.join(self.plugin.window.core.config.get_user_dir("data"), "ipython")

    def execute(self, code: str, current: bool = False) -> str:
        """
        Execute the code in the IPython kernel.

        :param code: Python code to execute.
        :param current: Use the current kernel.
        :return: Output from the kernel.
        """
        self.init()
        if not current:
            self.restart_kernel()

        self.log("Executing code: " + str(code)[:100] + "...")

        msg_id = self.client.execute(code)
        output = ""
        while True:
            try:
                msg = self.client.get_iopub_msg(timeout=1)
            except:
                continue

            if msg['parent_header'].get('msg_id') != msg_id:
                continue

            chunk = str(self.process_message(msg))
            if chunk.strip() != "":
                output += chunk
                self.send_output(chunk)

            if (msg['msg_type'] == 'status' and
                    msg['content']['execution_state'] == 'idle'):
                break

        return self.remove_ansi(output).strip()

    def restart_kernel(self) -> bool:
        """
        Restart the IPython kernel and reconnect.

        :return: True if the kernel was restarted successfully, False otherwise.
        """
        self.send_output("Restarting...")
        self.restart_container(self.get_container_name())
        if self.client is not None:
            self.client.stop_channels()
        self.client = BlockingKernelClient(connection_file=self.get_kernel_file_path())
        self.client.load_connection_file()
        self.client.start_channels()
        self.client.wait_for_ready()
        self.log("Connected to IPython kernel.")
        self.send_output("Restarted.")
        return True

    def send_output(self, output: str):
        """
        Send the output to the output.

        :param output: Output.
        :return: Output.
        """
        if self.signals is not None:
            self.signals.ipython_output.emit(output)

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

    def run(self):
        """Run the IPython kernel. (debug console)"""
        try:
            self.init()

            # loop to send code to the kernel
            while True:
                code = input('>>> ')
                if code.strip() == 'exit':
                    break
                elif code.strip() == 'restart':
                    self.restart_kernel()
                    continue
                elif code.strip() in ['quit', 'exit', 'stop']:
                    self.stop_container(self.get_container_name())
                    break

                # send the execution request
                msg_id = self.client.execute(code)

                # get messages until execution is idle
                while True:
                    try:
                        msg = self.client.get_iopub_msg(timeout=1)
                    except:
                        continue

                    if msg['parent_header'].get('msg_id') != msg_id:
                        continue

                    # show output
                    output = str(self.process_message(msg)).strip()
                    if output:
                        print(output)

                    if (msg['msg_type'] == 'status' and
                            msg['content']['execution_state'] == 'idle'):
                        # execution is complete
                        break
        except KeyboardInterrupt:
            pass
        finally:
            if self.initialized:
                self.end()  # stop the client

    def remove_ansi(self, text):
        """
        Clean the text from ANSI escape sequences, carriage returns, and progress bars.

        :param text: Text to clean.
        :return: Cleaned text.
        """
        # Remove ANSI escape sequences
        ansi_escape = re.compile(r'''
            \x1B  # ESC
            (?:   # Start of sequence
                [@-Z\\-_]  # ESC [@ to ESC _ (7-bit C1 Control codes)
            |     # or
                \[  # ESC[
                [0-?]*  # Parameter bytes
                [ -/]*  # Intermediate bytes
                [@-~]   # Final byte
            )
        ''', re.VERBOSE)
        text = ansi_escape.sub('', text)

        # Split text into lines
        lines = text.split('\n')

        cleaned_lines = []
        for line in lines:
            # Handle carriage returns - keep only the text after the last '\r'
            if '\r' in line:
                line = line.split('\r')[-1]
            # Optionally, remove progress bar lines by detecting lines containing box-drawing characters
            # Skip the line if it contains box-drawing characters
            if re.search(r'[\u2500-\u257F]', line):
                continue  # Skip this line
            # Append the cleaned line
            cleaned_lines.append(line)
        # Reconstruct the text
        text = '\n'.join(cleaned_lines)
        return text

    def attach_signals(self, signals):
        """
        Attach signals

        :param signals: signals
        """
        self.signals = signals

    def log(self, msg):
        """
        Log the message.

        :param msg: Message to log.
        """
        print(msg)