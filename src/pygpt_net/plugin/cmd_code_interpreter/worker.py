#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.20 10:15:00                  #
# ================================================== #

from PySide6.QtCore import Slot, Signal

from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals


class WorkerSignals(BaseSignals):
    output = Signal(object, str)
    output_begin = Signal(str)
    output_end = Signal(str)
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
        self.backend = None

    def get_backend(self):
        """Return the backend fixed for this worker run, or resolve it lazily."""
        if self.backend is not None:
            return self.backend
        return self.plugin.get_execution_backend()

    @Slot()
    def run(self):
        signals = self.signals
        backend = None
        interpreter = None
        try:
            # Runner and kernel objects are shared by plugin workers. Bind Qt
            # signals in the worker thread so overlapping tool calls cannot
            # replace another worker's signal source while it is restarting.
            if self.plugin is not None and signals is not None:
                backend = self.plugin.get_execution_backend()
                self.backend = backend
                interpreter = self.plugin.get_interpreter()
                self.plugin.runner.attach_signals(signals)
                interpreter.attach_signals(signals)

            responses = []
            for item in self.cmds:
                if self.is_stopped():
                    break
                try:
                    response = None
                    if (item["cmd"] in self.plugin.allowed_cmds
                            and (self.plugin.has_cmd(item["cmd"]) or 'force' in item)):

                        if item["cmd"] == "python_exec_file":
                            response = self.cmd_python_exec_file(item)

                        elif item["cmd"] == "python_exec":
                            response = self.cmd_python_exec(item)
                            if "silent" in item:
                                response = None

                        elif item["cmd"] == "ipython_exec":
                            response = self.cmd_ipython_exec(item)
                            if "silent" in item:
                                self.ctx.bag = response  # store tmp response
                                response = None

                        elif item["cmd"] == "ipython_sys_exec":
                            response = self.cmd_ipython_sys_exec(item)

                        elif item["cmd"] == "python_sys_exec":
                            response = self.cmd_python_sys_exec(item)

                        elif item["cmd"] == "ipython_kernel_restart":
                            response = self.cmd_ipython_kernel_restart(item)
                            if "silent" in item:
                                self.ctx.bag = response  # store tmp response
                                response = None

                        elif item["cmd"] == "html_render_output":
                            response = self.cmd_html_render_output(item)

                        elif item["cmd"] == "html_get_output":
                            response = self.cmd_html_get_output(item)

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
                self.reply_more(responses)  # send response

        except Exception as e:
            self.error(e)
        finally:
            if self.plugin is not None:
                try:
                    self.plugin.runner.detach_signals(signals)
                except Exception:
                    pass
                try:
                    if interpreter is not None:
                        interpreter.detach_signals(signals)
                except Exception:
                    pass
            self.cleanup()

    def cmd_ipython_exec(self, item: dict) -> dict:
        """
        Execute code in IPython interpreter (current kernel)

        :param item: command item
        :return: response item
        """
        try:
            result = self.plugin.runner.ipython_exec(
                ctx=self.ctx,
                item=item,
                request=self.from_request(item),
            )
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_ipython_sys_exec(self, item: dict) -> dict:
        """Execute a system command in the selected IPython execution backend."""
        request = self.from_request(item)
        try:
            result = self.get_backend().ipython_sys_exec(
                ctx=self.ctx,
                item=item,
                request=request,
            )
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_python_sys_exec(self, item: dict) -> dict:
        """Execute a system command in the selected standard Python backend."""
        request = self.from_request(item)
        try:
            result = self.get_backend().python_sys_exec(
                ctx=self.ctx,
                item=item,
                request=request,
            )
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_ipython_kernel_restart(self, item: dict) -> dict:
        """
        Restart current IPython kernel

        :param item: command item
        :return: response item
        """
        try:
            result = self.plugin.runner.ipython_kernel_restart(
                ctx=self.ctx,
                item=item,
                request=self.from_request(item),
            )
        except Exception as e:
            result = self.throw_error(e)

        extra = {
            'plugin': "cmd_code_interpreter",
        }
        return self.make_response(item, result, extra=extra)

    def cmd_python_exec_file(self, item: dict) -> dict:
        """Execute Python code from an existing file using the selected backend."""
        request = self.from_request(item)
        try:
            result = self.get_backend().python_exec_file(
                ctx=self.ctx,
                item=item,
                request=request,
            )
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_python_exec(self, item: dict) -> dict:
        """Execute Python code using the selected backend."""
        request = self.from_request(item)
        try:
            result = self.get_backend().python_exec(
                ctx=self.ctx,
                item=item,
                request=request,
                all=bool(item.get("all", False)),
            )
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_html_render_output(self, item: dict) -> dict:
        """
        Show output in HTML canvas

        :param item: command item
        :return: response item
        """
        try:
            if self.has_param(item, "html"):
                self.plugin.runner.send_html_output(self.get_param(item, "html")) # handle in main thread
            result = "OK"
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_html_get_output(self, item: dict) -> dict:
        """
        Get HTML canvas output

        :param item: command item
        :return: response item
        """
        try:
            result = self.plugin.window.tools.get("html_canvas").get_output()
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def prepare_extra(self, item: dict, result) -> dict:
        """
        Prepare extra data for response

        :param item: command item
        :param result: response data
        :return: extra data
        """
        cmd = item["cmd"]
        extra = {
            'plugin': "cmd_code_interpreter",
            'cmd': cmd,
            'code': {}
        }
        lang = "python"
        if cmd in ["html_render_output", "html_get_output"]:
            lang = "html"
        elif cmd in ["ipython_sys_exec", "python_sys_exec", "sys_exec"]:
            lang = "bash"
        if "params" in item and "code" in item["params"]:
            extra["code"]["input"] = {}
            extra["code"]["input"]["lang"] = lang
            extra["code"]["input"]["content"] = str(item["params"]["code"])
        elif cmd in ["ipython_sys_exec", "python_sys_exec"] and "params" in item and "command" in item["params"]:
            extra["code"]["input"] = {}
            extra["code"]["input"]["lang"] = "bash"
            extra["code"]["input"]["content"] = str(item["params"]["command"])
        if isinstance(result, dict) and "result" in result:
            extra["code"]["output"] = {}
            extra["code"]["output"]["lang"] = lang
            extra["code"]["output"]["content"] = str(result["result"])
        if isinstance(result, dict) and "context" in result:
            extra["context"] = str(result["context"])
        return extra


