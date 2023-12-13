#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.13 19:00:00                  #
# ================================================== #
import os.path
import subprocess
from datetime import datetime

from ..base_plugin import BasePlugin


class Plugin(BasePlugin):
    def __init__(self):
        super(Plugin, self).__init__()
        self.id = "cmd_custom"
        self.name = "Command: Custom Commands"
        self.description = "Provides availability to create and execute custom commands"
        self.window = None
        self.order = 100
        self.init_options()

    def init_options(self):
        """
        Initializes options
        """
        keys = {
            "name": "text",
            "instruction": "text",
            "params": "text",
            "cmd": "text",
        }
        value = [
            {
                "name": "example_cmd",
                "instruction": "execute tutorial test command by replacing 'hello' and 'world' params with some funny "
                               "words",
                "params": "hello, world",
                "cmd": 'echo "Response from {hello} and {world} at {_time}"',
            },
        ]
        desc = "Add your custom commands here, use {placeholders} to receive params, you can also use predefined " \
               "placeholders: {_time}, {_date}, {_datetime}, {_file}, {_home) "
        tooltip = "See the documentation for more details about examples, usage and list of predefined placeholders"
        self.add_option("cmds", "dict", value,
                        "Your custom commands", desc, tooltip, keys=keys)

    def setup(self):
        """
        Returns available config options

        :return: config options
        """
        return self.options

    def attach(self, window):
        """
        Attaches window

        :param window: Window
        """
        self.window = window

    def on_user_send(self, text):
        """
        Event: On user send text

        :param text: Text
        :return: Text
        """
        return text

    def on_ctx_begin(self, ctx):
        """
        Event: On new context begin

        :param ctx: Context
        :return: Context
        """
        return ctx

    def on_ctx_end(self, ctx):
        """
        Event: On context end

        :param ctx: Context
        :return: Context
        """
        return ctx

    def on_system_prompt(self, prompt):
        """
        Event: On prepare system prompt

        :param prompt: Prompt
        :return: Prompt
        """
        return prompt

    def on_ai_name(self, name):
        """
        Event: On set AI name

        :param name: Name
        :return: Name
        """
        return name

    def on_user_name(self, name):
        """
        Event: On set username

        :param name: Name
        :return: Name
        """
        return name

    def on_enable(self):
        """Event: On plugin enable"""
        pass

    def on_disable(self):
        """Event: On plugin disable"""
        pass

    def on_input_before(self, text):
        """
        Event: Before input

        :param text: Text
        """
        return text

    def on_ctx_before(self, ctx):
        """
        Event: Before ctx

        :param ctx: Text
        """
        return ctx

    def on_ctx_after(self, ctx):
        """
        Event: After ctx

        :param ctx: ctx
        """
        return ctx

    def cmd_syntax(self, syntax):
        """
        Event: On cmd syntax prepare

        :param syntax: Syntax
        :return: Syntax
        """
        for item in self.options["cmds"]["value"]:
            syntax += '\n"{}": {}'.format(item["name"], item["instruction"])
            if item["params"] != "":
                params = self.extract_params(item["params"])
                if len(params) > 0:
                    syntax += ', params: "{}"'.format('", "'.join(params))
        return syntax

    def extract_params(self, text):
        """
        Extracts params from params string

        :param text: Text
        :return: Params list
        """
        params = []
        if text is None or text == "":
            return params
        params_list = text.split(",")
        for param in params_list:
            param = param.strip()
            if param == "":
                continue
            params.append(param)
        return params

    def cmd(self, ctx, cmds):
        """
        Event: On command

        :param ctx: Context
        :param cmds: Commands requests
        :return: Context
        """
        msg = None
        for item in cmds:
            for my_cmd in self.options["cmds"]["value"]:

                # prepare request item for result
                request_item = {"cmd": item["cmd"]}

                if my_cmd["name"] == item["cmd"]:
                    try:
                        # prepare command
                        command = my_cmd["cmd"]

                        # append system placeholders
                        command = command.replace("{_file}", os.path.dirname(os.path.realpath(__file__)))
                        command = command.replace("{_home}", self.window.config.path)
                        command = command.replace("{_date}", datetime.now().strftime("%Y-%m-%d"))
                        command = command.replace("{_time}", datetime.now().strftime("%H:%M:%S"))
                        command = command.replace("{_datetime}", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

                        # append custom params to command placeholders
                        if 'params' in my_cmd and my_cmd["params"].strip() != "":
                            # append params to command placeholders
                            params_list = self.extract_params(my_cmd["params"])
                            for param in params_list:
                                if param in item["params"]:
                                    command = command.replace("{" + param + "}", item["params"][param])

                        # check if command is not empty
                        if command is None or command == "":
                            msg = "Command is empty"
                            continue

                        # execute custom command
                        msg = "Running custom command: {}".format(command)
                        print(msg)
                        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                                   stderr=subprocess.PIPE)
                        stdout, stderr = process.communicate()
                        result = None
                        if stdout:
                            result = stdout.decode("utf-8")
                            print("Result (STDOUT): {}".format(result))
                        if stderr:
                            result = stderr.decode("utf-8")
                            print("Result (STDERR): {}".format(result))
                        if result is None:
                            result = "No result (STDOUT/STDERR empty)"
                        ctx.results.append({"request": request_item, "result": result})
                        ctx.reply = True  # send result message
                    except Exception as e:
                        msg = "Error: {}".format(e)
                        ctx.results.append({"request": request_item, "result": "Error {}".format(e)})
                        ctx.reply = True
                        print(msg)

        # update status
        if msg is not None:
            self.window.statusChanged.emit(msg)
        return ctx
