#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.15 19:00:00                  #
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
        self.locked = False
        self.force_stop = False
        self.generating = False

    def setup(self):
        """Sets up input"""

        # stream
        if self.window.config.get('stream'):
            self.window.data['input.stream'].setChecked(True)
        else:
            self.window.data['input.stream'].setChecked(False)

        # send clear
        if self.window.config.get('send_clear'):
            self.window.data['input.send_clear'].setChecked(True)
        else:
            self.window.data['input.send_clear'].setChecked(False)

        # send with enter/shift/disabled
        mode = self.window.config.get('send_mode')
        if mode == 2:
            self.window.data['input.send_shift_enter'].setChecked(True)
            self.window.data['input.send_enter'].setChecked(False)
            self.window.data['input.send_none'].setChecked(False)
        elif mode == 1:
            self.window.data['input.send_enter'].setChecked(True)
            self.window.data['input.send_shift_enter'].setChecked(False)
            self.window.data['input.send_none'].setChecked(False)
        elif mode == 0:
            self.window.data['input.send_enter'].setChecked(False)
            self.window.data['input.send_shift_enter'].setChecked(False)
            self.window.data['input.send_none'].setChecked(True)

        # cmd enabled
        if self.window.config.get('cmd'):
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
        self.window.config.set('stream', value)

    def toggle_cmd(self, value):
        """
        Toggles cmd enabled

        :param value: value of the checkbox
        """
        self.window.config.set('cmd', value)

    def toggle_send_clear(self, value):
        """
        Toggles send clear

        :param value: value of the checkbox
        """
        self.window.config.set('send_clear', value)

    def toggle_send_shift(self, value):
        """
        Toggles send with shift

        :param value: value of the checkbox
        """
        self.window.config.set('send_mode', value)

    def lock_input(self):
        """
        Locks input
        """
        self.locked = True
        self.window.data['input.send_btn'].setEnabled(False)
        self.window.data['input.stop_btn'].setVisible(True)

    def unlock_input(self):
        """
        Unlocks input
        """
        self.locked = False
        self.window.data['input.send_btn'].setEnabled(True)
        self.window.data['input.stop_btn'].setVisible(False)

    def stop(self):
        """
        Stops input
        """
        self.window.controller.assistant.force_stop = True
        self.window.controller.plugins.dispatch('audio.input.toggle', False)  # stop audio input
        self.force_stop = True
        self.window.gpt.stop()
        self.unlock_input()
        self.generating = False

    def send_text(self, text):
        """
        Sends text to GPT

        :param text: text to send
        """
        self.window.statusChanged.emit(trans('status.sending'))

        # prepare names
        self.window.log("User name: {}".format(self.window.config.get('user_name')))  # log
        self.window.log("AI name: {}".format(self.window.config.get('ai_name')))  # log

        user_name = self.window.controller.plugins.apply('user.name', self.window.config.get('user_name'))
        ai_name = self.window.controller.plugins.apply('ai.name', self.window.config.get('ai_name'))

        self.window.log("User name [after plugin: user_name]: {}".format(self.window.config.get('user_name')))  # log
        self.window.log("AI name [after plugin: ai_name]: {}".format(self.window.config.get('ai_name')))  # log

        # store history (input)
        if self.window.config.get('store_history') and text is not None and text.strip() != "":
            self.history.save(text)

        # get mode
        mode = self.window.config.get('mode')

        # clear
        self.window.gpt.file_ids = []  # file ids

        # upload new attachments if assistant mode
        if mode == 'assistant':
            is_upload = False
            num_uploaded = 0
            try:
                # it uploads only new attachments (not uploaded before to remote)
                attachments = self.window.controller.attachment.attachments.get_all(mode)
                c = self.window.controller.assistant.count_upload_attachments(attachments)
                if c > 0:
                    is_upload = True
                    self.window.set_status(trans('status.uploading'))
                    num_uploaded = self.window.controller.assistant.upload_attachments(mode, attachments)
                    self.window.gpt.file_ids = self.window.controller.attachment.attachments.get_ids(mode)
                # show uploaded status
                if is_upload and num_uploaded > 0:
                    self.window.set_status(trans('status.uploaded'))
            except Exception as e:
                print(e)
                self.window.ui.dialogs.alert(str(e))

            # create or get current thread, it is required here
            if self.window.config.get('assistant_thread') is None:
                try:
                    self.window.set_status(trans('status.starting'))
                    self.window.config.set('assistant_thread', self.window.controller.assistant.create_thread())
                except Exception as e:
                    print(e)
                    self.window.ui.dialogs.alert(str(e))

        # create ctx item
        ctx = ContextItem()
        ctx.mode = mode
        ctx.set_input(text, user_name)
        ctx.set_output(None, ai_name)

        # store thread id, assistant id and pass to gpt wrapper
        if mode == 'assistant':
            ctx.thread = self.window.config.get('assistant_thread')
            self.window.gpt.assistant_id = self.window.config.get('assistant')
            self.window.gpt.thread_id = ctx.thread

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
        sys_prompt = self.window.config.get('prompt')
        sys_prompt = self.window.controller.plugins.apply('system.prompt', sys_prompt)

        # if commands enabled: append commands prompt
        if self.window.config.get('cmd'):
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
        stream_mode = self.window.config.get('stream')

        # disable stream mode for vision mode (tmp)
        if mode == "vision":
            stream_mode = False

        # call the model
        try:
            # set attachments (attachments are separated by mode)
            self.window.gpt.attachments = self.window.controller.attachment.attachments.get_all(mode)

            # make API call
            try:
                # lock input
                self.lock_input()

                if mode == "langchain":
                    self.window.log("Calling LangChain...")  # log
                    ctx = self.window.chain.call(text, ctx, stream_mode)
                else:
                    self.window.log("Calling OpenAI API...")  # log
                    ctx = self.window.gpt.call(text, ctx, stream_mode)

                    if mode == 'assistant':
                        # get run ID and save it in ctx
                        self.window.gpt.context.append_run(ctx.run_id)

                        # handle assistant run
                        self.window.controller.assistant.handle_run(ctx)

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

            # handle response (if no assistant mode)
            if mode != "assistant":
                self.handle_response(ctx, mode, stream_mode)

        except Exception as e:
            self.window.log("Output error: {}".format(e))  # log
            print("Error in send text: " + str(e))
            self.window.ui.dialogs.alert(str(e))
            self.window.set_status(trans('status.error'))

        # if commands enabled: post-execute commands (if no assistant mode)
        if mode != "assistant":
            self.handle_commands(ctx)
            self.unlock_input()

        # handle ctx name (generate title from summary if not initialized)
        if self.window.config.get('ctx.auto_summary'):
            self.handle_ctx_name(ctx)

        return ctx

    def handle_ctx_name(self, ctx):
        """
        Handle context name (summarize input and output)
        :param ctx: ContextItem
        """
        if ctx is not None:
            if not self.window.gpt.context.is_ctx_initialized():
                current = self.window.gpt.context.current_ctx
                title = self.window.gpt.prepare_ctx_name(ctx)
                if title is not None and title != "":
                    self.window.controller.context.update_name(current, title)

    def handle_commands(self, ctx):
        """
        Handle plugin commands

        :param ctx: ContextItem
        """
        if ctx is not None and self.window.config.get('cmd'):
            cmds = self.window.command.extract_cmds(ctx.output)
            self.window.log("Executing commands...")
            self.window.set_status("Executing commands...")
            self.window.controller.plugins.apply_cmds(ctx, cmds)
            self.window.set_status("")

    def handle_response(self, ctx, mode, stream_mode=False):
        """
        Handle response from LLM

        :param ctx: ContextItem
        :param mode: Mode
        :param stream_mode: Async stream mode
        """
        # if async stream mode
        if stream_mode and mode != 'assistant':
            output = ""
            output_tokens = 0
            begin = True
            submode = None  # submode for langchain (chat, completion)

            # get submode for langchain
            if mode == "langchain":
                cfg = self.window.config.get_model_cfg(self.window.config.get('model'))
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
                    # if force stop then break
                    if self.force_stop:
                        break

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

            # --- end of stream mode ---

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

            self.handle_complete(ctx)

    def handle_complete(self, ctx):
        """Handles completed context"""
        # save context
        self.window.gpt.context.store()
        self.window.set_status(
            trans('status.tokens') + ": {} + {} = {}".format(ctx.input_tokens, ctx.output_tokens, ctx.total_tokens))

        # store history (output)
        if self.window.config.get('store_history') and ctx.output is not None and ctx.output.strip() != "":
            self.history.save(ctx.output)

    def user_send(self, text=None):
        """Sends real user input"""
        text = self.window.controller.plugins.apply('user.send', text)
        self.send(text)

    def send(self, text=None):
        """
        Sends input text to API
        """
        # check if input is not locked
        if self.locked:
            return

        self.generating = True

        mode = self.window.config.get('mode')
        if mode == 'assistant':
            # check if assistant is selected
            if self.window.config.get('assistant') is None or self.window.config.get('assistant') == "":
                self.window.ui.dialogs.alert(trans('error.assistant_not_selected'))
                self.generating = False
                return
        elif mode == 'vision':
            # handle auto-capture mode
            if self.window.controller.camera.is_enabled():
                if self.window.controller.camera.is_auto():
                    self.window.controller.camera.capture_frame(False)

        # unlock Assistant run thread if locked
        self.window.controller.assistant.force_stop = False
        self.force_stop = False
        self.window.statusChanged.emit(trans('status.sending'))

        ctx = None
        if text is None:
            text = self.window.data['input'].toPlainText().strip()

        self.window.log("Input text: {}".format(text))  # log
        text = self.window.controller.plugins.apply('input.before', text)

        self.window.log("Input text [after plugin: input.before]: {}".format(text))  # log

        # allow empty input only for vision mode
        if len(text.strip()) > 0 \
                or (mode == 'vision' and self.window.controller.attachment.has_attachments(mode)):

            # clear input area if clear-on-send enabled
            if self.window.config.get('send_clear'):
                self.window.data['input'].clear()

            # check API key
            if self.window.config.get('api_key') is None or self.window.config.get('api_key') == '':
                self.window.controller.launcher.show_api_monit()
                self.window.controller.ui.update()
                self.window.statusChanged.emit("Missing API KEY!")
                self.generating = False
                return

            # init api key if defined later
            self.window.gpt.init()
            self.window.images.init()

            # prepare context, create new ctx if there is no contexts yet (first run)
            if len(self.window.gpt.context.contexts) == 0:
                self.window.gpt.context.new()
                self.window.controller.context.update()
                self.window.log("New context created...")  # log

            # process events to update UI
            QApplication.processEvents()

            # send input to API
            self.generating = True  # mark as generating
            if self.window.config.get('mode') == 'img':
                ctx = self.window.controller.image.send_text(text)
            else:
                ctx = self.window.controller.input.send_text(text)
        else:
            # reset status if input is empty
            self.window.statusChanged.emit("")

        # clear attachments after send if enabled
        if self.window.config.get('attachments_send_clear'):
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

            self.generating = False
            return

        self.window.controller.ui.update()  # update UI
        self.generating = False  # unlock as not generating

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
