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

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        """
        Set default options for plugin

        :param plugin: plugin instance
        """
        plugin.add_option(
            "smtp_host",
            type="text",
            value="",
            label="SMTP Host",
            persist=True,
            tab="smtp",
        )
        plugin.add_option(
            "smtp_port_inbox",
            type="int",
            value=995,
            label="SMTP Port (Inbox)",
            persist=True,
            tab="smtp",
        )
        plugin.add_option(
            "smtp_port_outbox",
            type="int",
            value=465,
            label="SMTP Port (Outbox)",
            persist=True,
            tab="smtp",
        )
        plugin.add_option(
            "smtp_user",
            type="text",
            value="",
            label="SMTP User",
            persist=True,
            tab="smtp",
        )
        plugin.add_option(
            "smtp_password",
            type="text",
            value="",
            label="SMTP Password",
            secret=True,
            persist=True,
            tab="smtp",
        )
        plugin.add_option(
            "from_email",
            type="text",
            value="",
            label="From (email)",
        )
        plugin.add_cmd(
            "send_email",
            instruction="Send email to specified address",
            params=[
                {
                    "name": "recipient",
                    "type": "str",
                    "description": "Recipient email address",
                    "required": True,
                },
                {
                    "name": "subject",
                    "type": "str",
                    "description": "Email subject",
                    "required": True,
                },
                {
                    "name": "message",
                    "type": "str",
                    "description": "Email message",
                    "required": True,
                },
            ],
            enabled=True,
            description="Allows sending emails",
            tab="general",
        )
        plugin.add_cmd(
            "get_emails",
            instruction="Retrieve emails from the inbox. Use this to access emails from the inbox when the user "
                        "requests fetching emails from their server.",
            params=[
                {
                    "name": "limit",
                    "type": "int",
                    "description": "Limit of emails to receive, default: 10",
                    "required": True,
                },
                {
                    "name": "offset",
                    "type": "int",
                    "description": "Offset of emails to receive, default: 0",
                    "required": False,
                },
                {
                    "name": "order",
                    "type": "text",
                    "description": "Sort order, default: desc, options: asc, desc",
                    "required": False,
                },
            ],
            enabled=True,
            description="Allows receiving emails",
            tab="general",
        )
        plugin.add_cmd(
            "get_email_body",
            instruction="Retrieve the complete email content from the inbox. Use this to access the message body. "
                        "To obtain email IDs, use the 'get_emails' function first.",
            params=[
                {
                    "name": "id",
                    "type": "int",
                    "description": "Email ID (index)",
                    "required": True,
                },
                {
                    "name": "format",
                    "type": "text",
                    "description": "Display format, default: text, options: text, html",
                    "required": False,
                },
            ],
            enabled=True,
            description="Allows receiving email body",
            tab="general",
        )