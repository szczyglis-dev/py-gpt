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

import re
from jupyter_client import KernelManager

class LocalKernel:
    def __init__(self, plugin = None):
        self.plugin = plugin
        self.client = None
        self.manager = None
        self.initialized = False
        self.signals = None

    def restart_kernel(self) -> bool:
        """
        Restart the IPython kernel.

        :return: True if successful.
        """
        if self.initialized:
            self.client.stop_channels()
            self.manager.restart_kernel(now=True)
            self.client = self.manager.client()
            self.client.start_channels()
            self.log("IPython kernel restarted.")
        else:
            self.init()
            self.log("IPython kernel started.")
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