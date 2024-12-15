#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.15 04:00:00                  #
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
        responses = []
        for item in self.cmds:
            if self.is_stopped():
                break
            try:
                response = None
                if (item["cmd"] in self.plugin.allowed_cmds
                        and (self.plugin.has_cmd(item["cmd"]) or 'force' in item)):

                    if item["cmd"] == "send_email":
                        response = self.cmd_send_mail(item)

                    elif item["cmd"] == "get_emails":
                        response = self.cmd_receive_emails(item)

                    elif item["cmd"] == "get_email_body":
                        response = self.cmd_get_email_body(item)

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

    def cmd_send_mail(self, item: dict) -> dict:
        """
        Send email command

        :param item: command item
        :return: response item
        """
        request = self.from_request(item)
        try:
            result = self.plugin.runner.smtp_send_email(
                ctx=self.ctx,
                item=item,
                request=request,
            )
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_receive_emails(self, item: dict) -> dict:
        """
        Receive emails command

        :param item: command item
        :return: response item
        """
        request = self.from_request(item)
        try:
            result = self.plugin.runner.smtp_receive_emails(
                ctx=self.ctx,
                item=item,
                request=request,
            )
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

    def cmd_get_email_body(self, item: dict) -> dict:
        """
        Get email body command

        :param item: command item
        :return: response item
        """
        request = self.from_request(item)
        try:
            result = self.plugin.runner.smtp_get_email_body(
                ctx=self.ctx,
                item=item,
                request=request,
            )
        except Exception as e:
            result = self.throw_error(e)
        return self.make_response(item, result)

