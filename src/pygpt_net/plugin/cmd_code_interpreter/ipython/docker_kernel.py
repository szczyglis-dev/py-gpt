#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 15:50:00                  #
# ================================================== #

import base64
import queue
import os
import json
import re
import time
import threading
import io
import tarfile

from pygpt_net.core.docker.docker import get_sandbox_user_ids

class DockerKernel:

    NOT_READY_MSG = (
        "IPython kernel is unavailable after automatic recovery. "
        "Do not restart it repeatedly; retry the execution once or report the error."
    )
    BUSY_MSG = (
        "IPython kernel is already executing another request. "
        "Wait for the current execution to finish or interrupt it; do not restart the kernel repeatedly."
    )
    RESTARTING_MSG = (
        "IPython kernel restart is already in progress. "
        "Wait for it to finish and retry the execution once; do not request another restart."
    )
    RECOVERED_MSG = (
        "IPython kernel stopped responding during execution and was restarted automatically. "
        "The interrupted code was not executed again; retry it once if appropriate."
    )
    RESTART_COOLDOWN = 10.0
    NONINTERACTIVE_SHELL_BOOTSTRAP = r"""
def _pygpt_make_system_noninteractive():
    import os
    import subprocess

    def _system(cmd):
        _ip = get_ipython()
        _expanded = _ip.var_expand(cmd, depth=1)
        _executable = None if os.name == "nt" else os.environ.get("SHELL")
        _exit_code = subprocess.call(
            _expanded,
            shell=True,
            executable=_executable,
            stdin=subprocess.DEVNULL,
        )
        if os.name != "nt" and _exit_code > 128:
            _exit_code = -(_exit_code - 128)
        _ip.user_ns["_exit_code"] = _exit_code
        if getattr(_ip, "system_raise_on_error", False) and _exit_code != 0:
            raise subprocess.CalledProcessError(_exit_code, cmd)

    return _system

get_ipython().system = _pygpt_make_system_noninteractive()
del _pygpt_make_system_noninteractive
"""

    def __init__(self, plugin = None):
        self.plugin = plugin
        self.kernel_file = ".interpreter.kernel.json"
        self.client = None
        self.container_name = "pygpt_ipython_kernel_container"
        self.image_name = "pygpt_ipython_kernel"
        self.initialized = False
        self._signals_local = threading.local()
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
        self._restart_lock = threading.Lock()
        self.restarting = False
        self.executing = False
        self.last_restart_at = 0.0

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
        import docker.errors
        client = self.get_docker_client()
        try:
            client.images.get(self.get_image_name())
            return True
        except docker.errors.ImageNotFound:
            return False

    def restart(self, ctx=None):
        """Restart the container."""
        self.restart_container(self.get_container_name(), ctx=ctx)

    def build_image(self):
        """Build the Docker image for the IPython kernel."""
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

    def init(
            self,
            force: bool = False,
            auto_init: bool = False,
            ctx=None) -> None:
        """
        Initialize the IPython kernel client.

        :param force: Force reinitialization.
        :param auto_init: Kept for caller compatibility; execute() owns automatic recovery.
        """
        from jupyter_client import BlockingKernelClient
        if self.initialized and not force:
            user_mode_current = self.is_container_user_mode_current(ctx=ctx)
            if user_mode_current and self.check_ready():
                return
            if not user_mode_current:
                self.log("IPython sandbox user mode changed. Reinitializing the container...")
            else:
                self.log("IPython kernel heartbeat was lost. Reinitializing the client...")
            try:
                if self.client is not None:
                    self.client.stop_channels()
            except Exception:
                pass
            self.initialized = False

        self.prepare_local_data_dir(ctx=ctx)
        self.start_container(self.get_container_name(), ctx=ctx)
        self.prepare_conn()
        self.client = BlockingKernelClient(connection_file=self.get_kernel_file_path())
        self.client.load_connection_file()
        self.client.start_channels()

        try:
            self.client.wait_for_ready()
        except RuntimeError as e:
            self.log(f"Error connecting to IPython kernel: {e}")
            self.initialized = False
            # Recovery is intentionally owned by execute(), so a single tool
            # call can trigger at most one automatic restart attempt.
            return

        self.initialized = True
        self._configure_noninteractive_shell()
        self.log("Connected to IPython kernel.")
        self.log("IPython kernel is ready.")

    def _configure_noninteractive_shell(self):
        """Make IPython !commands non-interactive as well as Python input()."""
        if self.client is None:
            return
        try:
            self.client.execute_interactive(
                self.NONINTERACTIVE_SHELL_BOOTSTRAP,
                silent=True,
                store_history=False,
                allow_stdin=False,
                timeout=5,
                output_hook=lambda _msg: None,
            )
        except Exception as e:
            self.log(f"Unable to configure non-interactive IPython shell: {e}")

    def prepare_local_data_dir(self, ctx=None):
        """
        Prepare the local data directory.
        """
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

    def prepare_conn(self):
        """Prepare the connection file."""
        ports = self.get_ports()
        conn = {
            "shell_port": int(ports["shell"]),
            "iopub_port": int(ports["iopub"]),
            "stdin_port": int(ports["stdin"]),
            "control_port": int(ports["control"]),
            "hb_port": int(ports["hb"]),
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
        import docker.errors
        client = self.get_docker_client()
        try:
            container = client.containers.get(name)
            container.stop()
            container.remove()
        except docker.errors.NotFound:
            self.log(f"Container '{name}' not found.")

    def run_container(self, name: str, ctx=None) -> bool:
        """
        Run the Docker container.

        :param name: Container name.
        :return: True if the container was started successfully, False otherwise.
        """
        import docker.errors
        client = self.get_docker_client()
        ports = self.get_ports()
        # at first, check for image
        if not self.is_image():
            self.build_image()

        # run the container
        try:
            print("Running container {}...".format(name))
            self.prepare_conn()
            local_data_dir = self.get_local_data_dir(ctx=ctx)
            kwargs = {
                "image": self.get_image_name(),
                "name": name,
                "ports": {
                    '5555/tcp': ports['shell'],
                    '5556/tcp': ports['iopub'],
                    '5557/tcp': ports['stdin'],
                    '5558/tcp': ports['control'],
                    '5559/tcp': ports['hb'],
                },
                # bind /data directory in container to the local data directory
                "volumes": {
                    local_data_dir: {
                        'bind': '/data',
                        'mode': 'rw',
                    }
                },
                "labels": self.get_container_labels(ctx=ctx),
                "detach": True,
            }
            user = self.get_container_user()
            if user:
                kwargs["user"] = user
            client.containers.run(
                **kwargs,
            )
            return True
        except docker.errors.APIError as e:
            self.log(f"Error running container: {e}")
            return False

    def start_container(self, name: str, ctx=None):
        """
        Start the Docker container.

        :param name: Container name.
        """
        import docker.errors
        client = self.get_docker_client()
        try:
            container = client.containers.get(name)
            container.reload()
            labels = container.attrs.get("Config", {}).get("Labels", {}) or {}
            expected = self.get_container_labels(ctx=ctx)
            if any(labels.get(key) != value for key, value in expected.items()):
                self.log(f"Container '{name}' sandbox runtime mapping changed. Recreating it...")
                if container.status == "running":
                    container.stop()
                    container.wait()
                container.remove()
                raise docker.errors.NotFound("Sandbox user mode changed")
            if container.status != "running":
                self.log(f"Container '{name}' is not running. Recreating it...")
                container.remove()
                raise docker.errors.NotFound("IPython container is not running")
        except docker.errors.NotFound:
            self.log(f"Container '{name}' not found. Creating new one...")
            self.log(f"Creating a new container: '{name}'...")
            self.run_container(name, ctx=ctx)
            self.log("Container has been started.")

    def restart_container(self, name: str, ctx=None):
        """
        Restart the Docker container.

        :param name: Container name.
        """
        import docker.errors
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
        self.run_container(name, ctx=ctx)
        self.log("Container has been started.")

    def get_conn_address(self) -> str:
        """
        Get the connection address.

        :return: Connection address.
        """
        return self.plugin.get_option_value('ipython_conn_addr')

    def get_run_as_root(self) -> bool:
        """Return whether the IPython sandbox should explicitly run as root."""
        return bool(self.plugin.get_option_value("ipython_run_as_root"))

    def is_container_user_mode_current(self, ctx=None) -> bool:
        """Check whether the running container matches the configured user mode."""
        import docker.errors
        try:
            container = self.get_docker_client().containers.get(self.get_container_name())
            container.reload()
            labels = container.attrs.get("Config", {}).get("Labels", {}) or {}
            expected = self.get_container_labels(ctx=ctx)
            return all(labels.get(key) == value for key, value in expected.items())
        except docker.errors.NotFound:
            return False
        except Exception:
            # Do not force a restart solely because inspection failed.
            return True

    def get_container_user(self):
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
        ports['shell'] = int(self.plugin.get_option_value('ipython_port_shell'))
        ports['iopub'] = int(self.plugin.get_option_value('ipython_port_iopub'))
        ports['stdin'] = int(self.plugin.get_option_value('ipython_port_stdin'))
        ports['control'] = int(self.plugin.get_option_value('ipython_port_control'))
        ports['hb'] = int(self.plugin.get_option_value('ipython_port_hb'))
        return ports

    def get_kernel_file_path(self) -> str:
        """
        Get the kernel file path.

        :return: Kernel file path.
        """
        return os.path.join(self.plugin.window.core.config.get_user_dir("tmp"), self.kernel_file)

    def get_local_data_dir(self, ctx=None) -> str:
        """
        Get the local data directory.

        :return: Local data directory.
        """
        return self.plugin.window.core.filesystem.get_data_dir(ctx=ctx)

    def execute_system(self, command: str, ctx=None) -> bytes:
        """
        Execute a shell command inside the same container as the IPython kernel.

        The command is run through /bin/sh so pipes, redirects and compound
        shell expressions behave like host-side shell execution.

        :param command: shell command to execute
        :return: combined stdout/stderr bytes
        """
        client = self.get_docker_client()
        name = self.get_container_name()

        try:
            self.prepare_local_data_dir(ctx=ctx)
            if not self.is_image():
                self.build_image()

            self.start_container(name, ctx=ctx)
            container = client.containers.get(name)
            container.reload()
            if container.status != "running":
                container.start()
                container.reload()

            result = container.exec_run(
                ["/bin/sh", "-c", command],
                stdin=False,
                stdout=True,
                stderr=True,
                workdir="/data",
            )
            return result.output or b""
        except Exception as e:
            self.log(f"Error executing command in IPython container: {e}")
            return str(e).encode("utf-8")

    def check_ready(self):
        """
        Check whether the kernel is alive without requiring it to be idle.

        A busy kernel may not answer ``wait_for_ready()`` quickly, so heartbeat
        liveness is used here to avoid treating normal execution as a crash.
        """
        try:
            return bool(self.client is not None and self.client.is_alive())
        except Exception as e:
            self.log(f"Error checking IPython kernel heartbeat: {e}")
            return False

    def execute(
            self,
            code: str,
            current: bool = False,
            auto_init: bool = False,
            ctx=None) -> str:
        """
        Execute the code in the IPython kernel.

        :param code: Python code to execute.
        :param current: Use the current kernel.
        :param auto_init: Automatically recover the kernel once if it is unavailable.
        :return: Output from the kernel.
        """
        if self.restarting:
            self.log("IPython kernel restart is already in progress; execution deferred.")
            self.send_output(self.RESTARTING_MSG)
            return self.RESTARTING_MSG

        if self.executing:
            self.log("IPython kernel is already executing another request.")
            return self.BUSY_MSG

        try:
            self.init(
                force=False,
                auto_init=auto_init,
                ctx=ctx,
            )
        except Exception as e:
            self.initialized = False
            self.log(f"Error initializing IPython kernel: {e}")

        if not self.initialized or not self.check_ready():
            self.log("IPython kernel is unavailable before execution.")
            if not auto_init or not self.restart_kernel(ctx=ctx):
                self.send_output(self.NOT_READY_MSG)
                return self.NOT_READY_MSG

        if not current:
            if not self.restart_kernel(ctx=ctx):
                self.send_output(self.NOT_READY_MSG)
                return self.NOT_READY_MSG

        self.log("Executing code: " + str(code)[:100] + "...")
        self.executing = True
        try:
            # Tool executions are non-interactive. Kernel-level input()/getpass()
            # is rejected by allow_stdin=False; !commands are configured with
            # stdin=DEVNULL when the kernel is initialized.
            client = self.client
            if client is None:
                self.send_output(self.NOT_READY_MSG)
                return self.NOT_READY_MSG
            msg_id = client.execute(code, allow_stdin=False)
            output = ""
            while True:
                try:
                    msg = client.get_iopub_msg(timeout=1)
                except queue.Empty:
                    # A one-second gap in IOPub output is normal for long-running
                    # code. Keep waiting while the execution client's heartbeat lives.
                    # If another thread restarted the kernel, never attach this old
                    # request to the newly created client.
                    if client is not self.client:
                        self.send_output(self.RECOVERED_MSG)
                        return self.RECOVERED_MSG
                    try:
                        client_alive = bool(client.is_alive())
                    except Exception:
                        client_alive = False
                    if client_alive:
                        continue
                    self.log("IPython kernel heartbeat was lost during execution.")
                    recovered = auto_init and self.restart_kernel(ctx=ctx)
                    result = self.RECOVERED_MSG if recovered else self.NOT_READY_MSG
                    self.send_output(result)
                    return result
                except Exception as e:
                    self.log(f"Error receiving IPython output: {e}")
                    if client is not self.client:
                        self.send_output(self.RECOVERED_MSG)
                        return self.RECOVERED_MSG
                    try:
                        client_alive = bool(client.is_alive())
                    except Exception:
                        client_alive = False
                    recovered = auto_init and not client_alive and self.restart_kernel(ctx=ctx)
                    result = self.RECOVERED_MSG if recovered else self.NOT_READY_MSG
                    self.send_output(result)
                    return result

                if msg['parent_header'].get('msg_id') != msg_id:
                    continue

                # receive binary image data
                if msg['msg_type'] in ['display_data', 'execute_result']:
                    data = msg['content'].get('data', {})
                    if 'image/png' in data:
                        b64_image = data['image/png']
                        binary_image = base64.b64decode(b64_image)
                        self.log("Received binary image data.")
                        if binary_image:
                            path_to_save = self.plugin.make_temp_file_path('png')
                            try:
                                with open(path_to_save, 'wb') as f:
                                    f.write(binary_image)
                                self.log(f"Image saved to: {path_to_save}")
                                self.send_output(path_to_save)
                                return str(path_to_save)
                            except Exception as e:
                                self.log(f"Error saving image: {e}")
                                self.send_output(f"Error saving image: {e}")
                                return f"Error saving image: {e}"

                chunk = str(self.process_message(msg))
                if chunk.strip() != "":
                    output += chunk
                    self.send_output(chunk)

                if (msg['msg_type'] == 'status' and
                        msg['content']['execution_state'] == 'idle'):
                    break

            return self.remove_ansi(output).strip()
        finally:
            self.executing = False

    def restart_kernel(self, ctx=None) -> bool:
        """Restart the kernel, suppressing duplicate restart bursts."""
        from jupyter_client import BlockingKernelClient
        if not self._restart_lock.acquire(blocking=False):
            self.log("Kernel is already restarting; duplicate request ignored.")
            return False

        self.restarting = True
        try:
            if (
                    self.last_restart_at > 0
                    and time.monotonic() - self.last_restart_at < self.RESTART_COOLDOWN
                    and self.check_ready()):
                self.log("IPython kernel was restarted recently; duplicate restart skipped.")
                return True

            self.send_output("Restarting...")
            self.restart_container(self.get_container_name(), ctx=ctx)

            if self.client is not None:
                try:
                    self.client.stop_channels()
                except Exception:
                    pass
                try:
                    self.client.close()
                except Exception:
                    pass

            self.prepare_conn()
            self.client = BlockingKernelClient(connection_file=self.get_kernel_file_path())
            self.client.load_connection_file()
            self.client.start_channels()
            self.client.wait_for_ready()
            self.initialized = True
            self._configure_noninteractive_shell()
            self.last_restart_at = time.monotonic()
            self.log("Connected to IPython kernel.")
            self.send_output("Restarted.")
            return True
        except Exception as e:
            self.initialized = False
            self.log(f"Error restarting IPython kernel: {e}")
            return False
        finally:
            self.restarting = False
            self._restart_lock.release()

    def send_output(self, output: str):
        """
        Send the output to the output.

        :param output: Output.
        :return: Output.
        """
        signals = self.signals
        if signals is None:
            return
        try:
            signals.ipython_output.emit(output)
        except RuntimeError:
            self.detach_signals(signals)

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

    def remove_ansi_more(self, text):
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

    def remove_ansi(self, text) -> str:
        """
        Clean the text from ANSI escape sequences.

        :param text: Text to clean.
        :return: Cleaned text.
        """
        ansi_escape = re.compile(
            r'''
            \x1B   # ESC
            (?:    # 7-bit C1 Fe
                [@-Z\\-_]
            |      # or 8-bit C1 Fe
                \[
                [0-?]*   # Parameter bytes
                [ -/]*   # Intermediate bytes
                [@-~]    # Final byte
            )
            ''',
            re.VERBOSE
        )
        return ansi_escape.sub('', text)

    @property
    def signals(self):
        """Return signals attached to the current worker thread."""
        return getattr(self._signals_local, "value", None)

    @signals.setter
    def signals(self, signals):
        self._signals_local.value = signals

    def attach_signals(self, signals):
        """Attach signals to the current worker thread."""
        self.signals = signals

    def detach_signals(self, signals=None):
        """Detach signals from the current worker thread if they still match."""
        current = self.signals
        if signals is None or current is signals:
            self.signals = None

    def log(self, msg):
        """
        Log the message.

        :param msg: Message to log.
        """
        print(msg)
        self.plugin.window.update_status(msg)