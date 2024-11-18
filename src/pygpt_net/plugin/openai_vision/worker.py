#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 00:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, Signal
from pygpt_net.plugin.base import BaseWorker, BaseSignals

class WorkerSignals(BaseSignals):
    screenshot = Signal(dict, object)

class Worker(BaseWorker):
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        self.signals = WorkerSignals()
        self.window = None
        self.args = args
        self.kwargs = kwargs
        self.plugin = None
        self.cmds = None
        self.ctx = None
        self.msg = None

    @Slot()
    def run(self):
        responses = []
        for item in self.cmds:
            response = None
            try:
                if item["cmd"] in self.plugin.allowed_cmds and self.plugin.has_cmd(item["cmd"]):

                    if item["cmd"] == "camera_capture":
                        response = self.cmd_camera_capture(item)

                    elif item["cmd"] == "make_screenshot":
                        response = self.cmd_make_screenshot(item)

                    elif item["cmd"] == "analyze_image_attachment":
                        print("Analyze image attachment")
                        response = self.cmd_analyze_image_attachment(item)

                    elif item["cmd"] == "analyze_screenshot":
                        print("Analyze screenshot")
                        response = self.cmd_analyze_screenshot(item)

                    elif item["cmd"] == "analyze_camera_capture":
                        print("Analyze camera capture")
                        response = self.cmd_analyze_camera_capture(item)

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

    def cmd_camera_capture(self, item: dict) -> dict:
        """
        Capture image from camera

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            self.window.controller.camera.manual_capture(force=True)
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

    def cmd_make_screenshot(self, item: dict) -> dict:
        """
        Make desktop screenshot

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            self.window.controller.painter.capture.screenshot()
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

    def cmd_analyze_image_attachment(self, item: dict) -> dict:
        """
        Analyze image attachment

        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            prompt = ""
            if "params" in item and "prompt" in item["params"]:
                prompt = item["params"]["prompt"]
            path = ""
            if "params" in item and "path" in item["params"]:
                path = item["params"]["path"]
            result = self.window.core.vision.analyzer.from_path(
                ctx=self.ctx,
                prompt=prompt,
                path=path,
            )
            response = {
                "request": request,
                "result": result,
            }
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_analyze_screenshot(self, item: dict) -> dict:
        """
        Analyze screenshot

        :param ctx: context
        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            prompt = ""
            if "params" in item and "prompt" in item["params"]:
                prompt = item["params"]["prompt"]
            result = self.window.core.vision.analyzer.from_screenshot(
                ctx=self.ctx,
                prompt=prompt,
            )
            response = {
                "request": request,
                "result": result,
            }
        except Exception as e:
            response = {
                "request": request,
                "result": "Error: {}".format(e),
            }
            self.error(e)
            self.log("Error: {}".format(e))
        return response

    def cmd_analyze_camera_capture(self, item: dict) -> dict:
        """
        Analyze camera capture

        :param ctx: context
        :param item: command item
        :return: response item
        """
        request = self.prepare_request(item)
        try:
            prompt = ""
            if "params" in item and "prompt" in item["params"]:
                prompt = item["params"]["prompt"]
            result = self.window.core.vision.analyzer.from_camera(
                ctx=self.ctx,
                prompt=prompt,
            )
            response = {
                "request": request,
                "result": result,
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
