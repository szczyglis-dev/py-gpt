#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.17 17:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, Signal

from pygpt_net.plugin.base import BaseWorker, BaseSignals


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
        responses = []
        for item in self.cmds:
            try:
                response = None
                if item["cmd"] in self.plugin.allowed_cmds and (self.plugin.has_cmd(item["cmd"]) or 'force' in item):

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
                            response = None

                    elif item["cmd"] == "ipython_execute":
                        response = self.cmd_ipython_execute(item)
                        if "silent" in item:
                            response = None

                    elif item["cmd"] == "ipython_kernel_restart":
                        response = self.cmd_ipython_kernel_restart(item)
                        if "silent" in item:
                            response = None

                    elif item["cmd"] == "sys_exec":
                        response = self.cmd_sys_exec(item)

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
                responses.append({
                    "request": {
                        "cmd": item["cmd"],
                    },
                    "result": "Error {}".format(e),
                })
                self.error(e)
                self.log("Error: {}".format(e))

        # send response
        if len(responses) > 0:
            self.reply_more(responses)


    def cmd_ipython_execute_new(self, item: dict) -> dict:
        """
        Execute code in IPython interpreter (new kernel)

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            response = self.plugin.runner.ipython_execute_new(
                ctx=self.ctx,
                item=item,
                request=request,
            )
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_ipython_execute(self, item: dict) -> dict:
        """
        Execute code in IPython interpreter (current kernel)

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            response = self.plugin.runner.ipython_execute(
                ctx=self.ctx,
                item=item,
                request=request,
            )
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_ipython_kernel_restart(self, item: dict) -> dict:
        """
        Restart current IPython kernel

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            response = self.plugin.runner.ipython_kernel_restart(
                ctx=self.ctx,
                item=item,
                request=request,
            )
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_code_execute_file(self, item: dict) -> dict:
        """
        Execute code command from existing file

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            if not self.plugin.runner.is_sandbox():
                response = self.plugin.runner.code_execute_file_host(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
            else:
                response = self.plugin.runner.code_execute_file_sandbox(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_code_execute(self, item: dict) -> dict:
        """
        Execute code command

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            if not self.plugin.runner.is_sandbox():
                response = self.plugin.runner.code_execute_host(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
            else:
                response = self.plugin.runner.code_execute_sandbox(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_code_execute_all(self, item: dict) -> dict:
        """
        Execute all code command

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            if not self.plugin.runner.is_sandbox():
                response = self.plugin.runner.code_execute_host(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                    all=True,
                )
            else:
                response = self.plugin.runner.code_execute_sandbox(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                    all=True,
                )
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_sys_exec(self, item: dict) -> dict:
        """
        Execute system command

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            if not self.plugin.runner.is_sandbox():
                response = self.plugin.runner.sys_exec_host(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
            else:
                response = self.plugin.runner.sys_exec_sandbox(
                    ctx=self.ctx,
                    item=item,
                    request=request,
                )
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_get_python_output(self, item: dict) -> dict:
        """
        Get python output

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            output = self.plugin.window.tools.get("interpreter").get_current_output()
            response = {
                "request": request,
                "result": output,
                "context": output,
            }
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_get_python_input(self, item: dict) -> dict:
        """
        Get python input (edit code)

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            input = self.plugin.window.tools.get("interpreter").get_current_history()
            response = {
                "request": request,
                "result": input,
                "context": input,
            }
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_clear_python_output(self, item: dict) -> dict:
        """
        Clear python output

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            self.signals.clear.emit()
            response = {
                "request": request,
                "result": "OK",
            }
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_render_html_output(self, item: dict) -> dict:
        """
        Show output in HTML canvas

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            if "params" in item and "html" in item["params"]:
                self.plugin.runner.send_html_output(item["params"]["html"])  # handle in main thread
            response = {
                "request": request,
                "result": "OK",
            }
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_get_html_output(self, item: dict) -> dict:
        """
        Get HTML canvas output

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            response = {
                "request": request,
                "result":  self.plugin.window.tools.get("html_canvas").get_output(),
                # "context": self.plugin.window.tools.get("html_canvas").get_output(),
            }
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def prepare_request(self, item) -> dict:
        """
        Prepare request item for result

        :param item: item with parameters
        :return: request item
        """
        return {"cmd": item["cmd"]}
