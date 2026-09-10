#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.10 14:10:00                  #
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

    @Slot()
    def run(self):
        signals = self.signals
        try:
            # Runner and kernel objects are shared by plugin workers. Bind Qt
            # signals in the worker thread so overlapping tool calls cannot
            # replace another worker's signal source while it is restarting.
            if self.plugin is not None and signals is not None:
                self.plugin.runner.attach_signals(signals)
                self.plugin.get_interpreter().attach_signals(signals)

            responses = []
            for item in self.cmds:
                if self.is_stopped():
                    break
                try:
                    response = None
                    if (item["cmd"] in self.plugin.allowed_cmds
                            and (self.plugin.has_cmd(item["cmd"]) or 'force' in item)):

                        if item["cmd"] == "code_execute_file":
                            response = self.cmd_code_execute_file(item)

                        elif item["cmd"] == "code_execute":
                            response = self.cmd_code_execute(item)
                            if "silent" in item:
                                response = None

                        elif item["cmd"] == "code_execute_all":
                            response = self.cmd_code_execute_all(item)
                            if "silent" in item:
                                response = None

                        elif item["cmd"] == "ipython_execute_new":
                            response = self.cmd_ipython_execute_new(item)
                            if "silent" in item:
                                self.ctx.bag = response  # store tmp response
                                response = None

                        elif item["cmd"] == "ipython_execute":
                            response = self.cmd_ipython_execute(item)
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

                        elif item["cmd"] == "get_python_output":
                            response = self.cmd_get_python_output(item)

                        elif item["cmd"] == "get_python_input":
                            response = self.cmd_get_python_input(item)

                        elif item["cmd"] == "clear_python_output":
                            response = self.cmd_clear_python_output(item)

                        elif item["cmd"] == "render_html_output":
                            response = self.cmd_render_html_output(item)

                        elif item["cmd"] == "get_html_output":
                            response = self.cmd_get_html_output(item)

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
                    self.plugin.get_interpreter().detach_signals(signals)
                except Exception:
                    pass
            self.cleanup()

    def cmd_ipython_execute_new(self, item: dict) -> dict:
        """
        Execute code in IPython interpreter (new kernel)

        :param item: command item
        :return: response item
        """
        try:
            result = self.plugin.runner.ipython_execute_new(
                ctx=self.ctx,
                item=item,
                request=self.from_request(item),
            )
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_ipython_execute(self, item: dict) -> dict:
        """
        Execute code in IPython interpreter (current kernel)

        :param item: command item
        :return: response item
        """
        try:
            result = self.plugin.runner.ipython_execute(
                ctx=self.ctx,
                item=item,
                request=self.from_request(item),
            )
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_ipython_sys_exec(self, item: dict) -> dict:
        """
        Execute a system command in the IPython environment.

        :param item: command item
        :return: response item
        """
        request = self.from_request(item)
        try:
            if self.plugin.runner.is_sandbox_ipython():
                result = self.plugin.runner.ipython_sys_exec_sandbox(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
            else:
                result = self.plugin.runner.ipython_sys_exec_host(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_python_sys_exec(self, item: dict) -> dict:
        """
        Execute a system command in the legacy Python environment.

        :param item: command item
        :return: response item
        """
        request = self.from_request(item)
        try:
            if self.plugin.runner.is_sandbox():
                result = self.plugin.runner.python_sys_exec_sandbox(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
            else:
                result = self.plugin.runner.python_sys_exec_host(
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
        # self.cmd_clear_python_output(item)
        return self.make_response(item, result, extra=extra)

    def cmd_code_execute_file(self, item: dict) -> dict:
        """
        Execute code command from existing file

        :param item: command item
        :return: response item
        """
        request = self.from_request(item)
        try:
            if not self.plugin.runner.is_sandbox():
                result = self.plugin.runner.code_execute_file_host(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
            else:
                result = self.plugin.runner.code_execute_file_sandbox(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_code_execute(self, item: dict) -> dict:
        """
        Execute code command

        :param item: command item
        :return: response item
        """
        request = self.from_request(item)
        try:
            if not self.plugin.runner.is_sandbox():
                result = self.plugin.runner.code_execute_host(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
            else:
                result = self.plugin.runner.code_execute_sandbox(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_code_execute_all(self, item: dict) -> dict:
        """
        Execute all code command

        :param item: command item
        :return: response item
        """
        request = self.from_request(item)
        try:
            if not self.plugin.runner.is_sandbox():
                result = self.plugin.runner.code_execute_host(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                    all=True,
                )
            else:
                result = self.plugin.runner.code_execute_sandbox(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                    all=True,
                )
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_get_python_output(self, item: dict) -> dict:
        """
        Get python output

        :param item: command item
        :return: response item
        """
        try:
            result = self.plugin.window.tools.get("interpreter").get_current_output()
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_get_python_input(self, item: dict) -> dict:
        """
        Get python input (edit code)

        :param item: command item
        :return: response item
        """
        try:
            result = self.plugin.window.tools.get("interpreter").get_current_history()
        except Exception as e:
            result = self.throw_error(e)

        extra = self.prepare_extra(item, result)
        return self.make_response(item, result, extra=extra)

    def cmd_clear_python_output(self, item: dict) -> dict:
        """
        Clear python output

        :param item: command item
        :return: response item
        """
        try:
            self.signals.clear.emit()
            result = "OK"
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_render_html_output(self, item: dict) -> dict:
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

    def cmd_get_html_output(self, item: dict) -> dict:
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

    def prepare_extra(self, item: dict, result: dict) -> dict:
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
        if cmd in ["render_html_output", "get_html_output"]:
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
        if "result" in result:
            extra["code"]["output"] = {}
            extra["code"]["output"]["lang"] = lang
            extra["code"]["output"]["content"] = str(result["result"])
        if "context" in result:
            extra["context"] = str(result["context"])
        return extra


