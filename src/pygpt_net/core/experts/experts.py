#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.03 14:00:00                  #
# ================================================== #

import json
from typing import Dict, List, Optional

from PySide6.QtCore import QRunnable, QObject, Signal, Slot
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.tools import QueryEngineTool

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_EXPERT,
    MODE_LANGCHAIN,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_AUDIO,
    MODE_RESEARCH,
)
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import Event, KernelEvent, RenderEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.preset import PresetItem
from pygpt_net.utils import trans


class Experts:
    def __init__(self, window=None):
        """
        Experts core

        :param window: Window instance
        """
        self.window = window
        self.allowed_modes = [
            MODE_CHAT,
            MODE_COMPLETION,
            MODE_VISION,
            # MODE_LANGCHAIN,
            MODE_LLAMA_INDEX,
            MODE_AUDIO,
            MODE_RESEARCH,
        ]
        self.allowed_cmds = ["expert_call"]
        self.worker = None
        self.last_expert_id = None  # last expert id used in call
        self.master_ctx = None  # master meta for expert calls

    def get_mode(self) -> str:
        """
        Get sub-mode to use internally

        :return: sub-mode
        """
        mode = MODE_CHAT
        current = self.window.core.config.get("experts.mode")
        if current is not None and current in self.allowed_modes:
            mode = current
        return mode

    def stopped(self) -> bool:
        """
        Check if experts are stopped

        :return: True if stopped
        """
        return self.window.controller.kernel.stopped()

    def agent_enabled(self) -> bool:
        """
        Check if agent is enabled

        :return: True if enabled
        """
        return self.window.controller.agent.legacy.enabled()

    def exists(self, id: str) -> bool:
        """
        Check if expert exists

        :param id: expert id
        :return: True if exists
        """
        return self.window.core.presets.has(MODE_EXPERT, id)

    def get_expert(self, id: str) -> PresetItem:
        """
        Get expert by id

        :param id: expert id
        :return: expert item (preset)
        """
        return self.window.core.presets.get_by_id(MODE_EXPERT, id)

    def get_experts(self) -> Dict[str, PresetItem]:
        """
        Get experts names with keys

        :return: experts dict
        """
        experts = {}
        presets = self.window.core.presets.get_by_mode(MODE_EXPERT)

        # mode: agent
        if self.agent_enabled():
            agents = self.window.core.presets.get_by_mode(MODE_AGENT)
            agent = self.window.core.config.get('preset')
            if agent is not None:
                if agent in agents:
                    for uuid in agents[agent].experts:
                        expert = self.window.core.presets.get_by_uuid(uuid)
                        if expert is not None:
                            id = expert.filename
                            experts[id] = expert
        # mode: expert
        else:
            for k in presets:
                if k.startswith("current."):  # skip current
                    continue
                if not presets[k].enabled:  # skip disabled experts
                    continue
                experts[k] = presets[k]
        return experts

    def get_expert_name_by_id(self, id: str) -> str:
        """
        Get expert name by id

        :param id: expert id
        :return: expert name
        """
        experts = self.get_experts()
        if id in experts:
            return experts[id].name

    def count_experts(self, uuid: str) -> int:
        """
        Count experts in agent

        :param uuid: agent uuid
        :return: number of experts
        """
        i = 0
        agents = self.window.core.presets.get_by_mode(MODE_AGENT)
        if uuid in agents:
            for expert_uuid in agents[uuid].experts:
                expert = self.window.core.presets.get_by_uuid(expert_uuid)
                if expert is not None:
                    i += 1
        return i

    def get_prompt(self) -> str:
        """
        Get prompt for handle experts

        :return: prompt with list of experts appended
        """
        prompt = self.window.core.config.get('prompt.expert')
        experts = self.get_experts()
        experts_list = []
        for k in experts:
            if k.startswith("current."):  # skip current presets
                continue
            if experts[k].description.strip() == "":
                experts_list.append(" - " + str(k) + ": " + str(experts[k].name))
            else:
                experts_list.append(" - " + str(k) + ": " + str(experts[k].name) + " (" + experts[k].description + ")")
        return prompt.replace("{presets}", "\n".join(experts_list))

    def extract_calls(self, ctx: CtxItem) -> Dict[str, str]:
        """
        Extract expert calls from context output

        :param ctx: context item
        :return: dict with calls
        """
        ids = self.get_experts().keys()
        if not ids:  # abort if no experts
            return {}
        cmds = self.window.core.command.extract_cmds(ctx.output)
        if len(cmds) > 0:
            ctx.cmds = cmds  # append commands to ctx
        else:  # abort if no cmds
            return {}
        commands = self.window.core.command.from_commands(cmds)  # pack to execution list
        is_cmd = False
        my_commands = []
        calls = {}
        for item in commands:
            if item["cmd"] in self.allowed_cmds:
                my_commands.append(item)
                is_cmd = True
        if not is_cmd:  # abort if no expert calls
            return {}
        for item in my_commands:
            try:
                if item["cmd"] == "expert_call":
                    if "params" not in item:
                        continue
                    if "id" not in item["params"] or "query" not in item["params"]:
                        continue
                    id = item["params"]["id"]
                    if id not in ids:
                        continue
                    query = item["params"]["query"]
                    calls[id] = query
            except Exception as e:
                self.window.core.debug.error(e)
                return {}
        return calls

    def reply(self, ctx: CtxItem):
        """
        Re-send response from commands to master expert

        If command has been called by expert then response for command is send here to parent

        :param ctx: context item
        """
        if self.stopped():
            return

        # master meta is here, ctx.meta = MASTER META ID here!

        # make copy of ctx for reply, and change input name to expert name
        reply_ctx = CtxItem()
        reply_ctx.from_dict(ctx.to_dict())
        expert_id = self.last_expert_id
        expert_name = ""
        if expert_id:
            expert_name = self.get_expert_name_by_id(expert_id)

        # reply ctx has no meta here!!!!
        reply_ctx.input_name = expert_name
        reply_ctx.output_name = ""
        reply_ctx.sub_call = True  # this flag is not copied in to_dict

        internal = False
        if self.agent_enabled():  # hide in agent mode
            internal = True
        if ctx.output.strip() != "":
            response = reply_ctx.output
        else:
            response = reply_ctx.input

        context = BridgeContext()
        context.ctx = reply_ctx
        result = {
            "expert_id": expert_id,
            "result": str(response),
        }
        context.prompt = str(response)
        if ctx.sub_reply:
            reply_ctx.extra["sub_reply"] = True  # mark as sub-reply
            context.prompt = json.dumps(result, ensure_ascii=False, indent=2)  # to master
        extra = {
            "force": True,
            "reply": True,
            "internal": internal,
        }
        event = KernelEvent(KernelEvent.INPUT_SYSTEM, {
            'context': context,
            'extra': extra,
        })
        self.window.dispatch(event)

    def call(
            self,
            master_ctx: CtxItem,
            expert_id: str,
            query: str
    ):
        """
        Call the expert

        :param master_ctx: master context
        :param expert_id: expert id (preset ID)
        :param query: input text (master prompt)
        """
        if self.stopped():
            return

        self.worker = ExpertWorker(
            window=self.window,
            master_ctx=master_ctx,
            expert_id=expert_id,
            query=query
        )
        self.worker.signals.response.connect(self.handle_response)  # connect to finished signal
        self.worker.signals.finished.connect(self.handle_finished)  # connect to finished signal
        self.worker.signals.error.connect(self.handle_error)  # connect to error signal
        self.worker.signals.event.connect(self.handle_event)  # connect to event signal
        self.worker.signals.output.connect(self.handle_output)  # connect to output signal
        self.worker.signals.lock_input.connect(self.handle_input_locked)  # connect to lock input signal
        self.worker.signals.cmd.connect(self.handle_cmd)  # connect to cmd signal

        # start worker in thread pool
        self.last_expert_id = expert_id  # store last expert id
        self.master_ctx = master_ctx
        expert_name = self.get_expert_name_by_id(expert_id)
        event = KernelEvent(KernelEvent.STATE_BUSY, {
            "msg": trans("expert.wait.status") + " ({})".format(expert_name),
        })
        self.window.dispatch(event)  # dispatch busy event
        self.window.threadpool.start(self.worker)

    @Slot(CtxItem, str)
    def handle_output(self, ctx: CtxItem, mode: str):
        """
        Handle output from worker

        :param ctx: CtxItem
        :param mode: mode of operation
        """
        if self.stopped():
            return

        self.window.controller.chat.output.handle(
            ctx=ctx,
            mode=mode,
            stream_mode=False,
        )

    @Slot(CtxItem, CtxItem, str, str, str)
    def handle_cmd(
            self,
            ctx: CtxItem,
            master_ctx: CtxItem,
            expert_id: str,
            expert_name: str,
            result: str
    ):
        """
        Handle command from worker

        :param ctx: CtxItem
        :param master_ctx: master context item
        :param expert_id: expert id
        :param expert_name: expert name
        :param result: result of command execution
        """
        if self.stopped():
            return

        # extract native tool calls if provided
        if ctx.tool_calls:
            # if not internal commands in a text body then append tool calls as commands (prevent double commands)
            if not self.window.core.command.has_cmds(ctx.output):
                self.window.core.command.append_tool_calls(ctx)  # append tool calls as commands
                if not isinstance(ctx.extra, dict):
                    ctx.extra = {}
                ctx.extra["tool_calls"] = ctx.tool_calls

        self.window.controller.chat.command.handle(ctx, internal=True)  # handle cmds sync
        if ctx.reply:
            self.window.update_status("")  # clear status

            # prepare data to send as reply
            tool_data = json.dumps(ctx.results)
            # if "tool_output" in ctx.extra and ctx.extra["tool_output"]:
               # tool_data = str(ctx.extra["tool_output"])

            self.window.core.ctx.update_item(ctx)  # update context in db
            self.window.update_status('...')
            ctx.output = "<tool>" + str(ctx.cmds) + "</tool>"
            self.window.core.ctx.update_item(ctx)  # update ctx in DB
            self.handle_finished()
            self.call(
                master_ctx=self.master_ctx,
                expert_id=self.last_expert_id,
                query=tool_data,
            )
            return

        # ----- no cmd reply ------ #

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
        self.handle_response(reply_ctx, str(expert_id))

    @Slot()
    def handle_input_locked(self):
        """
        Handle input locked signal from worker

        This is used to lock input in UI while worker is processing.
        """
        if self.stopped():
            return
        self.window.controller.chat.common.lock_input()

    @Slot(Event)
    def handle_event(self, event: Event):
        """
        Handle event from worker

        :param event: Event instance
        """
        if self.stopped():
            return
        self.window.dispatch(event)

    @Slot(str)
    def handle_error(self, error: str):
        """
        Handle worker error

        :param error: error message
        """
        if self.stopped():
            event = KernelEvent(KernelEvent.STATE_IDLE, {})
            self.window.dispatch(event)  # dispatch idle event
            return

        # handle error from worker
        context = BridgeContext()
        context.prompt = trans("expert.wait.failed") + ": " + str(error)
        extra = {
            "force": True,
            "reply": False,
            "internal": False,
        }
        # reply to master
        event = KernelEvent(KernelEvent.INPUT_SYSTEM, {
            'context': context,
            'extra': extra,
        })
        self.window.dispatch(event)
        event = KernelEvent(KernelEvent.STATE_IDLE, {})
        self.window.dispatch(event)  # dispatch idle event

    @Slot(CtxItem, str)
    def handle_finished(self):
        """Handle worker finished signal"""
        event = KernelEvent(KernelEvent.STATE_IDLE, {})
        self.window.dispatch(event)  # dispatch idle event


    @Slot(CtxItem, str)
    def handle_response(self, ctx: CtxItem, expert_id: str):
        """
        Handle response expert call

        :param ctx: CtxItem
        :param expert_id: expert id
        """
        if self.stopped():
            event = KernelEvent(KernelEvent.STATE_IDLE, {})
            self.window.dispatch(event)  # dispatch idle event
            return

        # handle reply from worker
        context = BridgeContext()
        context.ctx = ctx
        result = {
            "expert_id": expert_id,
            "result": str(ctx.output),
        }
        context.prompt = json.dumps(result, ensure_ascii=False, indent=2)  # prepare prompt for reply
        extra = {
            "force": True,
            "reply": True,
            "internal": False,
        }
        # reply to master
        event = KernelEvent(KernelEvent.INPUT_SYSTEM, {
            'context': context,
            'extra': extra,
        })
        self.window.dispatch(event)
        event = KernelEvent(KernelEvent.STATE_IDLE, {})
        self.window.dispatch(event)  # dispatch idle event

    def get_functions(self) -> List[Dict[str, str]]:
        """
        Append call the expert commands

        :return: call the expert commands
        """
        cmds = [
            {
                "cmd": "expert_call",
                "instruction": "Call the expert",
                "params": [
                    {
                        "name": "id",
                        "description": "expert id",
                        "required": True,
                        "type": "str",
                    },
                    {
                        "name": "query",
                        "description": "query to expert",
                        "required": True,
                        "type": "str",
                    }
                ]
            }
        ]
        return cmds

    def has_calls(self, ctx: CtxItem) -> bool:
        """
        Check if context has expert calls

        :param ctx: CtxItem
        """
        if not ctx.sub_reply and not ctx.reply:
            mentions = self.window.core.experts.extract_calls(ctx)
            if mentions:
                for expert_id in mentions:
                    if not self.window.core.experts.exists(expert_id):
                        continue
                    return True
        return False


