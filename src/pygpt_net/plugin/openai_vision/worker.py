#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.18 21:00:00                  #
# ================================================== #

from PySide6.QtCore import Slot, Signal
from pygpt_net.plugin.base.worker import BaseWorker, BaseSignals

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
            if self.is_stopped():
                break
            response = None
            try:
                if item["cmd"] in self.plugin.allowed_cmds and self.plugin.has_cmd(item["cmd"]):

                    if item["cmd"] == "camera_capture":
                        response = self.cmd_camera_capture(item)

                    elif item["cmd"] == "make_screenshot":
                        response = self.cmd_make_screenshot(item)

                    elif item["cmd"] == "analyze_image_attachment":
                        response = self.cmd_analyze_image_attachment(item)

                    elif item["cmd"] == "analyze_screenshot":
                        response = self.cmd_analyze_screenshot(item)

                    elif item["cmd"] == "analyze_camera_capture":
                        response = self.cmd_analyze_camera_capture(item)

                    if response:
                        responses.append(response)

            except Exception as e:
                responses.append(
                    self.make_response(
                        item,
                        self.throw_error(e)
                    )
                )

        # send response
        if len(responses) > 0:
            self.reply_more(responses)

    def cmd_camera_capture(self, item: dict) -> dict:
        """
        Capture image from camera

        :param item: command item
        :return: response item
        """
        try:
            if self.window.controller.camera.internal_capture():
                result = "OK"
            else:
                result = "FAILED"
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_make_screenshot(self, item: dict) -> dict:
        """
        Make desktop screenshot

        :param item: command item
        :return: response item
        """
        try:
            self.window.controller.painter.capture.screenshot()
            result = "OK"
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_analyze_image_attachment(self, item: dict) -> dict:
        """
        Analyze image attachment

        :param item: command item
        :return: response item
        """
        try:
            prompt = ""
            if self.has_param(item, "prompt"):
                prompt = self.get_param(item, "prompt")
            path = ""
            if self.has_param(item, "path"):
                path = self.get_param(item, "path")
            result = self.window.core.vision.analyzer.from_path(
                ctx=self.ctx,
                prompt=prompt,
                path=path,
            )
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_analyze_screenshot(self, item: dict) -> dict:
        """
        Analyze screenshot

        :param item: command item
        :return: response item
        """
        try:
            prompt = ""
            if self.has_param(item, "prompt"):
                prompt = self.get_param(item, "prompt")
            result = self.window.core.vision.analyzer.from_screenshot(
                ctx=self.ctx,
                prompt=prompt,
            )
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_analyze_camera_capture(self, item: dict) -> dict:
        """
        Analyze camera capture

        :param item: command item
        :return: response item
        """
        try:
            prompt = ""
            if self.has_param(item, "prompt"):
                prompt = self.get_param(item, "prompt")
            result = self.window.core.vision.analyzer.from_camera(
                ctx=self.ctx,
                prompt=prompt,
            )
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)
