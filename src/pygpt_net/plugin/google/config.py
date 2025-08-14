#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.14 00:00:00                  #
# ================================================== #

from pygpt_net.core.types import MODEL_DEFAULT_MINI
from pygpt_net.plugin.base.config import BaseConfig, BasePlugin


class Config(BaseConfig):
    def __init__(self, plugin: BasePlugin = None, *args, **kwargs):
        super(Config, self).__init__(plugin)
        self.plugin = plugin


    def from_defaults(self, plugin: BasePlugin = None):
        plugin.add_option(
            "credentials",
            type="textarea",
            value="",
            label="Google credentials.json (content)",
            description="Paste JSON content of your OAuth client or Service Account.",
            secret=True,
        )
        plugin.add_option(
            "oauth_token",
            type="textarea",
            value="",
            label="OAuth token store (auto)",
            description="Automatically stored/updated refresh token.",
            secret=True,
        )
        plugin.add_option(
            "oauth_local_server",
            type="bool",
            value=True,
            label="Use local server for OAuth",
            description="Run local server for installed app OAuth flow.",
        )
        plugin.add_option(
            "oauth_local_port",
            type="int",
            value=0,
            label="OAuth local port (0=random)",
            description="Port for InstalledAppFlow.run_local_server.",
        )
        plugin.add_option(
            "oauth_scopes",
            type="text",
            value="https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/contacts https://www.googleapis.com/auth/youtube.readonly",
            label="Scopes",
            description="Space-separated OAuth scopes. To use native Keep, add: https://www.googleapis.com/auth/keep and https://www.googleapis.com/auth/keep.readonly.",
        )
        plugin.add_option(
            "impersonate_user",
            type="text",
            value="",
            label="Impersonate user (Workspace DWD)",
            description="Optional subject for service account domain‑wide delegation.",
        )
        plugin.add_option(
            "youtube_api_key",
            type="text",
            value="",
            label="YouTube API Key (optional)",
            description="If provided, used for public video info without OAuth.",
            secret=True,
        )
        plugin.add_option(
            "allow_unofficial_youtube_transcript",
            type="bool",
            value=False,
            label="Allow unofficial YouTube transcript",
            description="Use youtube-transcript-api fallback when official captions are not available.",
        )
        plugin.add_option(
            "keep_mode",
            type="combo",
            value="auto",
            label="Keep mode",
            description="official | unofficial | auto",
            keys=["auto", "official", "unofficial"],
        )
        plugin.add_option(
            "allow_unofficial_keep",
            type="bool",
            value=True,
            label="Allow unofficial Keep",
            description="Enable gkeepapi fallback (needs keep_username and keep_master_token).",
        )
        plugin.add_option(
            "keep_username",
            type="text",
            value="",
            label="Keep username (unofficial)",
            description="Email for gkeepapi.",
        )
        plugin.add_option(
            "keep_master_token",
            type="text",
            value="",
            label="Keep master token (unofficial)",
            description="Master token for gkeepapi (handle securely).",
            secret=True,
        )


        # Gmail
        plugin.add_cmd(
            "gmail_list_recent",
            instruction="List n newest Gmail messages",
            params=[
                {"name": "n", "type": "int", "required": False, "description": "How many, default 10"},
                {"name": "q", "type": "str", "required": False, "description": "Gmail search query"},
                {"name": "labelIds", "type": "list", "required": False, "description": "Label IDs"},
            ],
            enabled=True,
            description="Gmail: newest mails",
            tab="gmail",
        )
        plugin.add_cmd(
            "gmail_list_all",
            instruction="List all Gmail messages (paginated)",
            params=[
                {"name": "q", "type": "str", "required": False, "description": "Gmail search query"},
                {"name": "labelIds", "type": "list", "required": False, "description": "Label IDs"},
                {"name": "limit", "type": "int", "required": False, "description": "Safety limit"},
            ],
            enabled=True,
            description="Gmail: list all",
            tab="gmail",
        )
        plugin.add_cmd(
            "gmail_search",
            instruction="Search Gmail",
            params=[
                {"name": "q", "type": "str", "required": True, "description": "Query"},
                {"name": "max", "type": "int", "required": False, "description": "Max results, default 50"},
            ],
            enabled=True,
            description="Gmail: search",
            tab="gmail",
        )
        plugin.add_cmd(
            "gmail_get_by_id",
            instruction="Get Gmail message by ID",
            params=[{"name": "id", "type": "str", "required": True, "description": "Message ID"}],
            enabled=True,
            description="Gmail: get by id",
            tab="gmail",
        )
        plugin.add_cmd(
            "gmail_send",
            instruction="Send Gmail message",
            params=[
                {"name": "to", "type": "str", "required": True, "description": "Recipient"},
                {"name": "subject", "type": "str", "required": False, "description": "Subject"},
                {"name": "body", "type": "str", "required": False, "description": "Body"},
                {"name": "html", "type": "bool", "required": False, "description": "HTML body?"},
                {"name": "cc", "type": "str", "required": False, "description": "CC"},
                {"name": "bcc", "type": "str", "required": False, "description": "BCC"},
                {"name": "attachments", "type": "list", "required": False, "description": "Local file paths"},
            ],
            enabled=True,
            description="Gmail: send",
            tab="gmail",
        )


        # Calendar
        plugin.add_cmd(
            "calendar_events_recent",
            instruction="Upcoming events (from now)",
            params=[{"name": "limit", "type": "int", "required": False, "description": "Default 10"}],
            enabled=True,
            description="Calendar: upcoming",
            tab="calendar",
        )
        plugin.add_cmd(
            "calendar_events_today",
            instruction="Events for today (UTC day bounds)",
            params=[],
            enabled=True,
            description="Calendar: today",
            tab="calendar",
        )
        plugin.add_cmd(
            "calendar_events_tomorrow",
            instruction="Events for tomorrow (UTC day bounds)",
            params=[],
            enabled=True,
            description="Calendar: tomorrow",
            tab="calendar",
        )
        plugin.add_cmd(
            "calendar_events_all",
            instruction="All events in range",
            params=[
                {"name": "timeMin", "type": "str", "required": False, "description": "RFC3339"},
                {"name": "timeMax", "type": "str", "required": False, "description": "RFC3339"},
            ],
            enabled=True,
            description="Calendar: all in range",
            tab="calendar",
        )
        plugin.add_cmd(
            "calendar_events_by_date",
            instruction="Events for date or date range",
            params=[
                {"name": "date", "type": "str", "required": True, "description": "YYYY-MM-DD or start|end RFC3339"},
            ],
            enabled=True,
            description="Calendar: by date",
            tab="calendar",
        )
        plugin.add_cmd(
            "calendar_add_event",
            instruction="Add calendar event",
            params=[
                {"name": "summary", "type": "str", "required": True, "description": "Title"},
                {"name": "start", "type": "str", "required": True, "description": "YYYY-MM-DDTHH:MM or RFC3339"},
                {"name": "end", "type": "str", "required": True, "description": "YYYY-MM-DDTHH:MM or RFC3339"},
                {"name": "timezone", "type": "str", "required": False, "description": "Default UTC"},
                {"name": "description", "type": "str", "required": False, "description": "Description"},
                {"name": "location", "type": "str", "required": False, "description": "Location"},
                {"name": "attendees", "type": "list", "required": False, "description": "Emails"},
            ],
            enabled=True,
            description="Calendar: add event",
            tab="calendar",
        )
        plugin.add_cmd(
            "calendar_delete_event",
            instruction="Delete event by ID",
            params=[{"name": "event_id", "type": "str", "required": True, "description": "Event ID"}],
            enabled=True,
            description="Calendar: delete",
            tab="calendar",
        )


        # Keep
        plugin.add_cmd(
            "keep_list_notes",
            instruction="List notes (Keep)",
            params=[{"name": "limit", "type": "int", "required": False, "description": "Default 50"}],
            enabled=True,
            description="Keep: list notes",
            tab="keep",
        )
        plugin.add_cmd(
            "keep_add_note",
            instruction="Add note (Keep)",
            params=[
                {"name": "title", "type": "str", "required": False, "description": "Title"},
                {"name": "text", "type": "str", "required": False, "description": "Content"},
            ],
            enabled=True,
            description="Keep: add note",
            tab="keep",
        )


        # Drive
        plugin.add_cmd(
            "drive_list_files",
            instruction="List Drive files",
            params=[
                {"name": "q", "type": "str", "required": False, "description": "Drive query"},
                {"name": "page_size", "type": "int", "required": False, "description": "Default 100"},
                {"name": "fields", "type": "str", "required": False, "description": "Fields mask"},
            ],
            enabled=True,
            description="Drive: list files",
            tab="drive",
        )
        plugin.add_cmd(
            "drive_find_by_path",
            instruction="Find Drive file by path",
            params=[{"name": "path", "type": "str", "required": True, "description": "/Folder/Sub/file.ext"}],
            enabled=True,
            description="Drive: find by path",
            tab="drive",
        )
        plugin.add_cmd(
            "drive_download_file",
            instruction="Download Drive file",
            params=[
                {"name": "file_id", "type": "str", "required": False, "description": "File ID"},
                {"name": "path", "type": "str", "required": False, "description": "Drive path (alternative)"},
                {"name": "out", "type": "str", "required": False, "description": "Local output path"},
                {"name": "export_mime", "type": "str", "required": False, "description": "Export mime for Docs"},
            ],
            enabled=True,
            description="Drive: download",
            tab="drive",
        )
        plugin.add_cmd(
            "drive_upload_file",
            instruction="Upload local file to Drive",
            params=[
                {"name": "local", "type": "str", "required": True, "description": "Local file path"},
                {"name": "remote_parent_path", "type": "str", "required": False, "description": "Drive folder path"},
                {"name": "name", "type": "str", "required": False, "description": "Remote name"},
                {"name": "mime", "type": "str", "required": False, "description": "Mime type"},
            ],
            enabled=True,
            description="Drive: upload",
            tab="drive",
        )


        # YouTube
        plugin.add_cmd(
            "youtube_video_info",
            instruction="Get YouTube video info",
            params=[{"name": "video", "type": "str", "required": True, "description": "Video ID or URL"}],
            enabled=True,
            description="YouTube: video info",
            tab="youtube",
        )
        plugin.add_cmd(
            "youtube_transcript",
            instruction="Get YouTube transcript",
            params=[
                {"name": "video", "type": "str", "required": True, "description": "Video ID or URL"},
                {"name": "languages", "type": "list", "required": False, "description": "Preferred languages"},
                {"name": "official_only", "type": "bool", "required": False, "description": "Force official API"},
                {"name": "format", "type": "str", "required": False, "description": "srt|vtt|ttml"},
            ],
            enabled=True,
            description="YouTube: transcript (official or optional unofficial)",
            tab="youtube",
        )


        # Contacts
        plugin.add_cmd(
            "contacts_list",
            instruction="List contacts",
            params=[
                {"name": "page_size", "type": "int", "required": False, "description": "Default 200"},
                {"name": "person_fields", "type": "str", "required": False, "description": "Fields mask"},
            ],
            enabled=True,
            description="Contacts: list",
            tab="contacts",
        )
        plugin.add_cmd(
            "contacts_add",
            instruction="Add new contact",
            params=[
                {"name": "givenName", "type": "str", "required": False, "description": "Given name"},
                {"name": "familyName", "type": "str", "required": False, "description": "Family name"},
                {"name": "emails", "type": "list", "required": False, "description": "Email list"},
                {"name": "phones", "type": "list", "required": False, "description": "Phone list"},
            ],
            enabled=True,
            description="Contacts: add",
            tab="contacts",
        )