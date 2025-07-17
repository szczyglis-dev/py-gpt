#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.10 20:00:00                  #
# ================================================== #
import base64
import re
import time

from jupyter_client import KernelManager

class LocalKernel:

    NOT_READY_MSG = "IPython kernel is not initialized... try to restart the kernel with: /restart"

    def __init__(self, plugin = None):
        self.plugin = plugin
        self.client = None
        self.manager = None
        self.initialized = False
        self.signals = None
        self.restarting = False

    def restart_kernel(self) -> bool:
        """
        Restart the IPython kernel.

        :return: True if successful.
        """
        if self.restarting:
            self.log("IPython kernel is already restarting.")
            return False

        self.restarting = True
        if self.initialized:
            self.client.stop_channels()
            self.manager.restart_kernel(now=True)
            self.client = self.manager.client()
            self.client.start_channels()
            self.log("IPython kernel restarted.")
        else:
            self.init()
            self.log("IPython kernel started.")
        self.client.wait_for_ready()
        self.restarting = False
        return True

    def shutdown_kernel(self):
        """Shutdown the IPython kernel."""
        self.client.stop_channels()
        self.manager.shutdown_kernel()

    def init(self, force: bool = False):
        """
        Initialize the IPython kernel client.

        :param force: Force reinitialization.
        """
        if self.initialized and not force:
            return
        self.manager = KernelManager()
        self.manager.start_kernel()
        self.client = self.manager.client()
        self.client.start_channels()
        self.client.wait_for_ready()
        self.log("Connected to local IPython kernel.")
        self.initialized = True
        self.log("IPython kernel is ready.")

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
        Check if the IPython kernel is ready.

        :return: True if the kernel is ready, False otherwise.
        """
        try:
            if self.client is not None:
                self.client.wait_for_ready(timeout=1)
                return True
        except Exception as e:
            self.log(f"Error checking IPython kernel readiness: {e}")
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
        :param auto_init: Automatically initialize the kernel if not initialized after error.
        :return: Output from the kernel.
        """
        self.init()
        if not self.initialized:
            self.log("IPython kernel is not initialized.")
            self.send_output(self.NOT_READY_MSG)
            return self.NOT_READY_MSG

        if not current:
            self.restart_kernel()
            time.sleep(1)

        self.log("Executing code: " + str(code)[:100] + "...")

        if not self.check_ready():
            self.log("IPython kernel is not ready.")
            self.send_output(self.NOT_READY_MSG)
            return self.NOT_READY_MSG

        msg_id = self.client.execute(code)
        output = ""
        while True:
            try:
                msg = self.client.get_iopub_msg(timeout=1)
            except:
                break

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
                        with open(path_to_save, 'wb') as f:
                            f.write(binary_image)
                        self.log(f"Image saved to: {path_to_save}")
                        self.send_output(path_to_save)
                        return str(path_to_save)

            chunk = str(self.process_message(msg))
            if chunk.strip() != "":
                output += chunk
                self.send_output(chunk)

            if (msg['msg_type'] == 'status' and
                    msg['content']['execution_state'] == 'idle'):
                break

        return self.remove_ansi(output).strip()

    def send_output(self, output: str):
        """
        Send the output to the output.

        :param output: Output.
        :return: Output.
        """
        if self.signals is not None:
            self.signals.ipython_output.emit(output)

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