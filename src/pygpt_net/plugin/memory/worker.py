#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.09 19:45:00                  #
# ================================================== #

from PySide6.QtCore import Slot

from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.core.events import KernelEvent
from pygpt_net.item.ctx import CtxItem
from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    pass


class Worker(BaseWorker):
    """Memory tool worker."""

    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds = None
        self.ctx = None

    @Slot()
    def run(self):
        try:
            responses = []
            for item in self.cmds or []:
                if self.is_stopped():
                    break
                try:
                    name = item.get("cmd")
                    if name not in self.plugin.allowed_cmds or not self.plugin.has_cmd(name):
                        continue
                    project_id = self.plugin.resolve_project_id(self.ctx)
                    if name == "memory_get":
                        result = self.plugin.get_memory(project_id)
                    elif name == "memory_add":
                        value = str(self.get_param(item, "text", "") or "")
                        result = self.plugin.add_memory(value, project_id)
                    elif name == "memory_update":
                        value = str(self.get_param(item, "text", "") or "")
                        if not value.strip():
                            result = (
                                "Memory was not updated. An empty replacement would clear the memory; "
                                "use memory_clear after explicit user confirmation instead."
                            )
                        else:
                            result = self.plugin.update_memory(value, project_id)
                    elif name == "memory_clear":
                        confirmed = bool(self.get_param(item, "confirmed", False))
                        if not confirmed:
                            result = (
                                "Memory was not cleared. Ask the user for explicit confirmation, then call "
                                "memory_clear again with confirmed=true."
                            )
                        else:
                            self.plugin.clear_memory(project_id)
                            self.plugin.skip_next_auto_update(self.ctx, project_id)
                            result = "Memory cleared."
                    else:
                        continue
                    responses.append(self.make_response(item, result))
                except Exception as exc:
                    responses.append(self.make_response(item, self.throw_error(exc)))

            if responses:
                self.reply_more(responses)
        except Exception as exc:
            self.error(exc)
        finally:
            self.cleanup()


class UpdateWorker(BaseWorker):
    """Background automatic memory updater scheduled on CTX_END."""

    def __init__(self, plugin=None, snapshot=None, project_id=None, *args, **kwargs):
        super(UpdateWorker, self).__init__(plugin=plugin)
        self.plugin = plugin
        self.window = plugin.window if plugin is not None else None
        self.snapshot = str(snapshot or "")
        self.project_id = project_id

    @Slot()
    def run(self):
        try:
            if self.plugin is None or not self.snapshot.strip():
                return
            with self.plugin.update_lock:
                current = self.plugin.get_memory(self.project_id)
                model = self.plugin.get_update_model()
                prompt = self.plugin.build_update_input(current, self.snapshot)
                bridge_ctx = BridgeContext(
                    ctx=CtxItem(),
                    prompt=prompt,
                    system_prompt=self.plugin.UPDATE_SYSTEM_PROMPT.format(
                        max_lines=self.plugin.get_max_lines()
                    ),
                    model=model,
                    max_tokens=8192,
                    temperature=0.0,
                    stream=False,
                    force=True,
                )
                event = KernelEvent(KernelEvent.FORCE_CALL, {
                    "context": bridge_ctx,
                    "extra": {"memory_update": True, "disable_tools": True},
                    "response": None,
                })
                self.window.dispatch(event)
                response = str(event.data.get("response") or "").strip()
                if not response:
                    return
                response = self.plugin.clean_model_memory(response)
                if not response:
                    return
                response = self.plugin.limit_lines(response, keep="first")
                self.plugin.store.set(response, self.project_id)
        except Exception as exc:
            try:
                self.window.core.debug.log(exc)
            except Exception:
                pass
        finally:
            self.cleanup()
