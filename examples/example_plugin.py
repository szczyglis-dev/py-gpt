#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.19 23:00:00                  #
# ================================================== #

from pygpt_net.plugin.base import BasePlugin  # <-- every plugin must inherit from BasePlugin
from pygpt_net.item.ctx import CtxItem
from pygpt_net.core.dispatcher import Event


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "example_plugin"  # unique plugin id
        self.name = "Example Plugin"
        self.description = "Example description"
        self.allowed_cmds = [
            "funny_cmd",  # list of allowed commands to handle in this plugin
        ]
        self.init_options()  # initialize plugin options

    def init_options(self):
        """
        Initialize options

        See other plugins from `pygpt_net.plugin` for more examples how to define options with different types.

        You can define options here, for example:
        """
        self.add_option(
            "example_text_option",  # option name (key)
            type="text",  # option type (text, textarea, bool, int, float, dict, combo)
            value="Hello world",  # default value
            label="Example text option",  # option label
            description="Example description #1",  # option description
            tooltip="Example tooltip #1",  # option tooltip
        )
        self.add_option(
            "example_bool_option",  # option name (key)
            type="bool",  # option type (text, textarea, bool, int, float, dict, combo)
            value=True,  # default value
            label="Example boolean option",
            description="Example description #2",  # option description
            tooltip="Example tooltip #2",  # option tooltip
        )

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event here

        :param event: event object
        :param args: event args
        :param kwargs: event kwargs
        """
        name = event.name  # event name (str), e.g. Event.SYSTEM_PROMPT
        data = event.data  # event data (dict) - additional data, e.g. {'value': 'Some value here'}
        ctx = event.ctx  # event context (CtxItem) - current context item (input/output)

        # Tip: set debug level to DEBUG to see all events in the console output and in app.log file

        # You can handle all the events here, for example:

        # 1) event called when system prompt is prepared
        if name == Event.SYSTEM_PROMPT:

            # Tip:
            # when calculating system prompt tokens on input change (e.g. typing), this event is called multiple times.
            # silent param is provided in this event to avoid multiple logs when handling the same event multiple times.
            if "silent" not in data or not data["silent"]:
                print("Handling example SYSTEM_PROMPT event...")
                self.log("Handling example SYSTEM_PROMPT event...")  # use self.log() to log messages

            # example of handling options: you can modify the system prompt based on the plugin options
            if self.get_option_value("example_bool_option"):  # bool
                # modify the system prompt only if the option is enabled
                data['value'] = self.on_system_prompt(data['value'])

        # 2) event called when command syntax is prepared
        elif name == Event.CMD_SYNTAX:
            # Event.CMD_SYNTAX_INLINE is also available and do not require "Execute commands" to be enabled
            print("Handling example CMD_SYNTAX event...")
            self.cmd_syntax(data)

        # 3) event called when commands are executed
        elif name == Event.CMD_EXECUTE:
            # Event.CMD_INLINE is also available and do not require "Execute commands" to be enabled
            print("Handling example CMD_EXECUTE event...")
            self.cmd(ctx, data['commands'])

        # etc...
        # See the plugins in `pygpt_net.plugin` for a more examples how to handle rest of events.

        """
        All available events are defined in 'pygpt_net.core.dispatcher.Event' class:
        
        AI_NAME = "ai.name"
        AUDIO_INPUT_STOP = "audio.input.stop"
        AUDIO_INPUT_TOGGLE = "audio.input.toggle"
        AUDIO_OUTPUT_STOP = "audio.output.stop"
        AUDIO_OUTPUT_TOGGLE = "audio.output.toggle"
        AUDIO_READ_TEXT = "audio.read_text"
        CMD_EXECUTE = "cmd.execute"
        CMD_INLINE = "cmd.inline"
        CMD_SYNTAX = "cmd.syntax"
        CMD_SYNTAX_INLINE = "cmd.syntax.inline"
        CTX_AFTER = "ctx.after"
        CTX_BEFORE = "ctx.before"
        CTX_BEGIN = "ctx.begin"
        CTX_END = "ctx.end"
        CTX_SELECT = "ctx.select"
        DISABLE = "disable"
        ENABLE = "enable"
        FORCE_STOP = "force.stop"
        INPUT_BEFORE = "input.before"
        MODE_BEFORE = "mode.before"
        MODE_SELECT = "mode.select"
        MODEL_BEFORE = "model.before"
        MODEL_SELECT = "model.select"
        PLUGIN_SETTINGS_CHANGED = "plugin.settings.changed"
        PLUGIN_OPTION_GET = "plugin.option.get"
        POST_PROMPT = "post.prompt"
        PRE_PROMPT = "pre.prompt"
        SYSTEM_PROMPT = "system.prompt"
        UI_ATTACHMENTS = "ui.attachments"
        UI_VISION = "ui.vision"
        USER_NAME = "user.name"
        USER_SEND = "user.send"
        """

        # If you want to stop event propagation, you can use:
        # event.stop = True  # stop event propagation

    def on_system_prompt(self, prompt: str) -> str:
        """
        Example of handling SYSTEM_PROMPT event

        Method is called when SYSTEM_PROMPT event is dispatched and can be used to modify system prompt.
        E.g. add instruction for model to always append 'END OF RESPONSE.' message to the end of every text response.

        :param prompt: current system prompt
        :return: updated system prompt
        """
        prompt += "\n" + "ALWAYS append the \"END OF RESPONSE.\" message to the end of every response."
        return prompt

    def cmd_syntax(self, data: dict):
        """
        Example of handling CMD_SYNTAX event (commands syntax)

        Method is called when CMD_SYNTAX event is dispatched and can be used to add custom commands syntax.
        Syntax is a list of strings with commands syntax description.

        To call this command in the app just ask the model for: "Execute a funny command with a random funny query"

        :param data: event data dictionary
        """
        data['syntax'].append(
            '"funny_cmd": use it to show funny command response for a specified query. Params: "query"'
        )
        # you can register as many commands as you want, use the same syntax as above:
        # data['syntax'].append('"command_name": description. Params: "param1", "param2", "param3"')

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Example of handling CMD_EXECUTE event (commands execution)

        Method is called when CMD_EXECUTE event is dispatched and can be used to handle commands execution.
        List of commands called by model and its params is passed as cmds list.
        Every command is a dict with keys: "cmd" and "params".
        "cmd" is a command name, and "params" is a dict with command params.

        :param ctx: CtxItem object - context item with current input
        :param cmds: list of dictionaries with called commands and its params
        """
        # iterate over all called by the model commands
        for item in cmds:

            # first, check if this command is allowed and should be handled by this plugin
            if item["cmd"] in self.allowed_cmds:

                print("Handling example command:", item)

                self.log("Handling example command: " + str(item["cmd"]))  # use self.log() to log messages

                # handle specific command by its name
                if item["cmd"] == "funny_cmd":

                    # get command params (provided by model)
                    query = item["params"]["query"]

                    # prepare request to instruct model for which command is current response
                    request = {
                        "cmd": item["cmd"],
                    }

                    # prepare response data
                    data = "My example response for a funny query: " + query

                    # prepare response object
                    response = {
                        "request": request,  # request, must be provided in the "request" key
                        "result": data,  # response, must be provided in the "result" key
                    }

                    # append response object to results list
                    ctx.results.append(response)

                    # set reply flag to True to force sending response to the model
                    ctx.reply = True
