#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.27 05:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QApplication

from pygpt_net.core.access.events import AppEvent
from pygpt_net.core.dispatcher import Event
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Output:
    def __init__(self, window=None):
        """
        Output controller

        :param window: Window instance
        """
        self.window = window
        self.not_stream_modes = ['assistant', 'img']

    def handle(self, ctx: CtxItem, mode: str, stream_mode: bool = False):
        """
        Handle response from LLM

        :param ctx: CtxItem
        :param mode: mode
        :param stream_mode: stream mode
        """
        self.window.stateChanged.emit(self.window.STATE_BUSY)

        # if stream mode then append chunk by chunk
        stream_enabled = self.window.core.config.get("stream")  # global stream enabled
        if stream_mode:  # local stream enabled
            if mode not in self.not_stream_modes:
                self.append_stream(ctx, mode)

        # check if tool calls detected
        if ctx.tool_calls:
            # if not internal commands in a text body then append tool calls as commands (prevent double commands)
            if not self.window.core.command.has_cmds(ctx.output):
                self.window.core.command.append_tool_calls(ctx)  # append tool calls as commands
                if not isinstance(ctx.extra, dict):
                    ctx.extra = {}
                ctx.extra["tool_calls"] = ctx.tool_calls
                stream_mode = False  # disable stream mode, show tool calls at the end
                self.log("Tool call received...")
            else:  # prevent execute twice
                self.log("Ignoring tool call because command received...")

        # agent mode
        if mode == 'agent':
            self.window.controller.agent.flow.on_ctx_after(ctx)

        # event: context after
        event = Event(Event.CTX_AFTER)
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)

        self.log("Appending output to chat window...")

        # only append output if not in stream mode, TODO: plugin output add
        if not stream_mode:
            if stream_enabled:  # use global stream settings here to persist previously added input
                self.window.controller.chat.render.append_input(ctx, flush=True, node=True)
            self.window.controller.chat.render.append_output(ctx)
            self.window.controller.chat.render.append_extra(ctx, True)  # + icons

        self.handle_complete(ctx)

    def append_stream(self, ctx: CtxItem, mode: str):
        """
        Handle stream response from LLM

        :param ctx: CtxItem
        :param mode: mode
        """
        output = ""
        output_tokens = 0
        begin = True
        sub_mode = None  # sub mode for langchain (chat, completion)

        # get sub mode for langchain
        if mode == "langchain":
            model_config = self.window.core.models.get(
                self.window.core.config.get('model')
            )
            sub_mode = 'chat'
            # get available modes for langchain
            if 'mode' in model_config.langchain:
                if 'chat' in model_config.langchain['mode']:
                    sub_mode = 'chat'
                elif 'completion' in model_config.langchain['mode']:
                    sub_mode = 'completion'

        # chunks: stream begin
        self.window.controller.chat.render.stream_begin()

        response_mode = mode
        if mode == "agent":
            tmp_mode = self.window.core.agents.get_mode()
            if tmp_mode is not None and tmp_mode != "_":
                response_mode = tmp_mode

        # read stream
        try:
            if ctx.stream is not None:
                self.log("Reading stream...")  # log

                tool_calls = []

                for chunk in ctx.stream:
                    # if force stop then break
                    if self.window.controller.chat.input.stop:
                        break

                    response = None

                    # chat and vision
                    if response_mode == "chat" or response_mode == "vision":
                        if chunk.choices[0].delta and chunk.choices[0].delta.content is not None:
                            response = chunk.choices[0].delta.content
                        elif chunk.choices[0].delta and chunk.choices[0].delta.tool_calls:
                            tool_chunks = chunk.choices[0].delta.tool_calls
                            for tool_chunk in tool_chunks:
                                if len(tool_calls) <= tool_chunk.index:
                                    tool_calls.append(
                                        {
                                            "id": "",
                                            "type": "function",
                                            "function": {
                                                "name": "",
                                                "arguments": ""
                                            }
                                        }
                                    )
                                tool_call = tool_calls[tool_chunk.index]
                                if tool_chunk.id:
                                    tool_call["id"] += tool_chunk.id
                                if tool_chunk.function.name:
                                    tool_call["function"]["name"] += tool_chunk.function.name
                                if tool_chunk.function.arguments:
                                    tool_call["function"]["arguments"] += tool_chunk.function.arguments

                    # completion
                    elif response_mode == "completion":
                        if chunk.choices[0].text is not None:
                            response = chunk.choices[0].text

                    # llama_index
                    elif response_mode == "llama_index":
                        if chunk is not None:
                            response = chunk

                    # langchain (can provide different modes itself)
                    elif response_mode == "langchain":
                        if sub_mode == 'chat':
                            # if chat model response is an object
                            if chunk.content is not None:
                                response = chunk.content
                        elif sub_mode == 'completion':
                            # if completion response is string
                            if chunk is not None:
                                response = chunk

                    if response is not None:
                        if begin and response == "":  # prevent empty beginning
                            continue
                        output += response
                        output_tokens += 1
                        self.window.controller.chat.render.append_chunk(
                            ctx,
                            response,
                            begin,
                        )
                        QApplication.processEvents()  # process events to update UI after each chunk
                        begin = False

                # unpack and store tool calls
                if tool_calls:
                    self.window.core.command.unpack_tool_calls_chunks(ctx, tool_calls)

        except Exception as e:
            self.window.core.debug.log(e)

        self.window.controller.ui.update_tokens()  # update UI tokens

        # update ctx
        ctx.output = output
        ctx.set_tokens(ctx.input_tokens, output_tokens)

        # chunks: stream end
        self.window.controller.chat.render.stream_end()

        # log
        self.log("End of stream.")

    def handle_complete(self, ctx: CtxItem):
        """
        Handle completed context

        :param ctx: CtxItem
        """
        mode = self.window.core.config.get('mode')
        self.window.core.ctx.post_update(mode)  # post update context, store last mode, etc.
        self.window.core.ctx.store()
        self.window.controller.ctx.update_ctx()  # update current ctx info

        # update response tokens
        self.show_response_tokens(ctx)

        # store to history
        if self.window.core.config.get('store_history'):
            self.window.core.history.append(ctx, "output")

        # unlock input if not unlocked before
        unlock_input = True
        if mode == "agent" and (not self.window.controller.agent.flow.finished or self.window.controller.agent.flow.stop):
            unlock_input = False
        if unlock_input:
            self.window.controller.chat.common.unlock_input()

    def handle_cmd(self, ctx: CtxItem):
        """
        Handle commands and expert mentions

        :param ctx: CtxItem
        """
        mode = self.window.core.config.get('mode')
        stream_mode = self.window.core.config.get('stream')

        # extract expert mentions
        if self.window.controller.agent.experts.enabled():
            # re-send to master
            if ctx.sub_reply:
                self.window.core.ctx.update_item(ctx)
                self.window.core.experts.reply(ctx)
            else:
                # call experts
                if not ctx.reply:
                    mentions = self.window.core.experts.extract_calls(ctx)
                    if mentions:
                        num_calls = 0
                        self.log("Calling experts...")
                        self.window.controller.chat.render.end(stream=stream_mode)  # close previous render
                        for expert_id in mentions:
                            if not self.window.core.experts.exists(expert_id):
                                self.log("Expert not found: " + expert_id)
                                continue
                            self.log("Calling: " + expert_id)
                            ctx.sub_calls += 1
                            self.window.core.experts.call(
                                ctx,  # master ctx
                                expert_id,  # expert id
                                mentions[expert_id],  # query
                            )
                            num_calls += 1
                        if num_calls > 0:
                            return  # abort commands if expert call detected

        # extract commands
        cmds = self.window.core.command.extract_cmds(ctx.output)
        if len(cmds) > 0:
            ctx.cmds = cmds  # append commands to ctx
            self.log("Command call received...")
            # agent mode
            if mode == 'agent':
                commands = self.window.core.command.from_commands(cmds)  # pack to execution list
                self.window.controller.agent.flow.on_cmd(
                    ctx,
                    commands,
                )
                # check if agent flow is not finished
                if self.window.controller.agent.flow.finished:
                    pass
                    # allow to continue commands execution if agent flow is finished
                    # return

            # don't change status if only goal update command
            change_status = True
            if mode == 'agent':
                if len(cmds) == 1 and cmds[0]["cmd"] == "goal_update":
                    change_status = False

            # plugins
            if self.window.core.config.get('cmd'):
                if change_status:
                    self.log("Executing plugin commands...")
                    self.window.ui.status(trans('status.cmd.wait'))
                self.window.controller.plugins.apply_cmds(
                    ctx,
                    cmds,
                )
            else:
                self.window.controller.plugins.apply_cmds_inline(
                    ctx,
                    cmds,
                )

    def handle_end(self, ctx: CtxItem, mode: str, has_attachments: bool = False):
        """
        Handle context end (finish output)

        :param ctx: CtxItem
        :param mode: mode
        :param has_attachments: has attachments
        """
        # clear attachments after send, only if attachments has been provided before send
        if has_attachments:
            if self.window.core.config.get('attachments_send_clear'):
                self.window.controller.attachment.clear(True, auto=True)
                self.window.controller.attachment.update()
                self.log("Attachments cleared.")  # log

        if self.window.core.config.get("log.ctx"):
            self.log("Context: END: {}".format(ctx))
        else:
            self.log("Context: END.")

        # agent mode
        if mode == 'agent':
            agent_iterations = int(self.window.core.config.get("agent.iterations"))
            self.log("Agent: ctx end, iterations: {}".format(agent_iterations))
            self.window.controller.agent.flow.on_ctx_end(
                ctx,
                iterations=agent_iterations,
            )

        # event: context end
        event = Event(Event.CTX_END)
        event.ctx = ctx
        self.window.core.dispatcher.dispatch(event)
        self.window.controller.ui.update_tokens()  # update UI
        self.window.controller.chat.input.generating = False  # unlock

        if (mode not in self.window.controller.chat.input.no_ctx_idx_modes
                and not self.window.controller.agent.enabled()):
            self.window.controller.idx.on_ctx_end(ctx, mode=mode)  # update ctx DB index
            # disabled in agent mode here to prevent loops, handled in agent flow internally if agent mode

        self.log("End.")
        self.window.core.dispatcher.dispatch(AppEvent(AppEvent.CTX_END))  # app event

        # restore state to idle if no errors
        if self.window.state != self.window.STATE_ERROR:
            self.window.stateChanged.emit(self.window.STATE_IDLE)

    def show_response_tokens(self, ctx: CtxItem):
        """
        Update response tokens

        :param ctx: CtxItem
        """
        extra_data = ""
        if ctx.is_vision:
            extra_data = " (VISION)"
        self.window.ui.status(
            trans('status.tokens') + ": {} + {} = {}{}".
            format(
                ctx.input_tokens,
                ctx.output_tokens,
                ctx.total_tokens,
                extra_data,
            ))

    def log(self, data: any):
        """
        Log data to debug

        :param data: Data to log
        """
        self.window.core.debug.info(data)
