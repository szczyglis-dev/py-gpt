#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.23 07:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, Signal

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    output = Signal(object, str)
    html_output = Signal(object)
    ipython_output = Signal(object)
    build_finished = Signal()
    clear = Signal()


class Worker(BaseWorker):
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
            for item in self.cmds:
                if self.is_stopped():
                    break
                try:
                    response = None
                    if (item["cmd"] in self.plugin.allowed_cmds
                            and (self.plugin.has_cmd(item["cmd"]) or 'force' in item)):

                        cmd = item["cmd"]
                        params = item.get("params", {}) or {}

                        # System command
                        if cmd == "sys_exec":
                            response = self.cmd_sys_exec(item)

                        # WinAPI commands
                        elif cmd == "win_list":
                            response = self._wrap(item, self.plugin.runner.win_list, params)
                        elif cmd == "win_find":
                            response = self._wrap(item, self.plugin.runner.win_find, params)
                        elif cmd == "win_children":
                            response = self._wrap(item, self.plugin.runner.win_children, params)
                        elif cmd == "win_foreground":
                            response = self._wrap(item, self.plugin.runner.win_foreground, params)
                        elif cmd == "win_rect":
                            response = self._wrap(item, self.plugin.runner.win_rect, params)
                        elif cmd == "win_get_state":
                            response = self._wrap(item, self.plugin.runner.win_get_state, params)

                        elif cmd == "win_focus":
                            response = self._wrap(item, self.plugin.runner.win_focus, params)
                        elif cmd == "win_move_resize":
                            response = self._wrap(item, self.plugin.runner.win_move_resize, params)
                        elif cmd == "win_minimize":
                            response = self._wrap(item, self.plugin.runner.win_minimize, params)
                        elif cmd == "win_maximize":
                            response = self._wrap(item, self.plugin.runner.win_maximize, params)
                        elif cmd == "win_restore":
                            response = self._wrap(item, self.plugin.runner.win_restore, params)
                        elif cmd == "win_close":
                            response = self._wrap(item, self.plugin.runner.win_close, params)
                        elif cmd == "win_show":
                            response = self._wrap(item, self.plugin.runner.win_show, params)
                        elif cmd == "win_hide":
                            response = self._wrap(item, self.plugin.runner.win_hide, params)
                        elif cmd == "win_always_on_top":
                            response = self._wrap(item, self.plugin.runner.win_always_on_top, params)
                        elif cmd == "win_set_opacity":
                            response = self._wrap(item, self.plugin.runner.win_set_opacity, params)

                        elif cmd == "win_screenshot":
                            response = self._wrap(item, self.plugin.runner.win_screenshot, params)
                        elif cmd == "win_area_screenshot":
                            response = self._wrap(item, self.plugin.runner.win_area_screenshot, params)

                        elif cmd == "win_clipboard_get":
                            response = self._wrap(item, self.plugin.runner.win_clipboard_get, params)
                        elif cmd == "win_clipboard_set":
                            response = self._wrap(item, self.plugin.runner.win_clipboard_set, params)

                        elif cmd == "win_cursor_get":
                            response = self._wrap(item, self.plugin.runner.win_cursor_get, params)
                        elif cmd == "win_cursor_set":
                            response = self._wrap(item, self.plugin.runner.win_cursor_set, params)

                        elif cmd == "win_keys_text":
                            response = self._wrap(item, self.plugin.runner.win_keys_text, params)
                        elif cmd == "win_keys_send":
                            response = self._wrap(item, self.plugin.runner.win_keys_send, params)
                        elif cmd == "win_click":
                            response = self._wrap(item, self.plugin.runner.win_click, params)
                        elif cmd == "win_drag":
                            response = self._wrap(item, self.plugin.runner.win_drag, params)

                        elif cmd == "win_monitors":
                            response = self._wrap(item, self.plugin.runner.win_monitors, params)

                        if response:
                            responses.append(response)

                except Exception as e:
                    responses.append(
                        self.make_response(
                            item,
                            self.throw_error(e)
                        )
                    )

            if len(responses) > 0:
                self.reply_more(responses) # send response

        except Exception as e:
            self.error(e)
        finally:
            self.cleanup()

    def cmd_sys_exec(self, item: dict) -> dict:
        """
        Execute system command
        """
        request = self.from_request(item)
        try:
            if not self.plugin.runner.is_sandbox():
                result = self.plugin.runner.sys_exec_host(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
            else:
                result = self.plugin.runner.sys_exec_sandbox(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def _wrap(self, item: dict, fn, params: dict) -> dict:
        """Execute runner function and adapt to response format"""
        request = self.from_request(item)
        try:
            result = fn(**(params or {}))
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def prepare_extra(self, item: dict, result: dict) -> dict:
        """
        Prepare extra data for response
        """
        cmd = item["cmd"]
        extra = {
            'plugin': "cmd_system",
            'cmd': cmd,
            'code': {}
        }
        # Language hint for renderer
        if cmd in ["sys_exec"]:
            lang = "bash"
        elif cmd in ["win_keys_text"]:
            lang = "text"
        else:
            lang = "json"

        if "params" in item and "code" in item["params"]:
            extra["code"]["input"] = {}
            extra["code"]["input"]["lang"] = lang
            extra["code"]["input"]["content"] = str(item["params"]["code"])
        if isinstance(result, dict) and "result" in result:
            extra["code"]["output"] = {}
            extra["code"]["output"]["lang"] = lang
            extra["code"]["output"]["content"] = str(result["result"])
        if isinstance(result, dict) and "context" in result:
            extra["context"] = str(result["context"])
        return extra