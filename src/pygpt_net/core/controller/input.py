#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #
import json

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

from ..context import ContextItem
from ..dispatcher import Event
from ..utils import trans


class Input:
    def __init__(self, window=None):
        """
        Input controller

        :param window: Window instance
        """
        self.window = window
        self.locked = False
        self.force_stop = False
        self.generating = False

    def setup(self):
        """Set up input"""
        # stream
        if self.window.config.get('stream'):
            self.window.ui.nodes['input.stream'].setChecked(True)
        else:
            self.window.ui.nodes['input.stream'].setChecked(False)

        # send clear
        if self.window.config.get('send_clear'):
            self.window.ui.nodes['input.send_clear'].setChecked(True)
        else:
            self.window.ui.nodes['input.send_clear'].setChecked(False)

        # send with enter/shift/disabled
        mode = self.window.config.get('send_mode')
        if mode == 2:
            self.window.ui.nodes['input.send_shift_enter'].setChecked(True)
            self.window.ui.nodes['input.send_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(False)
        elif mode == 1:
            self.window.ui.nodes['input.send_enter'].setChecked(True)
            self.window.ui.nodes['input.send_shift_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(False)
        elif mode == 0:
            self.window.ui.nodes['input.send_enter'].setChecked(False)
            self.window.ui.nodes['input.send_shift_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(True)

        # cmd enabled
        if self.window.config.get('cmd'):
            self.window.ui.nodes['cmd.enabled'].setChecked(True)
        else:
            self.window.ui.nodes['cmd.enabled'].setChecked(False)

        # set focus to input
        self.window.ui.nodes['input'].setFocus()

    def toggle_stream(self, value):
        """
        Toggle stream

        :param value: value of the checkbox
        """
        self.window.config.set('stream', value)

    def toggle_cmd(self, value):
        """
        Toggle cmd enabled

        :param value: value of the checkbox
        """
        self.window.config.set('cmd', value)

    def toggle_send_clear(self, value):
        """
        Toggle send clear

        :param value: value of the checkbox
        """
        self.window.config.set('send_clear', value)

    def toggle_send_shift(self, value):
        """
        Toggle send with shift

        :param value: value of the checkbox
        """
        self.window.config.set('send_mode', value)

    def lock_input(self):
        """
        Lock input
        """
        self.locked = True
        self.window.ui.nodes['input.send_btn'].setEnabled(False)
        self.window.ui.nodes['input.stop_btn'].setVisible(True)

    def unlock_input(self):
        """
        Unlock input
        """
        self.locked = False
        self.window.ui.nodes['input.send_btn'].setEnabled(True)
        self.window.ui.nodes['input.stop_btn'].setVisible(False)

    def stop(self):
        """
        Stop input
        """
        event = Event('audio.input.toggle', {"value": False})
        self.window.controller.assistant_thread.force_stop = True
        self.window.dispatch(event)  # stop audio input
        self.force_stop = True
        self.window.app.gpt.stop()
        self.unlock_input()
        self.generating = False

    def send_text(self, text):
        """
        Send text to GPT

        :param text: text to send
        """
        self.window.set_status(trans('status.sending'))

        # prepare names
        self.window.log("User name: {}".format(self.window.config.get('user_name')))  # log
        self.window.log("AI name: {}".format(self.window.config.get('ai_name')))  # log

        # dispatch events
        event = Event('user.name', {
            'value': self.window.config.get('user_name'),
        })
        self.window.dispatch(event)
        user_name = event.data['value']

        event = Event('ai.name', {
            'value': self.window.config.get('ai_name'),
        })
        self.window.dispatch(event)
        ai_name = event.data['value']

        self.window.log("User name [after plugin: user_name]: {}".format(self.window.config.get('user_name')))  # log
        self.window.log("AI name [after plugin: ai_name]: {}".format(self.window.config.get('ai_name')))  # log

        # store history (input)
        if self.window.config.get('store_history') and text is not None and text.strip() != "":
            self.window.app.history.save(text)

        # get mode
        mode = self.window.config.get('mode')

        # clear
        self.window.app.gpt.file_ids = []  # file ids

        # upload new attachments if assistant mode
        if mode == 'assistant':
            is_upload = False
            num_uploaded = 0
            try:
                # it uploads only new attachments (not uploaded before to remote)
                attachments = self.window.app.attachments.get_all(mode)
                c = self.window.controller.assistant_files.count_upload_attachments(attachments)
                if c > 0:
                    is_upload = True
                    self.window.set_status(trans('status.uploading'))
                    num_uploaded = self.window.controller.assistant_files.upload_attachments(mode, attachments)
                    self.window.app.gpt.file_ids = self.window.app.attachments.get_ids(mode)
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
                    self.window.config.set('assistant_thread', self.window.controller.assistant_thread.create_thread())
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
            self.window.app.gpt.assistant_id = self.window.config.get('assistant')
            self.window.app.gpt.thread_id = ctx.thread

        # log
        self.window.log("Context: input: {}".format(ctx.dump()))

        # dispatch event
        event = Event('ctx.before')
        event.ctx = ctx
        self.window.dispatch(event)

        # log
        self.window.log("Context: input [after plugin: ctx.before]: {}".format(ctx.dump()))
        self.window.log("System: {}".format(self.window.app.gpt.system_prompt))

        # apply cfg, plugins
        self.window.app.gpt.user_name = ctx.input_name
        self.window.app.gpt.ai_name = ctx.output_name
        self.window.app.chain.user_name = ctx.input_name
        self.window.app.chain.ai_name = ctx.output_name

        # prepare system prompt
        sys_prompt = self.window.config.get('prompt')

        # dispatch event
        event = Event('system.prompt', {
            'value': sys_prompt,
        })
        self.window.dispatch(event)
        sys_prompt = event.data['value']

        # if commands enabled: append commands prompt
        if self.window.config.get('cmd'):
            sys_prompt += " " + self.window.app.command.get_prompt()

            # dispatch event
            event = Event('cmd.syntax', {
                'value': sys_prompt,
            })
            self.window.dispatch(event)
            sys_prompt = self.window.app.gpt.system_prompt = event.data['value']

        # set system prompt
        self.window.app.gpt.system_prompt = sys_prompt
        self.window.app.chain.system_prompt = sys_prompt

        # log
        self.window.log("System [after plugin: system.prompt]: {}".format(self.window.app.gpt.system_prompt))
        self.window.log("User name: {}".format(self.window.app.gpt.user_name))
        self.window.log("AI name: {}".format(self.window.app.gpt.ai_name))
        self.window.log("Appending input to chat window...")

        # append input to chat window
        self.window.controller.output.append_input(ctx)
        QApplication.processEvents()  # process events to update UI

        # async or sync mode
        stream_mode = self.window.config.get('stream')

        # disable stream mode for vision mode (tmp)
        if mode == "vision":
            stream_mode = False

        # call the model
        try:
            # set attachments (attachments are separated by mode)
            self.window.app.gpt.attachments = self.window.app.attachments.get_all(mode)

            # make API call
            try:
                # lock input
                self.lock_input()

                if mode == "langchain":
                    self.window.log("Calling LangChain...")  # log
                    ctx = self.window.app.chain.call(text, ctx, stream_mode)
                else:
                    self.window.log("Calling OpenAI API...")  # log
                    ctx = self.window.app.gpt.call(text, ctx, stream_mode)

                    if mode == 'assistant':
                        # get run ID and save it in ctx
                        self.window.app.context.append_run(ctx.run_id)

                        # handle assistant run
                        self.window.controller.assistant_thread.handle_run(ctx)

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
            print("Error sending text: " + str(e))
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
            if not self.window.app.context.is_ctx_initialized():
                current = self.window.app.context.current_ctx
                title = self.window.app.gpt.prepare_ctx_name(ctx)
                if title is not None and title != "":
                    self.window.controller.context.update_name(current, title)

    def handle_commands(self, ctx):
        """
        Handle plugin commands

        :param ctx: ContextItem
        """
        if ctx is not None and self.window.config.get('cmd'):
            cmds = self.window.app.command.extract_cmds(ctx.output)
            self.window.log("Executing commands...")
            self.window.set_status("Executing commands...")
            self.window.controller.plugins.apply_cmds(ctx, cmds)
            self.window.set_status("")

    def handle_response(self, ctx, mode, stream_mode=False):
        """
        Handle response from LLM

        :param ctx: ContextItem
        :param mode: mode
        :param stream_mode: async stream mode
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
                        self.window.controller.ui.update_tokens()  # update UI
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
            # dispatch event
            event = Event('ctx.after')
            event.ctx = ctx
            self.window.dispatch(event)

        # log
        if ctx is not None:
            self.window.log("Context: output [after plugin: ctx.after]: {}".format(ctx.dump()))
            self.window.log("Appending output to chat window...")

            # only append output if not in async stream mode, TODO: plugin output add
            if not stream_mode:
                self.window.controller.output.append_output(ctx)

            self.handle_complete(ctx)

    def handle_complete(self, ctx):
        """
        Handle completed context

        :param ctx: ContextItem
        """
        # save context
        mode = self.window.config.get('mode')
        self.window.app.context.post_update(mode)  # post update context, store last mode, etc.
        self.window.app.context.store()
        self.window.set_status(
            trans('status.tokens') + ": {} + {} = {}".format(ctx.input_tokens, ctx.output_tokens, ctx.total_tokens))

        # store history (output)
        if self.window.config.get('store_history') \
                and ctx.output is not None \
                and ctx.output.strip() != "":
            self.window.app.history.save(ctx.output)

    def user_send(self, text=None):
        """
        Send real user input

        :param text: input text
        """
        # dispatch event
        event = Event('user.send', {
            'value': text,
        })
        self.window.dispatch(event)
        text = event.data['value']
        self.send(text)

    def send(self, text=None):
        """
        Send input text to API

        :param text: input text
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
        self.window.controller.assistant_thread.force_stop = False
        self.force_stop = False
        self.window.set_status(trans('status.sending'))

        ctx = None
        if text is None:
            text = self.window.ui.nodes['input'].toPlainText().strip()

        self.window.log("Input text: {}".format(text))  # log

        # dispatch event
        event = Event('input.before', {
            'value': text,
        })
        self.window.dispatch(event)
        text = event.data['value']

        self.window.log("Input text [after plugin: input.before]: {}".format(text))  # log

        # allow empty input only for vision mode
        if len(text.strip()) > 0 \
                or (mode == 'vision' and self.window.controller.attachment.has_attachments(mode)):

            # clear input area if clear-on-send enabled
            if self.window.config.get('send_clear'):
                self.window.ui.nodes['input'].clear()

            # check API key
            if mode != 'langchain':
                if self.window.config.get('api_key') is None or self.window.config.get('api_key') == '':
                    self.window.controller.launcher.show_api_monit()
                    self.window.set_status("Missing API KEY!")
                    self.generating = False
                    return

            # init api key if defined later
            self.window.app.gpt.init()
            self.window.app.images.init()

            # prepare context, create new ctx if there is no contexts yet (first run)
            if len(self.window.app.context.contexts) == 0:
                self.window.app.context.new()
                self.window.controller.context.update()
                self.window.log("New context created...")  # log
            else:
                # check if current context is allowed for this mode, if now then create new
                self.window.controller.context.handle_allowed(mode)

            # process events to update UI
            QApplication.processEvents()

            # send input to API
            self.generating = True  # mark as generating (lock)
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

            # dispatch event
            event = Event('ctx.end')
            event.ctx = ctx
            self.window.dispatch(event)

            self.window.log("Context: output [after plugin: ctx.end]: {}".format(ctx.dump()))  # log
            self.window.controller.ui.update_tokens()  # update tokens counters

            # if reply from commands then send reply (as response JSON)
            if ctx.reply:
                self.window.controller.input.send(json.dumps(ctx.results))

            self.generating = False
            self.window.controller.ui.update()  # update UI
            return

        self.generating = False  # unlock as not generating
        self.window.controller.ui.update()  # update UI

    def append(self, text):
        """
        Append text to input

        :param text: text to append
        """
        cur = self.window.ui.nodes['input'].textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)
        s = str(text) + "\n"
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertBlock()
        self.window.ui.nodes['input'].setTextCursor(cur)  # Update visible cursor
