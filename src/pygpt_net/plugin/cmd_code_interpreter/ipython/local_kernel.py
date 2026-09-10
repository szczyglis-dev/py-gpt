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
import re
import time
import threading

class LocalKernel:

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
        self.client = None
        self.manager = None
        self.initialized = False
        self._signals_local = threading.local()
        self.signals = None
        self._restart_lock = threading.Lock()
        self.restarting = False
        self.executing = False
        self.last_restart_at = 0.0

    def restart_kernel(self) -> bool:
        """
        Restart the IPython kernel. Duplicate restart requests immediately after
        a successful restart are treated as a no-op.

        :return: True if the kernel is ready after the request.
        """
        if not self._restart_lock.acquire(blocking=False):
            self.log("IPython kernel is already restarting; duplicate request ignored.")
            return False

        self.restarting = True
        try:
            if (
                    self.last_restart_at > 0
                    and time.monotonic() - self.last_restart_at < self.RESTART_COOLDOWN
                    and self.check_ready()):
                self.log("IPython kernel was restarted recently; duplicate restart skipped.")
                return True

            if self.manager is None:
                self.init(force=True)
                if not self.initialized:
                    return False
            else:
                try:
                    if self.client is not None:
                        self.client.stop_channels()
                except Exception:
                    pass
                self.manager.restart_kernel(now=True)
                self.client = self.manager.client()
                self.client.start_channels()
                self.client.wait_for_ready()
                self.initialized = True
                self._configure_noninteractive_shell()
                self.log("IPython kernel restarted.")

            self.last_restart_at = time.monotonic()
            return True
        except Exception as e:
            self.initialized = False
            self.log(f"Error restarting IPython kernel: {e}")
            return False
        finally:
            self.restarting = False
            self._restart_lock.release()

    def shutdown_kernel(self):
        """Shutdown the IPython kernel."""
        self.client.stop_channels()
        self.manager.shutdown_kernel()

    def init(self, force: bool = False):
        """
        Initialize the IPython kernel client.

        :param force: Force reinitialization.
        """
        from jupyter_client import KernelManager
        if self.initialized and not force:
            if self.check_ready():
                return
            self.log("IPython kernel heartbeat was lost. Reinitializing the kernel client...")
            self.initialized = False
            try:
                if self.client is not None:
                    self.client.stop_channels()
            except Exception:
                pass

        self.manager = KernelManager()
        self.manager.start_kernel()
        self.client = self.manager.client()
        self.client.start_channels()
        self.client.wait_for_ready()
        self.initialized = True
        self._configure_noninteractive_shell()
        self.log("Connected to local IPython kernel.")
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
        self.manager.shutdown_kernel()

    def check_ready(self):
        """
        Check whether the kernel is alive without requiring it to be idle.

        ``wait_for_ready()`` is intentionally not used here: a healthy kernel
        executing a long-running cell is busy and may not answer a kernel-info
        request immediately. Treating that state as a dead kernel caused false
        restart loops.
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
            auto_init: bool = False
    ) -> str:
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
            self.init()
        except Exception as e:
            self.initialized = False
            self.log(f"Error initializing IPython kernel: {e}")

        if not self.initialized or not self.check_ready():
            self.log("IPython kernel is unavailable before execution.")
            if not auto_init or not self.restart_kernel():
                self.send_output(self.NOT_READY_MSG)
                return self.NOT_READY_MSG

        if not current:
            if not self.restart_kernel():
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
                    recovered = auto_init and self.restart_kernel()
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
                    recovered = auto_init and not client_alive and self.restart_kernel()
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