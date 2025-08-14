#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.14 00:00:00                  #
# ================================================== #

from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin

    def from_defaults(self, plugin: BasePlugin = None):
        # Mode / HTTP
        plugin.add_option(
            "mode",
            type="combo",
            value="bot",
            keys=["bot", "user"],
            label="Mode",
            description="bot = Bot API (token). user = User account via Telethon.",
        )
        plugin.add_option(
            "api_base",
            type="text",
            value="https://api.telegram.org",
            label="API base (Bot)",
            description="Telegram Bot API base.",
        )
        plugin.add_option(
            "http_timeout",
            type="int",
            value=30,
            label="HTTP timeout (s)",
            description="Requests timeout in seconds.",
        )

        # Bot options
        plugin.add_option(
            "bot_token",
            type="textarea",
            value="",
            label="Bot token",
            description="Token from BotFather.",
            secret=True,
        )
        plugin.add_option(
            "default_parse_mode",
            type="combo",
            value="HTML",
            keys=["", "HTML", "Markdown", "MarkdownV2"],
            label="Default parse_mode",
            description="Default parse mode for sending text/captions.",
        )
        plugin.add_option(
            "default_disable_preview",
            type="bool",
            value=False,
            label="Disable link previews (default)",
            description="Applies when not overridden in command.",
        )
        plugin.add_option(
            "default_disable_notification",
            type="bool",
            value=False,
            label="Disable notifications (default)",
            description="Applies when not overridden in command.",
        )
        plugin.add_option(
            "default_protect_content",
            type="bool",
            value=False,
            label="Protect content (default)",
            description="Applies when not overridden in command.",
        )
        plugin.add_option(
            "last_update_id",
            type="text",
            value="",
            label="(auto) last update id",
            description="Stored after tg_get_updates.",
        )

        # User options (Telethon)
        plugin.add_option(
            "api_id",
            type="text",
            value="",
            label="API ID (user mode)",
            description="Get from https://my.telegram.org (Development tools).",
            secret=False,
        )
        plugin.add_option(
            "api_hash",
            type="text",
            value="",
            label="API Hash (user mode)",
            description="Get from https://my.telegram.org (Development tools).",
            secret=True,
        )
        plugin.add_option(
            "phone_number",
            type="text",
            value="",
            label="Phone number (+CC...)",
            description="Used to send login code in user mode.",
        )
        plugin.add_option(
            "password_2fa",
            type="text",
            value="",
            label="(optional) 2FA password",
            description="Used if your account has two-step verification.",
            secret=True,
        )
        plugin.add_option(
            "user_session",
            type="textarea",
            value="",
            label="(auto) Session (StringSession)",
            description="Saved after successful login in user mode.",
            secret=True,
        )
        plugin.add_option(
            "auto_login_begin",
            type="bool",
            value=True,
            label="Auto-begin login when needed",
            description="If a user command needs auth and session missing, send code automatically (requires phone).",
        )

        # ---------------- Commands ----------------

        # Auth (user)
        plugin.add_cmd(
            "tg_login_begin",
            instruction="Begin Telegram user login (sends code to phone).",
            params=[
                {"name": "phone", "type": "str", "required": False, "description": "Phone E.164 (defaults to option)"},
            ],
            enabled=True,
            description="Auth (user): begin login",
            tab="auth",
        )
        plugin.add_cmd(
            "tg_login_complete",
            instruction="Complete login with code (and optional 2FA password).",
            params=[
                {"name": "phone", "type": "str", "required": False, "description": "Phone E.164 (defaults to option)"},
                {"name": "code", "type": "str", "required": True, "description": "Code received in Telegram"},
                {"name": "password", "type": "str", "required": False, "description": "2FA password if required"},
            ],
            enabled=True,
            description="Auth (user): complete login",
            tab="auth",
        )
        plugin.add_cmd(
            "tg_logout",
            instruction="Log out and clear saved session.",
            params=[],
            enabled=True,
            description="Auth (user): logout",
            tab="auth",
        )

        # Info
        plugin.add_cmd(
            "tg_mode",
            instruction="Return current mode (bot|user).",
            params=[],
            enabled=True,
            description="Info: mode",
            tab="info",
        )
        plugin.add_cmd(
            "tg_me",
            instruction="Get authorized identity: Bot getMe or User get_me.",
            params=[],
            enabled=True,
            description="Info: me",
            tab="info",
        )

        # Messaging
        plugin.add_cmd(
            "tg_send_message",
            instruction="Send text message to chat/channel.",
            params=[
                {"name": "chat", "type": "str", "required": True, "description": "chat id or @username"},
                {"name": "text", "type": "str", "required": True, "description": "Message text"},
                {"name": "parse_mode", "type": "str", "required": False, "description": "HTML|Markdown|MarkdownV2"},
                {"name": "disable_web_page_preview", "type": "bool", "required": False, "description": "Default from options"},
                {"name": "disable_notification", "type": "bool", "required": False, "description": "Default from options"},
                {"name": "protect_content", "type": "bool", "required": False, "description": "Default from options"},
                {"name": "reply_to_message_id", "type": "int", "required": False, "description": "Reply to"},
            ],
            enabled=True,
            description="Messaging: send message",
            tab="messages",
        )
        plugin.add_cmd(
            "tg_send_photo",
            instruction="Send photo to chat/channel.",
            params=[
                {"name": "chat", "type": "str", "required": True, "description": "chat id or @username"},
                {"name": "photo", "type": "str", "required": True, "description": "Local path, URL or file_id"},
                {"name": "caption", "type": "str", "required": False, "description": "Caption"},
                {"name": "parse_mode", "type": "str", "required": False, "description": "HTML|Markdown|MarkdownV2"},
                {"name": "disable_notification", "type": "bool", "required": False, "description": "Default from options"},
                {"name": "protect_content", "type": "bool", "required": False, "description": "Default from options"},
            ],
            enabled=True,
            description="Messaging: send photo",
            tab="messages",
        )
        plugin.add_cmd(
            "tg_send_document",
            instruction="Send document/file to chat/channel.",
            params=[
                {"name": "chat", "type": "str", "required": True, "description": "chat id or @username"},
                {"name": "document", "type": "str", "required": True, "description": "Local path, URL or file_id"},
                {"name": "caption", "type": "str", "required": False, "description": "Caption"},
                {"name": "disable_notification", "type": "bool", "required": False, "description": "Default from options"},
                {"name": "protect_content", "type": "bool", "required": False, "description": "Default from options"},
            ],
            enabled=True,
            description="Messaging: send document",
            tab="messages",
        )

        # Chats
        plugin.add_cmd(
            "tg_get_chat",
            instruction="Get chat info by id or @username.",
            params=[
                {"name": "chat", "type": "str", "required": True, "description": "chat id or @username"},
            ],
            enabled=True,
            description="Chats: get chat",
            tab="chats",
        )

        # Updates / Files (bot)
        plugin.add_cmd(
            "tg_get_updates",
            instruction="Poll updates (bot mode). Stores last_update_id automatically.",
            params=[
                {"name": "offset", "type": "int", "required": False, "description": "Start from this update_id+1"},
                {"name": "timeout", "type": "int", "required": False, "description": "Long polling timeout seconds"},
                {"name": "allowed_updates", "type": "list", "required": False, "description": "update types list"},
            ],
            enabled=True,
            description="Bot: getUpdates",
            tab="updates",
        )
        plugin.add_cmd(
            "tg_download_file",
            instruction="Download file by file_id (bot mode).",
            params=[
                {"name": "file_id", "type": "str", "required": True, "description": "file_id from a message"},
                {"name": "save_as", "type": "str", "required": False, "description": "Local path (relative=./data)"},
            ],
            enabled=True,
            description="Bot: download file",
            tab="updates",
        )

        # Contacts / Dialogs / Messages (user)
        plugin.add_cmd(
            "tg_contacts_list",
            instruction="List contacts (user mode).",
            params=[],
            enabled=True,
            description="User: contacts list",
            tab="user",
        )
        plugin.add_cmd(
            "tg_dialogs_list",
            instruction="List recent dialogs/chats (user mode).",
            params=[
                {"name": "limit", "type": "int", "required": False, "description": "Default 20"},
            ],
            enabled=True,
            description="User: dialogs list",
            tab="user",
        )
        plugin.add_cmd(
            "tg_messages_get",
            instruction="Get recent messages from chat (user mode).",
            params=[
                {"name": "chat", "type": "str", "required": True, "description": "chat id or @username"},
                {"name": "limit", "type": "int", "required": False, "description": "Default 30"},
                {"name": "offset_id", "type": "int", "required": False, "description": "Pagination"},
                {"name": "min_id", "type": "int", "required": False, "description": "Fetch > min_id"},
                {"name": "max_id", "type": "int", "required": False, "description": "Fetch < max_id"},
                {"name": "search", "type": "str", "required": False, "description": "Search query"},
            ],
            enabled=True,
            description="User: messages get",
            tab="user",
        )