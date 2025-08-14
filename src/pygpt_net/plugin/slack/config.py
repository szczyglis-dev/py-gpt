# config.py
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
        # Endpoints / HTTP
        plugin.add_option(
            "api_base",
            type="text",
            value="https://slack.com/api",
            label="API base",
            description="Base Slack Web API URL.",
        )
        plugin.add_option(
            "oauth_base",
            type="text",
            value="https://slack.com",
            label="OAuth base",
            description="Base for OAuth authorize (default https://slack.com).",
        )
        plugin.add_option(
            "http_timeout",
            type="int",
            value=30,
            label="HTTP timeout (s)",
            description="Requests timeout in seconds.",
        )

        # OAuth2 (Slack)
        plugin.add_option(
            "oauth2_client_id",
            type="text",
            value="",
            label="OAuth2 Client ID",
            description="Client ID from Slack App.",
            secret=True,
        )
        plugin.add_option(
            "oauth2_client_secret",
            type="text",
            value="",
            label="OAuth2 Client Secret",
            description="Client Secret from Slack App.",
            secret=True,
        )
        plugin.add_option(
            "oauth2_redirect_uri",
            type="text",
            value="http://127.0.0.1:8733/callback",
            label="Redirect URI",
            description="Must match one of the redirect URLs in your Slack App.",
        )
        plugin.add_option(
            "bot_scopes",
            type="text",
            value="chat:write,users:read,users:read.email,channels:read,groups:read,im:read,mpim:read,channels:history,groups:history,im:history,mpim:history,files:write",
            label="Bot scopes (comma-separated)",
            description="Scopes for bot token.",
        )
        plugin.add_option(
            "user_scopes",
            type="text",
            value="",
            label="User scopes (comma-separated)",
            description="Optional user scopes (if you need a user token).",
        )

        # Tokens/cache
        plugin.add_option(
            "bot_token",
            type="textarea",
            value="",
            label="(auto/manual) Bot token",
            description="xoxb-... You can paste manually or obtain via OAuth.",
            secret=True,
        )
        plugin.add_option(
            "user_token",
            type="textarea",
            value="",
            label="(auto) User token (optional)",
            description="xoxp-... from OAuth (if user scopes requested).",
            secret=True,
        )
        plugin.add_option(
            "oauth2_refresh_token",
            type="textarea",
            value="",
            label="(auto) Refresh token (if rotation enabled)",
            description="Stored refresh token (bot or user).",
            secret=True,
        )
        plugin.add_option(
            "oauth2_expires_at",
            type="text",
            value="0",
            label="(auto) Expires at (unix)",
            description="Auto-calculated expiry time.",
        )
        plugin.add_option(
            "team_id",
            type="text",
            value="",
            label="(auto) Team ID",
            description="Cached after auth.test or OAuth.",
        )
        plugin.add_option(
            "bot_user_id",
            type="text",
            value="",
            label="(auto) Bot user ID",
            description="Cached after OAuth exchange.",
        )
        plugin.add_option(
            "authed_user_id",
            type="text",
            value="",
            label="(auto) Authed user ID",
            description="Cached after auth.test/OAuth.",
        )

        plugin.add_option(
            "oauth_auto_begin",
            type="bool",
            value=True,
            label="Auto-start OAuth when required",
            description="If a command needs token, begin OAuth flow automatically.",
        )
        plugin.add_option(
            "oauth_open_browser",
            type="bool",
            value=True,
            label="Open browser automatically",
            description="Open authorize URL in default browser.",
        )
        plugin.add_option(
            "oauth_local_server",
            type="bool",
            value=True,
            label="Use local server for OAuth",
            description="Start local HTTP server to capture redirect (requires local redirect).",
        )
        plugin.add_option(
            "oauth_local_timeout",
            type="int",
            value=180,
            label="OAuth local timeout (s)",
            description="How long to wait for redirect with code.",
        )
        plugin.add_option(
            "oauth_success_html",
            type="textarea",
            value="<html><body><h3>Authorization complete. You can close this window.</h3></body></html>",
            label="Success HTML",
            description="HTML shown on local callback success.",
        )
        plugin.add_option(
            "oauth_fail_html",
            type="textarea",
            value="<html><body><h3>Authorization failed.</h3></body></html>",
            label="Fail HTML",
            description="HTML shown on local callback error.",
        )
        plugin.add_option(
            "oauth_local_port",
            type="int",
            value=8733,
            label="OAuth local port (0=auto)",
            description="Local HTTP port for callback; use >1024. Must be registered in Slack App.",
        )
        plugin.add_option(
            "oauth_allow_port_fallback",
            type="bool",
            value=True,
            label="Allow fallback port if busy",
            description="If preferred port is busy/forbidden, pick a free local port.",
        )

        # ---------------- Commands ----------------

        # Auth
        plugin.add_cmd(
            "slack_oauth_begin",
            instruction="Begin OAuth2 flow (returns authorize URL).",
            params=[],
            enabled=True,
            description="Auth: begin OAuth2",
            tab="auth",
        )
        plugin.add_cmd(
            "slack_oauth_exchange",
            instruction="Exchange authorization code for tokens.",
            params=[
                {"name": "code", "type": "str", "required": True, "description": "Authorization code"},
                {"name": "state", "type": "str", "required": False, "description": "State (if used)"},
            ],
            enabled=True,
            description="Auth: exchange code",
            tab="auth",
        )
        plugin.add_cmd(
            "slack_oauth_refresh",
            instruction="Refresh token (if rotation enabled).",
            params=[],
            enabled=True,
            description="Auth: refresh token",
            tab="auth",
        )
        plugin.add_cmd(
            "slack_auth_test",
            instruction="Test authentication and get ids.",
            params=[],
            enabled=True,
            description="Auth: test",
            tab="auth",
        )

        # Users
        plugin.add_cmd(
            "slack_users_list",
            instruction="List workspace users (contacts).",
            params=[
                {"name": "limit", "type": "int", "required": False, "description": "Default Slack pagination"},
                {"name": "cursor", "type": "str", "required": False, "description": "Cursor for next page"},
                {"name": "include_locale", "type": "bool", "required": False, "description": "Include locale"},
            ],
            enabled=True,
            description="Users: list",
            tab="users",
        )

        # Conversations
        plugin.add_cmd(
            "slack_conversations_list",
            instruction="List channels/DMs visible to the token.",
            params=[
                {"name": "types", "type": "str", "required": False, "description": "public_channel,private_channel,im,mpim"},
                {"name": "exclude_archived", "type": "bool", "required": False, "description": "Default true"},
                {"name": "limit", "type": "int", "required": False, "description": "Default Slack pagination"},
                {"name": "cursor", "type": "str", "required": False, "description": "Cursor for next page"},
            ],
            enabled=True,
            description="Conversations: list",
            tab="conversations",
        )
        plugin.add_cmd(
            "slack_conversations_history",
            instruction="Fetch channel/DM history.",
            params=[
                {"name": "channel", "type": "str", "required": True, "description": "Conversation ID"},
                {"name": "limit", "type": "int", "required": False, "description": "Default Slack pagination"},
                {"name": "cursor", "type": "str", "required": False, "description": "Cursor for next page"},
                {"name": "oldest", "type": "str", "required": False, "description": "TS lower bound"},
                {"name": "latest", "type": "str", "required": False, "description": "TS upper bound"},
                {"name": "inclusive", "type": "bool", "required": False, "description": "Include bounds"},
            ],
            enabled=True,
            description="Conversations: history",
            tab="conversations",
        )
        plugin.add_cmd(
            "slack_conversations_replies",
            instruction="Fetch a thread by root ts.",
            params=[
                {"name": "channel", "type": "str", "required": True, "description": "Conversation ID"},
                {"name": "ts", "type": "str", "required": True, "description": "Root thread ts"},
                {"name": "limit", "type": "int", "required": False, "description": "Default Slack pagination"},
                {"name": "cursor", "type": "str", "required": False, "description": "Cursor for next page"},
            ],
            enabled=True,
            description="Conversations: replies",
            tab="conversations",
        )
        plugin.add_cmd(
            "slack_conversations_open",
            instruction="Open/resume DM or MPDM.",
            params=[
                {"name": "users", "type": "list|str", "required": False, "description": "User IDs (1..8)."},
                {"name": "channel", "type": "str", "required": False, "description": "Existing IM/MPIM id to resume"},
                {"name": "return_im", "type": "bool", "required": False, "description": "Return full obj (default true)"},
            ],
            enabled=True,
            description="Conversations: open",
            tab="conversations",
        )

        # Chat
        plugin.add_cmd(
            "slack_chat_post_message",
            instruction="Post message to channel/DM.",
            params=[
                {"name": "channel", "type": "str", "required": True, "description": "Channel/DM ID"},
                {"name": "text", "type": "str", "required": False, "description": "Message text"},
                {"name": "thread_ts", "type": "str", "required": False, "description": "Reply to thread"},
                {"name": "blocks", "type": "list|dict", "required": False, "description": "Block Kit"},
                {"name": "attachments", "type": "list", "required": False, "description": "Legacy attachments"},
                {"name": "mrkdwn", "type": "bool", "required": False, "description": "Enable markdown"},
                {"name": "unfurl_links", "type": "bool", "required": False, "description": "Unfurl links"},
                {"name": "unfurl_media", "type": "bool", "required": False, "description": "Unfurl media"},
                {"name": "reply_broadcast", "type": "bool", "required": False, "description": "Broadcast reply"},
            ],
            enabled=True,
            description="Chat: post message",
            tab="chat",
        )
        plugin.add_cmd(
            "slack_chat_delete",
            instruction="Delete a message.",
            params=[
                {"name": "channel", "type": "str", "required": True, "description": "Channel/DM ID"},
                {"name": "ts", "type": "str", "required": True, "description": "Message ts"},
            ],
            enabled=True,
            description="Chat: delete",
            tab="chat",
        )

        # Files (new upload flow)
        plugin.add_cmd(
            "slack_files_upload",
            instruction="Upload file (External flow) and share.",
            params=[
                {"name": "path", "type": "str", "required": True, "description": "Local file path"},
                {"name": "channel", "type": "str", "required": False, "description": "Share to channel id"},
                {"name": "title", "type": "str", "required": False, "description": "Title"},
                {"name": "initial_comment", "type": "str", "required": False, "description": "Comment with file"},
                {"name": "thread_ts", "type": "str", "required": False, "description": "Share in thread"},
                {"name": "alt_text", "type": "str", "required": False, "description": "Alt text (images)"},
            ],
            enabled=True,
            description="Files: upload (getUploadURLExternal + completeUploadExternal)",
            tab="files",
        )