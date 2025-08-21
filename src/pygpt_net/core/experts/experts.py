#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.21 07:00:00                  #
# ================================================== #

import json
from typing import Dict, List

from PySide6.QtCore import Slot

from pygpt_net.core.experts.worker import ExpertWorker
from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_CHAT,
    MODE_COMPLETION,
    MODE_EXPERT,
    MODE_LLAMA_INDEX,
    MODE_VISION,
    MODE_AUDIO,
    MODE_RESEARCH,
    TOOL_EXPERT_CALL_NAME,
    TOOL_EXPERT_CALL_DESCRIPTION,
    TOOL_EXPERT_CALL_PARAM_ID_DESCRIPTION,
    TOOL_EXPERT_CALL_PARAM_QUERY_DESCRIPTION,
    QUERY_ENGINE_TOOL_NAME,
    QUERY_ENGINE_TOOL_DESCRIPTION,
    QUERY_ENGINE_PARAM_DESCRIPTION,
)
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import Event, KernelEvent
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
        self.allowed_cmds = [TOOL_EXPERT_CALL_NAME]
        self.worker = None
        self.last_expert_id = None  # last expert id used in call
        self.last_idx = None  # last index used in call
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
                experts_list.append(f" - {k}: {experts[k].name}")
            else:
                experts_list.append(f" - {k}: {experts[k].name} ({experts[k].description})")
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
                if item["cmd"] == TOOL_EXPERT_CALL_NAME:
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
                self.window.core.debug.log(e)
                return {}
        return calls

    def extract_tool_calls(self, ctx: CtxItem):
        """
        Extract tool calls from expert

        :param ctx: context item
        """
        for call in ctx.tool_calls:
            if (call["type"] == "function"
                    and "function" in call
                    and call["function"]["name"] == QUERY_ENGINE_TOOL_NAME):
                ctx.force_call = True  # force call if query engine tool is used
                ctx.cmds_before = [
                    {
                        "cmd": QUERY_ENGINE_TOOL_NAME,
                        "params": {
                            "query": call["function"]["arguments"]["query"],
                            "idx": self.last_idx,
                        },
                    }
                ]
                break

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
            "msg": f"{trans('expert.wait.status')} ({expert_name})",
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

        # if 'get_context' tool is used then force call, and append idx
        self.extract_tool_calls(ctx)  # extract tool calls from ctx

        self.window.controller.chat.command.handle(ctx, internal=True)  # handle cmds sync
        if ctx.reply:
            self.window.update_status("")  # clear status

            # prepare data to send as reply
            tool_data = json.dumps(ctx.results)
            # if "tool_output" in ctx.extra and ctx.extra["tool_output"]:
               # tool_data = str(ctx.extra["tool_output"])

            self.window.core.ctx.update_item(ctx)  # update context in db
            self.window.update_status('...')
            ctx.output = f"<tool>{ctx.cmds}</tool>"
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
        context.prompt = f"{trans('expert.wait.failed')}: {error}"
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

    @Slot()
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
                "cmd": TOOL_EXPERT_CALL_NAME,
                "instruction": TOOL_EXPERT_CALL_DESCRIPTION,
                "params": [
                    {
                        "name": "id",
                        "description": TOOL_EXPERT_CALL_PARAM_ID_DESCRIPTION,
                        "required": True,
                        "type": "str",
                    },
                    {
                        "name": "query",
                        "description": TOOL_EXPERT_CALL_PARAM_QUERY_DESCRIPTION,
                        "required": True,
                        "type": "str",
                    }
                ]
            }
        ]
        return cmds

    def get_retriever_tool(self) -> Dict[str, str]:
        """
        Get retriever tool for additional context retrieval

        :return: retriever tool definition
        """
        return {
            "cmd": QUERY_ENGINE_TOOL_NAME,
            "instruction": QUERY_ENGINE_TOOL_DESCRIPTION,
            "params": [
                {
                    "name": "query",
                    "description": QUERY_ENGINE_PARAM_DESCRIPTION,
                    "required": True,
                    "type": "str",
                }
            ]
        }

    def has_calls(self, ctx: CtxItem) -> bool:
        """
        Check if context has expert calls

        :param ctx: CtxItem
        :return: True if expert calls found
        """
        if not ctx.sub_reply and not ctx.reply:
            mentions = self.window.core.experts.extract_calls(ctx)
            if mentions:
                for expert_id in mentions:
                    if not self.window.core.experts.exists(expert_id):
                        continue
                    return True
        return False