class WorkerSignals(QObject):
    """
    Signals for worker to communicate with main thread.
    """
    finished = Signal()  # when worker is finished
    response = Signal(object, str)  # when worker has response
    error = Signal(str)  # when worker has error
    event = Signal(object)  # when worker has event to dispatch
    output = Signal(object, str)  # when worker has output to handle
    lock_input = Signal()  # when worker locks input for UI
    cmd = Signal(object, object, str, str, str)  # when worker has command to handle


class ExpertWorker(QObject, QRunnable):
    """Worker for handling expert calls in a separate thread."""
    def __init__(
            self,
            window,
            master_ctx: CtxItem,
            expert_id: str,
            query: str
    ):
        QObject.__init__(self)
        QRunnable.__init__(self)
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
            expert = self.window.core.experts.get_expert(expert_id)
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
            db_idx = self.window.controller.idx.current_idx  # get idx from agent config

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
            if db_idx:
                use_index = True
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

                # disable tools if cmd is not enabled
                if not self.window.core.command.is_cmd(inline=False):
                    tools = []

                # remove expert_call tool from tools
                for tool in list(tools):
                    if tool.metadata.name == "expert_call":
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
                if self.window.core.command.is_native_enabled():
                    functions = self.window.core.command.get_functions(master_ctx.id)
                    # without expert_call here

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
                    request=True, # use normal request instead of quick call
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

            # tmp switch meta for render purposes
            ctx.meta = master_ctx.meta

            if use_agent:
                self.signals.output.emit(ctx, mode)  # emit output signal, only if final response from agent

            ctx.clear_reply()  # reset results
            ctx.meta = slave  # restore before cmd execute

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

            # cleanup
            self.window = None
            self.master_ctx = None
            self.expert_id = None
            self.query = None
            self.signals.finished.disconnect()  # disconnect finished signal
            self.signals.response.disconnect()  # disconnect response signal
            self.signals.error.disconnect()  # disconnect error signal
            self.signals.event.disconnect()
            self.signals.output.disconnect()
            self.signals.lock_input.disconnect()
            self.signals.cmd.disconnect()
            self.deleteLater()  # delete worker instance

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
        :return: True if success, False otherwise
        """
        history = self.window.core.agents.memory.prepare(context)
        if system_prompt:
            msg = ChatMessage(
                role=MessageRole.SYSTEM,
                content=system_prompt
            )
            history.insert(0, msg)
        kwargs = {
            "context": context,
            "tools": tools,
            "llm": llm,
            "chat_history": history,
            "max_iterations": 30,
            "verbose": verbose,
            "system_prompt": system_prompt,
            "are_commands": self.window.core.config.get("cmd"),
        }
        provider = self.window.core.agents.provider.get("planner")
        agent = provider.get_agent(self.window, kwargs)
        response_ctx = self.window.core.agents.runner.llama_plan.run_once(
            agent=agent,
            ctx=ctx,
            prompt=query,
            verbose=verbose,
        )
        if response_ctx:
            return str(response_ctx.output)
        else:
            return "No response from expert."