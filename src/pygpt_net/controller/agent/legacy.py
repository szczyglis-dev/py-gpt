#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.08 21:20:00                  #
# ================================================== #

from typing import Optional, List, Dict, Any

from pygpt_net.core.types import (
    MODE_AGENT,
    MODE_AGENT_LLAMA,
    MODE_AGENT_OPENAI,
)
from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.ctx.reply import ReplyContext
from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Legacy:
    """Controller for the simple/legacy autonomous Agent mode.

    The provider/API request path is intentionally shared with ordinary chat.
    What makes this mode autonomous is only the small continuation loop below.
    Every user request owns one durable ``CtxItem``; later autonomous model
    messages and all tool round-trips are folded into partials/tasks of that item.
    """

    LEGACY_PROMPT_MARKERS = (
        "self-dialogue mode",
        "Any input that begins with 'user: '",
    )
    LEGACY_GOAL_PROMPT_MARKERS = (
        "## STATUS UPDATE:",
        "## ON GOAL FINISH:",
        "Attach this special command to response text",
    )

    AUTONOMOUS_INSTRUCTION = """# AUTONOMOUS MODE

You are executing one user task autonomously. Work in a simple iterative loop until the task is complete, paused, failed, or the configured iteration limit is reached.

Rules:
- Treat the original user message as the goal. Do not simulate a conversation with yourself and do not invent user replies.
- On every iteration, perform the next useful action toward the goal. Do not repeat previous text just to keep the loop running.
- Use available tools whenever they are useful. Prefer native tool/function calls when the provider supports them; otherwise use the application's tool syntax.
- After a tool result, inspect it and continue from the actual result. Do not assume a tool succeeded without checking its returned data.
- You may use enabled tools without asking for permission unless a tool or safety policy explicitly requires user confirmation.
- Keep intermediate assistant messages focused on useful progress/results; do not expose private chain-of-thought or artificial self-critique.
- If the task cannot continue without information from the user, pause instead of guessing.
- When the task is fully complete, provide the final user-facing result and signal completion with goal_update(status="finished") when that control is available.
- Do not offer unrelated additional work after completion.
"""

    CONTINUE_PROMPT = (
        "Continue the same autonomous run. Review the work already completed and the remaining goal, "
        "then perform the next useful action. Use tools if needed and verify their results. Do not repeat "
        "previous text. If the task is fully complete, give the final user-facing result and finish the run "
        "with goal_update(status=\"finished\") when available."
    )

    CONTINUE_ALWAYS_PROMPT = (
        "Continue the same autonomous run with the next useful action. Use tools if needed, verify results, "
        "and do not repeat previous text. Continue until the configured iteration limit or an explicit "
        "pause/failed/wait condition is reached."
    )

    PROMPT_GOAL_NATIVE = """# AUTONOMOUS RUN STATUS
Use the goal_update control function only as a run-control signal:
- status="finished": the requested task is fully complete and the user-facing result is ready.
- status="wait": more information or an explicit user decision is required.
- status="pause": the run should be intentionally paused.
- status="failed": the task cannot be completed in the current run.
Do not call goal_update for ordinary progress updates. Prefer calling it at the end of the response that concludes the run.
"""

    PROMPT_GOAL_LEGACY = """# AUTONOMOUS RUN STATUS
Use the special goal_update command only as a run-control signal. Put it at the end of the response in tool syntax, for example:
<tool>{"cmd":"goal_update","params":{"status":"finished"}}</tool>
Allowed statuses are: finished, wait, pause, failed.
Use finished only when the task is fully complete. Use wait when user input is required, pause for an intentional pause, and failed when the task cannot be completed. Do not emit goal_update for ordinary progress updates.
"""

    def __init__(self, window=None):
        """
        Agent flow controller

        :param window: Window instance
        """
        self.window = window
        # Number of completed autonomous model steps in the current run. Tool
        # replies do not increment this counter.
        self.iteration = 0
        self.prev_output = None
        self.is_user = True
        self.stop = False
        self.finished = False
        self.terminal_status = None
        # Snapshot run-control options at USER_SEND so switching/focusing another
        # chat/mode while an async agent run is in progress cannot change its
        # termination semantics halfway through the task.
        self.run_active = False
        self.run_auto_stop = None
        self.run_always_continue = None
        self.allowed_cmds = [
            "goal_update",
        ]
        self.pause_status = ["pause", "failed", "wait"]
        self.prompt_goal_native = self.PROMPT_GOAL_NATIVE
        self.options = {
            "agent.iterations": {
                "type": "int",
                "slider": True,
                "label": "agent.iterations",
                "min": 0,
                "max": 100,
                "step": 1,
                "value": 3,
                "multiplier": 1,
            },
        }

    def setup(self):
        """Setup agent controller"""
        self.window.ui.add_hook("update.global.agent.iterations", self.hook_update)
        self.reload()

    def reload(self):
        """Reload agent toolbox options"""
        if self.window.core.config.get('agent.auto_stop'):
            self.window.ui.config['global']['agent.auto_stop'].setChecked(True)
        else:
            self.window.ui.config['global']['agent.auto_stop'].setChecked(False)

        if self.window.core.config.get('agent.continue.always'):
            self.window.ui.config['global']['agent.continue'].setChecked(True)
        else:
            self.window.ui.config['global']['agent.continue'].setChecked(False)

        self.window.controller.config.apply_value(
            parent_id="global",
            key="agent.iterations",
            option=self.options["agent.iterations"],
            value=self.window.core.config.get('agent.iterations'),
        )

    def update(self):
        """Update agent status"""
        iterations = "-"
        mode = self.window.core.config.get('mode')

        if mode in [
            MODE_AGENT,
            MODE_AGENT_LLAMA,
            MODE_AGENT_OPENAI,
        ]:
            iterations = int(self.window.core.config.get("agent.iterations"))
        elif self.is_inline():
            if self.window.controller.plugins.is_enabled("agent"):
                iterations = int(self.window.core.plugins.get_option("agent", "iterations"))
        if iterations == 0:
            iterations_str = "∞"
        else:
            iterations_str = str(iterations)

        status = str(self.iteration) + " / " + iterations_str
        self.window.ui.nodes['status.agent'].setText(status)
        self.window.controller.agent.common.toggle_status()

    def get_auto_stop(self) -> bool:
        """Return auto-stop setting for global or inline autonomous mode."""
        if self.run_active and self.run_auto_stop is not None:
            return bool(self.run_auto_stop)
        if self.window.core.config.get('mode') == MODE_AGENT:
            return bool(self.window.core.config.get('agent.auto_stop'))
        if self.is_inline() and self.window.controller.plugins.is_enabled("agent"):
            try:
                return bool(self.window.core.plugins.get_option("agent", "auto_stop"))
            except Exception:
                return False
        return False

    def get_always_continue(self) -> bool:
        """Return whether a normal `finished` signal should be ignored."""
        if self.run_active and self.run_always_continue is not None:
            return bool(self.run_always_continue)
        if self.window.core.config.get('mode') == MODE_AGENT:
            return bool(self.window.core.config.get('agent.continue.always'))
        if self.is_inline() and self.window.controller.plugins.is_enabled("agent"):
            try:
                return bool(self.window.core.plugins.get_option("agent", "always_continue"))
            except Exception:
                return False
        return False

    def get_functions(self) -> List[Dict[str, Any]]:
        """Append the internal run-control function when auto-stop is enabled."""
        if not self.get_auto_stop():
            return []
        return [
            {
                "cmd": "goal_update",
                "instruction": (
                    "Finish or pause the current autonomous run. Use only when the task is complete, "
                    "needs user input, is intentionally paused, or has failed."
                ),
                "params": [
                    {
                        "name": "status",
                        "description": "terminal status of the autonomous run",
                        "required": True,
                        "type": "str",
                        "enum": {
                            "status": ["finished", "pause", "failed", "wait"],
                        }
                    }
                ]
            }
        ]

    def normalize_instruction_prompt(self, prompt: Optional[str]) -> str:
        """Upgrade the historical self-dialogue default without overwriting custom prompts."""
        value = str(prompt or "").strip()
        if not value:
            return self.AUTONOMOUS_INSTRUCTION
        if all(marker in value for marker in self.LEGACY_PROMPT_MARKERS):
            return self.AUTONOMOUS_INSTRUCTION
        return value

    def get_goal_prompt(self) -> str:
        """Return run-control instructions while preserving custom legacy prompts."""
        if self.window.core.command.is_native_enabled():
            return self.PROMPT_GOAL_NATIVE

        value = str(self.window.core.prompt.get("agent.goal") or "").strip()
        if not value or all(marker in value for marker in self.LEGACY_GOAL_PROMPT_MARKERS):
            return self.PROMPT_GOAL_LEGACY
        return value

    def get_continue_prompt(self) -> str:
        """Return a useful continuation instruction, upgrading old short defaults in-place."""
        core = self.window.core
        if self.get_always_continue():
            value = str(core.prompt.get("agent.continue.always") or "").strip()
            if not value or value.lower() in ("continue reasoning...", "continue reasoning"):
                return self.CONTINUE_ALWAYS_PROMPT
            return value

        value = str(core.prompt.get("agent.continue") or "").strip()
        old = "continue, or complete the run if the goal is fully achieved."
        if not value or value.lower() == old:
            return self.CONTINUE_PROMPT
        return value

    def on_system_prompt(
            self,
            prompt: str,
            append_prompt: Optional[str] = "",
            auto_stop: bool = True,
    ) -> str:
        """
        Event: On prepare system prompt

        :param prompt: prompt
        :param append_prompt: extra prompt (instruction)
        :param auto_stop: auto stop
        :return: updated prompt
        """
        prompt = str(prompt or "")
        if append_prompt is not None and str(append_prompt).strip() != "":
            prompt += "\n\n" + self.normalize_instruction_prompt(append_prompt)

        if auto_stop:
            prompt += "\n\n" + self.get_goal_prompt()
        return prompt

    def on_input_before(self, prompt: str) -> str:
        """Keep real user input unchanged; API roles already distinguish user and assistant."""
        return prompt

    def on_user_send(self, text: str):
        """Begin a new autonomous run and freeze its run-control options."""
        # Read the active configuration before setting run_active, otherwise the
        # getters would return the previous run's snapshot.
        self.run_active = False
        auto_stop = self.get_auto_stop()
        always_continue = self.get_always_continue()

        self.iteration = 0
        self.prev_output = None
        self.is_user = True
        self.stop = False
        self.finished = False
        self.terminal_status = None
        self.run_auto_stop = bool(auto_stop)
        self.run_always_continue = bool(always_continue)
        self.run_active = True
        self.window.controller.agent.legacy.update()

    def _queue_continue(self, ctx: CtxItem, prompt: str):
        """Queue one explicit autonomous continuation against the durable root turn."""
        if not prompt or self.stop:
            return
        if self.window.controller.kernel.stack.waiting():
            return

        reply = ReplyContext()
        reply.type = ReplyContext.AGENT_CONTINUE
        reply.ctx = ctx
        reply.input = prompt

        context = BridgeContext()
        context.ctx = ctx
        context.reply_context = reply
        event = KernelEvent(KernelEvent.AGENT_CONTINUE, {
            'context': context,
            'extra': {},
        })
        self.window.dispatch(event)

    def on_ctx_end(
            self,
            ctx: CtxItem,
            iterations: int = 0,
    ):
        """Advance the simple autonomous loop after a completed, tool-free step."""
        if ctx is None or ctx.sub_reply:
            return

        # A terminal goal signal is consumed before CTX_END. Count the response
        # that contained it, then finish without scheduling another provider call.
        if self.stop:
            return

        # A plain first assistant response normally has no partial yet. Persist
        # it now before scheduling the next autonomous provider turn; otherwise
        # creating the second partial would make the first response disappear
        # from the parent's composed output/history. Tool responses already
        # create their partial through record_tool_calls(), so ensure_part() is
        # intentionally idempotent here.
        self.window.core.ctx.ensure_part(
            ctx,
            name=getattr(ctx, "output_name", None),
        )

        self.iteration += 1
        self.window.controller.agent.legacy.update()

        if self.finished:
            self.on_stop(auto=True, preserve_finished=True)
            return

        limit = max(0, int(iterations or 0))
        if limit > 0 and self.iteration >= limit:
            self.on_stop(auto=True)
            if self.window.core.config.get("agent.goal.notify"):
                self.window.ui.tray.show_msg(
                    trans("notify.agent.stop.title"),
                    trans("notify.agent.stop.content"),
                )
            return

        self._queue_continue(ctx, self.prev_output or self.get_continue_prompt())

    def on_ctx_before(
            self,
            ctx: CtxItem,
            reverse_roles: bool = False,
    ):
        """Prepare one autonomous provider call."""
        ctx.internal = True
        self.is_user = False
        if self.iteration == 0:
            ctx.first = True

        # Kept for the inline plugin compatibility option. Global Agent mode does
        # not request role reversal and therefore follows ordinary chat roles.
        if self.iteration > 0 \
                and self.iteration % 2 != 0 \
                and reverse_roles:
            tmp_input_name = ctx.input_name
            tmp_output_name = ctx.output_name
            ctx.input_name = tmp_output_name
            ctx.output_name = tmp_input_name

    def on_ctx_after(self, ctx: CtxItem):
        """Prepare the next loop instruction; tool outputs remain in structured history."""
        if self.stop or self.finished:
            self.prev_output = None
            return
        # Do not reuse ctx.extra_ctx here. It can contain a tool/plugin payload
        # already represented in the partial task graph and would feed the same
        # result back to the model a second time.
        self.prev_output = self.get_continue_prompt()

    def on_cmd(
            self,
            ctx: CtxItem,
            cmds: List[Dict[str, Any]],
            cmds_raw: List[Dict[str, Any]] = None,
    ):
        """Handle run-control commands when auto-stop is enabled."""
        if self.get_auto_stop():
            return self.cmd(ctx, cmds, cmds_raw)
        return False

    def cmd(
            self,
            ctx: CtxItem,
            cmds: List[Dict[str, Any]],
            cmds_raw: List[Dict[str, Any]] = None,
    ) -> bool:
        """Consume goal_update and return True if it terminates the current run."""
        my_commands = []
        for item in cmds or []:
            if isinstance(item, dict) and item.get("cmd") in self.allowed_cmds:
                my_commands.append(item)

        if cmds_raw:
            for item in cmds_raw:
                if (isinstance(item, dict)
                        and item.get("cmd") in self.allowed_cmds
                        and item not in my_commands):
                    my_commands.append(item)

        if not my_commands:
            return False

        for item in my_commands:
            try:
                params = item.get("params") if isinstance(item.get("params"), dict) else {}
                status = str(params.get("status") or "").strip().lower()
                if status not in ["finished", *self.pause_status]:
                    continue

                # "Always continue" deliberately ignores only successful finish;
                # pause/wait/failed must still stop an otherwise infinite loop.
                if status == "finished" and self.get_always_continue():
                    self.window.core.debug.info(
                        "[agent] goal_update(finished) ignored because Always continue is enabled."
                    )
                    return False

                self.finished = True
                self.terminal_status = status
                self.prev_output = None
                self.window.update_status(trans('status.finished'))

                if status == "finished" and self.window.core.config.get("agent.goal.notify"):
                    self.window.ui.tray.show_msg(
                        trans("notify.agent.goal.title"),
                        trans("notify.agent.goal.content"),
                    )
                return True
            except Exception as e:
                self.window.core.debug.error(e)
                return False
        return False

    def consume_control_commands(self, ctx: CtxItem) -> bool:
        """Remove goal_update from the normal tool pipeline and apply it as control state.

        ``goal_update`` is not a real plugin tool and therefore must not create a
        pending task or require a tool-result roundtrip. Native providers can still
        call it as a function, but the call is consumed locally before command
        dispatch. This also lets a response containing only goal_update complete
        the normal output/history lifecycle instead of being mistaken for a
        pending tool request.
        """
        if ctx is None or not self.get_auto_stop():
            return False

        commands = list(ctx.cmds_before or [])
        controls = [
            item for item in commands
            if isinstance(item, dict) and item.get("cmd") in self.allowed_cmds
        ]
        if not controls:
            return False

        terminal = self.cmd(ctx, controls, controls)

        def is_control_cmd(item):
            return isinstance(item, dict) and item.get("cmd") in self.allowed_cmds

        if terminal:
            # A terminal control and another tool in the same model response are
            # contradictory. Terminal state wins: do not execute additional work
            # after the model declared the run complete/paused/failed.
            ctx.cmds_before = []
            ctx.cmds = []
            ctx.tool_calls = []
        else:
            ctx.cmds_before = [item for item in (ctx.cmds_before or []) if not is_control_cmd(item)]
            ctx.cmds = [item for item in (ctx.cmds or []) if not is_control_cmd(item)]
            remaining_calls = []
            for call in ctx.tool_calls or []:
                fn = call.get("function") if isinstance(call, dict) else None
                name = fn.get("name") if isinstance(fn, dict) else None
                if name != "goal_update":
                    remaining_calls.append(call)
            ctx.tool_calls = remaining_calls

        if not isinstance(ctx.extra, dict):
            ctx.extra = {}
        if ctx.tool_calls:
            ctx.extra["tool_calls"] = list(ctx.tool_calls)
        else:
            ctx.extra.pop("tool_calls", None)
            ctx.extra.pop("prev_tool_calls", None)
        return terminal

    def is_inline(self) -> bool:
        """Return True when the inline autonomous plugin is enabled."""
        return self.window.controller.plugins.is_type_enabled("agent")

    def enabled(self, check_inline=True) -> bool:
        """Return whether legacy/simple autonomous handling is active."""
        if not check_inline:
            return self.window.core.config.get('mode') == MODE_AGENT
        return self.window.core.config.get('mode') == MODE_AGENT or self.is_inline()

    def add_run(self):
        """Compatibility no-op: tool replies are not autonomous iterations."""
        self.update()

    def on_stop(self, auto: bool = False, preserve_finished: bool = False):
        """Stop the current autonomous loop without discarding its final counter."""
        self.window.controller.kernel.stack.lock()
        self.window.controller.chat.common.unlock_input()
        self.prev_output = None
        self.stop = True
        self.run_active = False
        if not preserve_finished:
            self.finished = False
            self.terminal_status = None

        if auto:
            self.window.controller.idx.on_ctx_end(
                ctx=None,
                mode="agent",
            )

    def hook_update(self, key: str, value: Any, caller, *args, **kwargs):
        """Handle global agent toolbox option changes."""
        if self.window.core.config.get(key) == value:
            return
        if key == 'agent.iterations':
            self.window.core.config.set(key, int(value))
            self.window.core.config.save()
            self.update()
