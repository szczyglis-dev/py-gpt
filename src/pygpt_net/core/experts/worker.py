#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.23 15:00:00                  #
# ================================================== #

from typing import List, Optional

from PySide6.QtCore import QRunnable, QObject, Signal, Slot
from llama_index.core.tools import QueryEngineTool

from pygpt_net.core.types import (
    MODE_EXPERT,
    TOOL_EXPERT_CALL_NAME,
)
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import Event, KernelEvent, RenderEvent
from pygpt_net.item.ctx import CtxItem


class WorkerSignals(QObject):
    """Signals for worker to communicate with main thread."""
    finished = Signal()  # when worker is finished
    response = Signal(object, str)  # when worker has response
    error = Signal(str)  # when worker has error
    event = Signal(object)  # when worker has event to dispatch
    output = Signal(object, str)  # when worker has output to handle
    lock_input = Signal()  # when worker locks input for UI
    cmd = Signal(object, object, str, str, str)  # when worker has command to handle


class ExpertWorker(QRunnable):
    """Worker for handling expert calls in a separate thread."""

    def __init__(
            self,
            window,
            master_ctx: CtxItem,
            expert_id: str,
            query: str
    ):
        super().__init__()
        self.window = window
        self.master_ctx = master_ctx
        self.expert_id = expert_id
        self.query = query
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        master_ctx = self.master_ctx
        expert_id = self.expert_id
        query = self.query

        try:
            # get or create children (slave) meta
            slave = self.window.core.ctx.get_or_create_slave_meta(master_ctx, expert_id)
            expert = self.window.core.experts.get_expert(expert_id)  # preset
            reply = True
            hidden = False
            internal = False

            if self.window.core.experts.agent_enabled():  # hide in agent mode
                internal = False
                hidden = True

            mode = self.window.core.config.get("mode")
            base_mode = mode
            model = expert.model
            expert_name = expert.name
            ai_name = ""
            sys_prompt = expert.prompt
            model_data = self.window.core.models.get(model)

            files = []
            file_ids = []
            functions = []
            tools_outputs = []

            # from current config
            max_tokens = self.window.core.config.get('max_output_tokens')
            stream_mode = self.window.core.config.get('stream')
            verbose = self.window.core.config.get('agent.llama.verbose')
            use_agent = self.window.core.config.get('experts.use_agent', False)
            db_idx = expert.idx  # get idx from expert preset

            mode = MODE_EXPERT  # force expert mode, mode will change in bridge

            # create slave item
            ctx = CtxItem()
            ctx.meta = slave  # use slave-meta
            ctx.internal = internal
            ctx.hidden = hidden
            ctx.current = True  # mark as current context item
            ctx.mode = mode  # store current selected mode (not inline changed)
            ctx.model = model  # store model list key, not real model id
            ctx.set_input(query, str(ai_name))
            ctx.set_output(None, expert_name)
            ctx.sub_call = True  # mark as sub-call
            ctx.pid = master_ctx.pid  # copy PID from parent to allow reply

            # render: begin
            event = RenderEvent(RenderEvent.BEGIN, {
                "meta": ctx.meta,
                "ctx": ctx,
                "stream": stream_mode,
            })
            self.signals.event.emit(event)  # dispatch render event
            self.window.core.ctx.provider.append_item(slave, ctx)  # to slave meta

            # build sys prompt
            sys_prompt_raw = sys_prompt  # store raw prompt
            event = Event(Event.PRE_PROMPT, {
                'mode': mode,
                'value': sys_prompt,
                'is_expert': True,
            })
            self.signals.event.emit(event)  # dispatch pre-prompt event
            sys_prompt = event.data['value']
            sys_prompt = self.window.core.prompt.prepare_sys_prompt(
                mode,
                model_data,
                sys_prompt,
                ctx,
                reply,
                internal,
                is_expert=True,  # mark as expert, blocks expert prompt append in plugin
            )

            # index to use
            use_index = False
            if self.window.core.idx.is_valid(db_idx):
                use_index = True
                self.window.core.experts.last_idx = db_idx  # store last index used in call
            else:
                self.window.core.experts.last_idx = None
            if use_index:
                index, llm = self.window.core.idx.chat.get_index(db_idx, model_data, stream=False)
            else:
                llm = self.window.core.idx.llm.get(model_data, stream=False)

            history = self.window.core.ctx.all(
                meta_id=slave.id
            )  # get history for slave ctx, not master ctx

            if use_agent:
                # call the agent (planner) with tools and index
                ctx.agent_call = True  # directly return tool call response
                ctx.use_agent_final_response = True  # use agent final response as output
                bridge_context = BridgeContext(
                    ctx=ctx,
                    history=history,
                    mode=mode,
                    parent_mode=base_mode,
                    model=model_data,
                    system_prompt=sys_prompt,
                    system_prompt_raw=sys_prompt_raw,
                    prompt=query,
                    stream=False,
                    attachments=files,
                    file_ids=file_ids,
                    assistant_id=self.window.core.config.get('assistant'),
                    idx=db_idx,
                    idx_mode=self.window.core.config.get('llama.idx.mode'),
                    external_functions=functions,
                    tools_outputs=tools_outputs,
                    max_tokens=max_tokens,
                    is_expert_call=True,  # mark as expert call
                    preset=expert,
                )
                extra = {}
                if use_index:
                    extra["agent_idx"] = db_idx

                tools = self.window.core.agents.tools.prepare(
                    bridge_context, extra, verbose=False, force=True)

                # remove expert_call tool from tools
                for tool in list(tools):
                    if tool.metadata.name == TOOL_EXPERT_CALL_NAME:
                        tools.remove(tool)

                result = self.call_agent(
                    context=bridge_context,
                    tools=tools,
                    ctx=ctx,
                    query=query,
                    llm=llm,
                    system_prompt=sys_prompt,
                    verbose=verbose,
                )
                ctx.reply = False  # reset reply flag, we handle reply here

                if not result:  # abort if bridge call failed
                    self.signals.finished.emit()
                    return
            else:
                # native func call
                if self.window.core.command.is_native_enabled(force=False, model=model):

                    # get native functions, without expert_call here
                    functions = self.window.core.command.get_functions(master_ctx.id)

                    # append retrieval tool if index is selected
                    if use_index:
                        retriever_tool = self.window.core.experts.get_retriever_tool()
                        func_list = self.window.core.command.cmds_to_functions([retriever_tool])
                        functions.append(func_list[0])  # append only first function

                # call bridge
                bridge_context = BridgeContext(
                    ctx=ctx,
                    history=history,
                    mode=mode,
                    parent_mode=base_mode,
                    model=model_data,
                    system_prompt=sys_prompt,
                    system_prompt_raw=sys_prompt_raw,
                    prompt=query,
                    stream=False,
                    attachments=files,
                    file_ids=file_ids,
                    assistant_id=self.window.core.config.get('assistant'),
                    idx=db_idx,
                    idx_mode=self.window.core.config.get('llama.idx.mode'),
                    external_functions=functions,
                    tools_outputs=tools_outputs,
                    max_tokens=max_tokens,
                    is_expert_call=True,  # mark as expert call
                    preset=expert,
                    force_sync=True,  # force sync call, no async bridge call
                    request=True,  # use normal request instead of quick call
                )

                self.signals.lock_input.emit()  # emit lock input signal
                event = KernelEvent(KernelEvent.CALL, {
                    'context': bridge_context,  # call using slave ctx history
                    'extra': {},
                })
                self.window.dispatch(event)
                result = event.data.get("response")
                # result: <tool>{"cmd": "read_file", "params": {"path": ["xxxx.txt"]}}</tool>
                # ctx:
                # input: please read the file xxx.txt
                # output: <tool>cmd read</tool>
                if not result and not ctx.tool_calls:  # abort if bridge call failed
                    self.signals.finished.emit()
                    return

            # handle output
            ctx.current = False  # reset current state
            ctx.output = result  # store expert output in their context

            self.window.core.ctx.update_item(ctx)

            ctx.from_previous()  # append previous result if exists
            ctx.clear_reply()  # reset results

            if not use_agent:
                ctx.sub_tool_call = True
                self.signals.cmd.emit(ctx, master_ctx, expert_id, expert_name, result)  # emit cmd signal
                # tool call here and reply to window, from <tool></tool>
                return

            # if command to execute then end here, and reply is returned to reply() above from stack, and ctx.reply = TRUE here
            ctx.from_previous()  # append previous result again before save
            self.window.core.ctx.update_item(ctx)  # update ctx in DB

            # if commands reply after bridge call, then stop (already handled in sync dispatcher)
            if ctx.reply:
                self.signals.finished.emit()
                return

            # make copy of ctx for reply, and change input name to expert name
            reply_ctx = CtxItem()
            reply_ctx.from_dict(ctx.to_dict())
            reply_ctx.meta = master_ctx.meta

            # assign expert output
            reply_ctx.output = result
            reply_ctx.input_name = expert_name
            reply_ctx.output_name = ""
            reply_ctx.cmds = []  # clear cmds
            reply_ctx.sub_call = True  # this flag is not copied in to_dict

            # reply to main thread

            # send to reply()
            # input: something (no tool results here)
            # output: ... (call the master)
            self.signals.response.emit(reply_ctx, str(expert_id))  # emit response signal

        except Exception as e:
            self.window.core.debug.log(e)
            self.signals.error.emit(str(e))

        finally:
            self.signals.finished.emit()
            self.cleanup()

    def call_agent(
            self,
            context: BridgeContext,
            tools: Optional[List[QueryEngineTool]] = None,
            ctx: Optional[CtxItem] = None,
            query: str = "",
            llm=None,
            system_prompt: str = "",
            verbose: bool = False,

    ) -> str:
        """
        Call agent with tools and index

        :param context: Bridge context
        :param tools: Tools
        :param ctx: CtxItem
        :param query: Input prompt
        :param llm: LLM provider
        :param system_prompt: System prompt to use for agent
        :param verbose: Verbose mode, default is False
        :return: Response from agent as string
        """
        history = self.window.core.agents.memory.prepare(context)
        bridge_context = BridgeContext(
            ctx=ctx,
            system_prompt=system_prompt,
            model=context.model,
            prompt=query,
            stream=False,
            is_expert_call=True,  # mark as expert call
        )
        extra = {
            "agent_provider": "react",  # use react workflow provider
            "agent_idx": context.idx,  # index to use
            "agent_tools": tools,  # tools to use
            "agent_history": history,  # already prepared history
        }
        response_ctx = self.window.core.agents.runner.call_once(
            context=bridge_context,
            extra=extra,
            signals=None,
        )
        if response_ctx:
            return str(response_ctx.output)
        else:
            return "No response from expert."

    def cleanup(self):
        """Cleanup resources after worker execution."""
        sig = self.signals
        self.signals = None
        if sig is not None:
            try:
                sig.deleteLater()
            except RuntimeError:
                pass