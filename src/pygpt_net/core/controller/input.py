#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.04 19:00:00                  #
# ================================================== #
import json

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

from ..context import ContextItem
from ..history import History
from ..utils import trans


class Input:
    def __init__(self, window=None):
        """
        Input controller

        :param window: main window
        """
        self.window = window
        self.history = History(self.window.config)

    def setup(self):
        """Sets up input"""

        # stream
        if self.window.config.data['stream']:
            self.window.data['input.stream'].setChecked(True)
        else:
            self.window.data['input.stream'].setChecked(False)

        # send clear
        if self.window.config.data['send_clear']:
            self.window.data['input.send_clear'].setChecked(True)
        else:
            self.window.data['input.send_clear'].setChecked(False)

        # send with shift
        if self.window.config.data['send_shift_enter']:
            self.window.data['input.send_shift_enter'].setChecked(True)
            self.window.data['input.send_enter'].setChecked(False)
        else:
            self.window.data['input.send_enter'].setChecked(True)
            self.window.data['input.send_shift_enter'].setChecked(False)

        # cmd enabled
        if self.window.config.data['cmd']:
            self.window.data['cmd.enabled'].setChecked(True)
        else:
            self.window.data['cmd.enabled'].setChecked(False)

        # set focus to input
        self.window.data['input'].setFocus()

    def toggle_stream(self, value):
        """
        Toggles stream

        :param value: value of the checkbox
        """
        self.window.config.data['stream'] = value

    def toggle_cmd(self, value):
        """
        Toggles cmd enabled

        :param value: value of the checkbox
        """
        self.window.config.data['cmd'] = value

    def toggle_send_clear(self, value):
        """
        Toggles send clear

        :param value: value of the checkbox
        """
        self.window.config.data['send_clear'] = value

    def toggle_send_shift(self, value):
        """
        Toggles send with shift

        :param value: value of the checkbox
        """
        self.window.config.data['send_shift_enter'] = value

    def send_text(self, text):
        """
        Sends text to GPT

        :param text: text to send
        """
        self.window.statusChanged.emit(trans('status.sending'))

        # prepare names
        self.window.log("User name: {}".format(self.window.config.data['user_name']))  # log
        self.window.log("AI name: {}".format(self.window.config.data['ai_name']))  # log

        user_name = self.window.controller.plugins.apply('user.name', self.window.config.data['user_name'])
        ai_name = self.window.controller.plugins.apply('ai.name', self.window.config.data['ai_name'])

        self.window.log("User name [after plugin: user_name]: {}".format(self.window.config.data['user_name']))  # log
        self.window.log("AI name [after plugin: ai_name]: {}".format(self.window.config.data['ai_name']))  # log

        # store history (input)
        if self.window.config.data['store_history'] and text is not None and text.strip() != "":
            self.history.save(text)

        # get mode
        mode = self.window.config.data['mode']

        # upload new attachments if assistant mode
        if mode == 'assistant':
            self.window.set_status(trans('status.uploading'))
            try:
                self.window.controller.attachment.upload_to_assistant()
            except Exception as e:
                print(e)
                self.window.ui.dialogs.alert(str(e))
            self.window.set_status(trans('status.uploaded'))

        # create ctx item
        ctx = ContextItem()
        ctx.mode = mode
        ctx.set_input(text, user_name)
        ctx.set_output(None, ai_name)

        # log
        self.window.log("Context: input: {}".format(ctx.dump()))

        # apply plugins
        ctx = self.window.controller.plugins.apply('ctx.before', ctx)

        # log
        self.window.log("Context: input [after plugin: ctx.before]: {}".format(ctx.dump()))
        self.window.log("System: {}".format(self.window.gpt.system_prompt))

        # apply cfg, plugins
        self.window.gpt.user_name = ctx.input_name
        self.window.gpt.ai_name = ctx.output_name
        self.window.chain.user_name = ctx.input_name
        self.window.chain.ai_name = ctx.output_name

        # prepare system prompt
        sys_prompt = self.window.config.data['prompt']
        sys_prompt = self.window.controller.plugins.apply('system.prompt', sys_prompt)

        # if commands enabled: append commands prompt
        if self.window.config.data['cmd']:
            sys_prompt += " " + self.window.command.get_prompt()
            sys_prompt = self.window.gpt.system_prompt = self.window.controller.plugins.apply('cmd.syntax', sys_prompt)

        # set system prompt
        self.window.gpt.system_prompt = sys_prompt
        self.window.chain.system_prompt = sys_prompt

        # log
        self.window.log("System [after plugin: system.prompt]: {}".format(self.window.gpt.system_prompt))
        self.window.log("User name: {}".format(self.window.gpt.user_name))
        self.window.log("AI name: {}".format(self.window.gpt.ai_name))
        self.window.log("Appending input to chat window...")

        # append input to chat window
        self.window.controller.output.append_input(ctx)
        QApplication.processEvents()  # process events to update UI
        self.window.controller.ui.update()  # update UI

        # async or sync mode
        stream_mode = self.window.config.data['stream']

        # disable stream mode for vision mode (tmp)
        if mode == "vision":
            stream_mode = False

        # call the model
        try:
            # set attachments
            self.window.gpt.attachments = self.window.controller.attachment.attachments.get_list()

            # make API call
            try:
                if mode == "langchain":
                    self.window.log("Calling LangChain...")  # log
                    ctx = self.window.chain.call(text, ctx, stream_mode)
                else:
                    self.window.log("Calling OpenAI API...")  # log
                    ctx = self.window.gpt.call(text, ctx, stream_mode)

                if ctx is not None:
                    self.window.log("Context: output: {}".format(ctx.dump()))  # log
                else:
                    # error in call if ctx is None
                    self.window.log("Context: output: None")
                    self.window.ui.dialogs.alert(trans('status.error'))
                    self.window.set_status(trans('status.error'))

            except Exception as e:
                self.window.log("GPT output error: {}".format(e))  # log
                print("Error in send text (GPT call): " + str(e))
                self.window.ui.dialogs.alert(str(e))
                self.window.set_status(trans('status.error'))

            # if async stream mode
            if stream_mode:
                output = ""
                output_tokens = 0
                begin = True
                submode = None  # submode for langchain (chat, completion)

                # get submode for langchain
                if mode == "langchain":
                    cfg = self.window.config.get_model_cfg(self.window.config.data['model'])
                    submode = 'chat'
                    # get available modes for langchain
                    if 'langchain' in cfg:
                        if 'chat' in cfg['langchain']['mode']:
                            submode = 'chat'
                        elif 'completion' in cfg['langchain']['mode']:
                            submode = 'completion'

                # read stream
                try:
                    self.window.log("Reading stream...")  # log
                    for chunk in ctx.stream:
                        response = None
                        if mode == "chat" or mode == "vision" or mode == "assistant":
                            if chunk.choices[0].delta.content is not None:
                                response = chunk.choices[0].delta.content
                        elif mode == "completion":
                            if chunk.choices[0].text is not None:
                                response = chunk.choices[0].text

                        # langchain can provide different modes itself
                        elif mode == "langchain":
                            if submode == 'chat':
                                # if chat model response is object
                                if chunk.content is not None:
                                    response = chunk.content
                            elif submode == 'completion':
                                # if completion response is string
                                if chunk is not None:
                                    response = chunk

                        if response is not None:
                            # prevent empty begin
                            if begin and response == "":
                                continue
                            output += response
                            output_tokens += 1
                            self.window.controller.output.append_chunk(ctx, response, begin)
                            QApplication.processEvents()  # process events to update UI
                            self.window.controller.ui.update()  # update UI
                            begin = False

                except Exception as e:
                    # debug
                    # self.window.log("Stream error: {}".format(e))  # log
                    # print("Error in stream: " + str(e))
                    # self.window.ui.dialogs.alert(str(e))
                    pass

                self.window.controller.output.append("\n")  # append EOL
                self.window.log("End of stream.")  # log

                # update ctx
                if ctx is not None:
                    ctx.output = output
                    ctx.set_tokens(ctx.input_tokens, output_tokens)

            # apply plugins
            if ctx is not None:
                ctx = self.window.controller.plugins.apply('ctx.after', ctx)

            # log
            if ctx is not None:
                self.window.log("Context: output [after plugin: ctx.after]: {}".format(ctx.dump()))
                self.window.log("Appending output to chat window...")

                # only append output if not in async stream mode, TODO: plugin output add
                if not stream_mode:
                    self.window.controller.output.append_output(ctx)

                # save context
                self.window.gpt.context.store()
                self.window.set_status(
                    trans('status.tokens') + ": {} + {} = {}".format(ctx.input_tokens, ctx.output_tokens, ctx.total_tokens))

                # store history (output)
                if self.window.config.data['store_history'] and ctx.output is not None and ctx.output.strip() != "":
                    self.history.save(ctx.output)

        except Exception as e:
            self.window.log("Output error: {}".format(e))  # log
            print("Error in send text: " + str(e))
            self.window.ui.dialogs.alert(str(e))
            self.window.set_status(trans('status.error'))

        # if commands enabled: execute commands
        if ctx is not None and self.window.config.data['cmd']:
            cmds = self.window.command.extract_cmds(ctx.output)
            self.window.log("Executing commands...")
            self.window.set_status("Executing commands...")
            ctx = self.window.controller.plugins.apply_cmds(ctx, cmds)
            self.window.set_status("")

        return ctx

    def user_send(self, text=None):
        """Sends real user input"""
        text = self.window.controller.plugins.apply('user.send', text)
        self.send(text)

    def send(self, text=None):
        """
        Sends input text to API
        """
        self.window.statusChanged.emit(trans('status.sending'))

        ctx = None
        if text is None:
            text = self.window.data['input'].toPlainText().strip()

        self.window.log("Input text: {}".format(text))  # log
        text = self.window.controller.plugins.apply('input.before', text)

        self.window.log("Input text [after plugin: input.before]: {}".format(text))  # log

        if len(text.strip()) > 0:
            if self.window.config.data['send_clear']:
                self.window.data['input'].clear()

            # check API key
            if self.window.config.data['api_key'] is None or self.window.config.data['api_key'] == '':
                self.window.controller.launcher.show_api_monit()
                self.window.controller.ui.update()
                self.window.statusChanged.emit("")
                return

            # init api key if defined later
            self.window.gpt.init()
            self.window.images.init()

            # prepare context, create new if no contexts (first run)
            if len(self.window.gpt.context.contexts) == 0:
                self.window.gpt.context.new()
                self.window.controller.context.update()
                self.window.log("New context created...")  # log

            # process events to update UI
            QApplication.processEvents()

            # send to API
            if self.window.config.data['mode'] == 'img':
                ctx = self.window.controller.image.send_text(text)
            else:
                ctx = self.window.controller.input.send_text(text)
        else:
            self.window.statusChanged.emit("")

        # clear attachments after send if enabled
        if self.window.config.data['attachments_send_clear']:
            self.window.controller.attachment.clear(True)
            self.window.controller.attachment.update()

        if ctx is not None:
            self.window.log("Context: output: {}".format(ctx.dump()))  # log
            ctx = self.window.controller.plugins.apply('ctx.end', ctx)  # apply plugins
            self.window.log("Context: output [after plugin: ctx.end]: {}".format(ctx.dump()))  # log
            self.window.controller.ui.update()  # update UI

            # if reply from commands then send reply (as response JSON)
            if ctx.reply:
                self.window.controller.input.send(json.dumps(ctx.results))
                self.window.controller.ui.update()
            return

        self.window.controller.ui.update()  # update UI

    def append(self, text):
        """
        Appends text to input

        :param text: text to append
        """
        cur = self.window.data['input'].textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)
        s = str(text) + "\n"
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertBlock()
        self.window.data['input'].setTextCursor(cur)  # Update visible cursor
