#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.23 19:00:00                  #
# ================================================== #

from datetime import datetime
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QApplication

from ..ctx_item import CtxItem
from ..dispatcher import Event
from ..utils import trans


class Output:
    def __init__(self, window=None):
        """
        Output controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup output"""
        self.window.ui.nodes['output.timestamp'].setChecked(self.window.config.get('output_timestamp'))

    def clear(self):
        """
        Clear output
        """
        self.window.ui.nodes['output'].clear()

    def append_context(self):
        """
        Append context to output
        """
        for item in self.window.app.ctx.items:
            self.append_context_item(item)

    def append_context_item(self, item):
        """
        Append context item to output

        :param item: context item
        """
        self.append_input(item)
        self.append_output(item)

    def append_input(self, item):
        """
        Append input to output

        :param item: context item
        """
        if item.input is None or item.input == "":
            return
        if self.window.config.get('output_timestamp') and item.input_timestamp is not None:
            name = ""
            if item.input_name is not None and item.input_name != "":
                name = item.input_name + " "
            ts = datetime.fromtimestamp(item.input_timestamp)
            hour = ts.strftime("%H:%M:%S")
            self.append("{}{}: > {}\n".format(name, hour, item.input))
        else:
            self.append("> {}\n".format(item.input))

    def append_output(self, item):
        """
        Append output to output

        :param item: context item
        """
        if item.output is None or item.output == "":
            return
        if self.window.config.get('output_timestamp') and item.output_timestamp is not None:
            name = ""
            if item.output_name is not None and item.output_name != "":
                name = item.output_name + " "
            ts = datetime.fromtimestamp(item.output_timestamp)
            hour = ts.strftime("%H:%M:%S")
            self.append("{}{}: {}".format(name, hour, item.output) + "\n")
        else:
            self.append(item.output + "\n")

    def append_chunk(self, item, text_chunk, begin=False):
        """
        Append output to output

        :param item: context item
        :param text_chunk: text chunk
        :param begin: if it is the beginning of the text
        """
        if text_chunk is None or text_chunk == "":
            return
        if begin and self.window.config.get('output_timestamp') and item.output_timestamp is not None:
            name = ""
            if item.output_name is not None and item.output_name != "":
                name = item.output_name + " "
            ts = datetime.fromtimestamp(item.output_timestamp)
            hour = ts.strftime("%H:%M:%S")
            self.append("{}{}: ".format(name, hour), "")

        self.append(text_chunk, "")

    def append(self, text, end="\n"):
        """
        Append text to output

        :param text: text to append
        :param end: end of the line character
        """
        cur = self.window.ui.nodes['output'].textCursor()  # Move cursor to end of text
        cur.movePosition(QTextCursor.End)
        s = str(text) + end
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertBlock()
        self.window.ui.nodes['output'].setTextCursor(cur)  # Update visible cursor

    def toggle_timestamp(self, value):
        """
        Toggle timestamp

        :param value: value of the checkbox
        """
        self.window.config.set('output_timestamp', value)
        self.window.config.save()
        self.window.controller.ctx.refresh()

    def handle_ctx_name(self, ctx):
        """
        Handle context name (summarize input and output)

        :param ctx: CtxItem
        """
        if ctx is not None:
            if not self.window.app.ctx.is_initialized():
                id = self.window.app.ctx.current
                self.window.controller.summarize.summarize_ctx(id, ctx)

    def handle_commands(self, ctx):
        """
        Handle plugin commands

        :param ctx: CtxItem
        """
        if ctx is not None and self.window.config.get('cmd'):
            cmds = self.window.app.command.extract_cmds(ctx.output)
            if len(cmds) > 0:
                self.window.log("Executing commands...")
                self.window.set_status(trans('status.cmd.wait'))
                self.window.controller.plugins.apply_cmds(ctx, cmds)

    def handle_response(self, ctx, mode, stream_mode=False):
        """
        Handle response from LLM

        :param ctx: CtxItem
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
                    if self.window.controller.input.force_stop:
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
                        self.append_chunk(ctx, response, begin)
                        QApplication.processEvents()  # process events to update UI
                        self.window.controller.ui.update_tokens()  # update UI
                        begin = False

            except Exception as e:
                self.window.app.error.log(e)
                # debug
                # self.window.log("Stream error: {}".format(e))  # log
                # print("Error in stream: " + str(e))
                # self.window.ui.dialogs.alert(str(e))
                pass

            self.append("\n")  # append EOL
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
            self.window.log("Context: output [after plugin: ctx.after]: {}".format(self.window.app.ctx.dump(ctx)))
            self.window.log("Appending output to chat window...")

            # only append output if not in async stream mode, TODO: plugin output add
            if not stream_mode:
                self.append_output(ctx)

            self.handle_complete(ctx)

    def handle_complete(self, ctx):
        """
        Handle completed context

        :param ctx: CtxItem
        """
        # save context
        mode = self.window.config.get('mode')
        self.window.app.ctx.post_update(mode)  # post update context, store last mode, etc.
        self.window.app.ctx.store()
        self.window.controller.ctx.update_ctx()  # update current ctx info
        self.window.set_status(
            trans('status.tokens') + ": {} + {} = {}".
            format(ctx.input_tokens, ctx.output_tokens, ctx.total_tokens))

        # store history (output)
        if self.window.config.get('store_history') \
                and ctx.output is not None \
                and ctx.output.strip() != "":
            self.window.app.history.save(ctx.output)

    def speech_selected_text(self, text):
        """
        Process selected text

        :param text: selected text
        """
        ctx = CtxItem()
        ctx.output = text
        all = False
        if self.window.controller.audio.is_output_enabled():
            event = Event('ctx.after')
        else:
            all = True
            event = Event('audio.read_text')  # to all plugins (even if disabled)
        event.ctx = ctx
        self.window.dispatch(event, all)
