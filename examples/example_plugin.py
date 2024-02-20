#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.02.20 02:00:00                  #
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

        This method is called externally by event dispatcher every time when the event is dispatched.

        :param event: event object
        :param args: event args
        :param kwargs: event kwargs
        """
        name = event.name  # event name (str), e.g. Event.SYSTEM_PROMPT
        data = event.data  # event data (dict) - additional data, e.g. {'value': 'Some value here'}
        ctx = event.ctx  # event context (CtxItem) - current context item (input/output)

        # Tip:
        # Set Log level (in Settings / Developer) to DEBUG to see all events in the console output and in app.log file.

        # HANDLING EVENTS: you can handle all the events here, for example:

        # 1) event called when system prompt is prepared
        if name == Event.SYSTEM_PROMPT:
            # Tip:
            # When the system prompt tokens are recalculated due to an input change (for example, while typing),
            # this event is triggered multiple times. The silent parameter is provided in this event to avoid multiple
            # executions of the same code. Here, we are preventing from generating lots of logs when typing.
            if "silent" not in data or not data["silent"]:
                print("Handling example SYSTEM_PROMPT event...")
                self.log("Handling example SYSTEM_PROMPT event...")  # use self.log() to log messages
            else:
                # event called in silent mode, tokens calculation here, do not handle the event
                pass

            # example of handling plugin options: let's modify the system prompt, based on the plugin option value
            if self.get_option_value("example_bool_option"):  # bool
                # modify the system prompt only if the option is enabled
                data['value'] = self.on_system_prompt(data['value'])

        # 2) event called when command syntax is prepared (before input is sent to the model)
        elif name == Event.CMD_SYNTAX:
            # Event.CMD_SYNTAX_INLINE is also available and do not require "Execute commands" to be enabled
            print("Handling example CMD_SYNTAX event...")
            self.cmd_syntax(data)  # list of syntax items is available in data['syntax']

        # 3) event called when commands are executed (after model output is received)
        elif name == Event.CMD_EXECUTE:
            # Event.CMD_INLINE is also available and do not require "Execute commands" to be enabled
            print("Handling example CMD_EXECUTE event...")
            self.cmd(ctx, data['commands'])  # list of commands is available in data['commands']

        # etc...
        # See the plugins in `pygpt_net.plugin` for a more examples how to handle rest of events.

        """
        All available events are defined in 'pygpt_net.core.dispatcher.Event' class:

        Syntax: `event name` - triggered on, `event data` (data type):

        AI_NAME = "ai.name" - when preparing an AI name, `data['value']` (string, name of the AI assistant)
        AUDIO_INPUT_STOP = "audio.input.stop" - force stop audio input
        AUDIO_INPUT_TOGGLE = "audio.input.toggle" - when speech input is enabled or disabled, `data['value']` 
                             (bool, True/False)
        AUDIO_OUTPUT_STOP = "audio.output.stop" - force stop audio output
        AUDIO_OUTPUT_TOGGLE = "audio.output.toggle" - when speech output is enabled or disabled, `data['value']` 
                             (bool, True/False)
        AUDIO_READ_TEXT = "audio.read_text" - on text read with speech synthesis, `data['value']` (string)
        CMD_EXECUTE = "cmd.execute" - when a command is executed, `data['commands']` (list, commands and arguments)
        CMD_INLINE = "cmd.inline" - when an inline command is executed, `data['commands']` 
                     (list, commands and arguments)
        CMD_SYNTAX = "cmd.syntax" - when appending syntax for commands, `data['prompt'], data['syntax']` 
                     (string, list, prompt and list with commands usage syntax)
        CMD_SYNTAX_INLINE = "cmd.syntax.inline" - when appending syntax for commands (inline mode), `data['prompt'], 
                             data['syntax']` (string, list, prompt and list with commands usage syntax)
        CTX_AFTER = "ctx.after" - after the context item is sent, `ctx`
        CTX_BEFORE = "ctx.before" - before the context item is sent, `ctx`
        CTX_BEGIN = "ctx.begin" - when context item create, `ctx`
        CTX_END = "ctx.end" - when context item handling is finished, `ctx`
        CTX_SELECT = "ctx.select" - when context is selected on list, `data['value']` (int, ctx meta ID)
        DISABLE = "disable" - when the plugin is disabled, `data['value']` (string, plugin ID)
        ENABLE = "enable" - when the plugin is enabled, `data['value']` (string, plugin ID)
        FORCE_STOP = "force.stop" - on force stop plugins
        INPUT_BEFORE = "input.before" - upon receiving input from the textarea, `data['value']` 
                       (string, text to be sent)
        MODE_BEFORE = "mode.before" - before the mode is selected `data['value'], data['prompt']` 
                      (string, string, mode ID)
        MODE_SELECT = "mode.select" - on mode select `data['value']` (string, mode ID)
        MODEL_BEFORE = "model.before" - before the model is selected `data['value']` (string, model ID)
        MODEL_SELECT = "model.select" - on model select `data['value']` (string, model ID)
        PLUGIN_SETTINGS_CHANGED = "plugin.settings.changed" - on plugin settings update
        PLUGIN_OPTION_GET = "plugin.option.get" - on request for plugin option value `data['name'], data['value']` 
                            (string, any, name of requested option, value)
        POST_PROMPT = "post.prompt" - after preparing a system prompt, `data['value']` (string, system prompt)
        PRE_PROMPT = "pre.prompt" - before preparing a system prompt, `data['value']` (string, system prompt)
        SYSTEM_PROMPT = "system.prompt" - when preparing a system prompt, `data['value']` (string, system prompt)
        UI_ATTACHMENTS = "ui.attachments" - when the attachment upload elements are rendered, `data['value']` 
                         (bool, show True/False)
        UI_VISION = "ui.vision" - when the vision elements are rendered, `data['value']` (bool, show True/False)
        USER_NAME = "user.name" - when preparing a user's name, `data['value']` (string, name of the user)
        USER_SEND = "user.send" - just before the input text is sent, `data['value']` (string, input text)
        """

        # If you want to stop event propagation, you can use:
        # event.stop = True  # stop event propagation

    def on_system_prompt(self, prompt: str) -> str:
        """
        Example of handling SYSTEM_PROMPT event

        Method will call when SYSTEM_PROMPT event is dispatched and will be used to modify system prompt.
        E.g. add instruction for model to always append 'END OF RESPONSE.' message to the end of every text response.

        :param prompt: current system prompt
        :return: updated system prompt with additional instructions
        """
        prompt += "\n" + "ALWAYS append the \"END OF RESPONSE.\" message to the end of every response."
        return prompt

    def cmd_syntax(self, data: dict):
        """
        Example of handling CMD_SYNTAX event (commands syntax)

        Method will call when CMD_SYNTAX event is dispatched and will be used to add custom commands syntax.
        Syntax is a list of strings with command syntax descriptions.

        To call this command in the app just ask the model for: "Execute a funny command with a random funny query".
        Model will generate the command in JSON format, and after the response with command will be received,
        the Event.CMD_EXECUTE event will be dispatched with the command to be executed and its params.

        :param data: event data dictionary
        """
        data['syntax'].append(
            '"funny_cmd": use it to show funny command response for a specified query. Params: "query"'
        )
        # You can register as many commands as you want, use the same syntax as above:
        # data['syntax'].append('"command_name": description. Params: "param1", "param2", "param3"')

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Example of handling CMD_EXECUTE event (commands execution)

        Method will call when CMD_EXECUTE event is dispatched and will be used to handle commands execution.
        List of commands called by model and its params is passed as cmds list.
        Every command item is a dict with keys: "cmd" and "params".
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

                    # prepare request object to instruct the model for which command is current response
                    request = {
                        "cmd": item["cmd"],
                    }

                    # prepare example response data
                    data = "My example response for a funny query: " + query

                    # create response object
                    response = {
                        "request": request,  # request, must be provided in the "request" key
                        "result": data,  # response, must be provided in the "result" key
                    }

                    # append response object to result list in the context item
                    ctx.results.append(response)

                    # Set the reply flag to True to force sending a response to the model.
                    # If the ctx.reply flag is set to True,
                    # then the response will be resent to the model as new input.
                    ctx.reply = True
