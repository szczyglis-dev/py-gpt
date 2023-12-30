#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.30 02:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QApplication

from pygpt_net.core.dispatcher import Event
from pygpt_net.utils import trans


class Output:
    def __init__(self, window=None):
        """
        Output controller

        :param window: Window instance
        """
        self.window = window

    def setup(self):
        """Setup output"""
        self.window.ui.nodes['output.timestamp'].setChecked(self.window.core.config.get('output_timestamp'))

    def toggle_timestamp(self, value):
        """
        Toggle timestamp

        :param value: value of the checkbox
        """
        self.window.core.config.set('output_timestamp', value)
        self.window.core.config.save()
        self.window.controller.ctx.refresh()

    def handle_ctx_name(self, ctx):
        """
        Handle context name (summarize input and output)

        :param ctx: CtxItem
        """
        if ctx is not None:
            if not self.window.core.ctx.is_initialized():
                id = self.window.core.ctx.current
                self.window.controller.summarize.summarize_ctx(id, ctx)

    def handle_commands(self, ctx):
        """
        Handle plugin commands

        :param ctx: CtxItem
        """
        if ctx is not None and self.window.core.config.get('cmd'):
            cmds = self.window.core.command.extract_cmds(ctx.output)
            if len(cmds) > 0:
                ctx.cmds = cmds  # append to ctx
                self.window.controller.debug.log("Executing commands...")
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
                config = self.window.core.models.get(self.window.core.config.get('model'))
                submode = 'chat'
                # get available modes for langchain
                if 'mode' in config.langchain:
                    if 'chat' in config.langchain['mode']:
                        submode = 'chat'
                    elif 'completion' in config.langchain['mode']:
                        submode = 'completion'

            # read stream
            try:
                if ctx.stream is not None:
                    self.window.controller.debug.log("Reading stream...")  # log
                    for chunk in ctx.stream:
                        # if force stop then break
                        if self.window.controller.chat.input.force_stop:
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
                            self.window.controller.chat.render.append_chunk(ctx, response, begin)
                            self.window.controller.ui.update_tokens()  # update UI
                            QApplication.processEvents()  # process events to update UI
                            begin = False

            except Exception as e:
                self.window.core.debug.log(e)

            self.window.controller.chat.render.append("\n")  # append EOL
            self.window.controller.debug.log("End of stream.")  # log

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
            self.window.core.dispatcher.dispatch(event)

        # log
        if ctx is not None:
            self.window.controller.debug.log("Context: output [after plugin: ctx.after]: {}".
                                             format(self.window.core.ctx.dump(ctx)))
            self.window.controller.debug.log("Appending output to chat window...")

            # only append output if not in async stream mode, TODO: plugin output add
            if not stream_mode:
                self.window.controller.chat.render.append_output(ctx)

            self.handle_complete(ctx)

    def handle_complete(self, ctx):
        """
        Handle completed context

        :param ctx: CtxItem
        """
        # save context
        mode = self.window.core.config.get('mode')
        self.window.core.ctx.post_update(mode)  # post update context, store last mode, etc.
        self.window.core.ctx.store()
        self.window.controller.ctx.update_ctx()  # update current ctx info
        self.window.set_status(
            trans('status.tokens') + ": {} + {} = {}".
            format(ctx.input_tokens, ctx.output_tokens, ctx.total_tokens))

        # store history (output)
        if self.window.core.config.get('store_history'):
            self.window.core.history.append(ctx, "output")
