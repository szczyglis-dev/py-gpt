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
            value="https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/contacts https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/documents",
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

        # Google Maps API keys
        plugin.add_option(
            "google_maps_api_key",
            type="text",
            value="",
            label="Google Maps API Key",
            description="Used for Geocoding, Directions, Distance Matrix, Places, Static Maps.",
            secret=True,
        )
        plugin.add_option(
            "maps_api_key",
            type="text",
            value="",
            label="Maps API Key (alias)",
            description="Alias for google_maps_api_key (backward compatibility).",
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

        # Google Docs
        plugin.add_cmd(
            "docs_create",
            instruction="Create Google Doc",
            params=[
                {"name": "title", "type": "str", "required": False, "description": "Document title (default Untitled)"},
            ],
            enabled=True,
            description="Docs: create document",
            tab="docs",
        )
        plugin.add_cmd(
            "docs_get",
            instruction="Get Google Doc (structure + plain text)",
            params=[
                {"name": "document_id", "type": "str", "required": False, "description": "Document ID"},
                {"name": "path", "type": "str", "required": False, "description": "Drive path (alternative)"},
            ],
            enabled=True,
            description="Docs: get document",
            tab="docs",
        )
        plugin.add_cmd(
            "docs_list",
            instruction="List Google Docs",
            params=[
                {"name": "q", "type": "str", "required": False, "description": "Name contains"},
                {"name": "page_size", "type": "int", "required": False, "description": "Default 100"},
            ],
            enabled=True,
            description="Docs: list documents",
            tab="docs",
        )
        plugin.add_cmd(
            "docs_append_text",
            instruction="Append text to Google Doc",
            params=[
                {"name": "document_id", "type": "str", "required": False, "description": "Document ID"},
                {"name": "path", "type": "str", "required": False, "description": "Drive path (alternative)"},
                {"name": "text", "type": "str", "required": True, "description": "Text to append"},
                {"name": "newline", "type": "bool", "required": False, "description": "Prepend newline (default True)"},
            ],
            enabled=True,
            description="Docs: append text",
            tab="docs",
        )
        plugin.add_cmd(
            "docs_replace_text",
            instruction="Replace all text occurrences in Google Doc",
            params=[
                {"name": "document_id", "type": "str", "required": False, "description": "Document ID"},
                {"name": "path", "type": "str", "required": False, "description": "Drive path (alternative)"},
                {"name": "find", "type": "str", "required": True, "description": "Find pattern (literal)"},
                {"name": "replace", "type": "str", "required": False, "description": "Replacement (can be empty)"},
                {"name": "matchCase", "type": "bool", "required": False, "description": "Match case"},
            ],
            enabled=True,
            description="Docs: replace text",
            tab="docs",
        )
        plugin.add_cmd(
            "docs_insert_heading",
            instruction="Insert heading at end of Google Doc",
            params=[
                {"name": "document_id", "type": "str", "required": False, "description": "Document ID"},
                {"name": "path", "type": "str", "required": False, "description": "Drive path (alternative)"},
                {"name": "text", "type": "str", "required": True, "description": "Heading text"},
                {"name": "level", "type": "int", "required": False, "description": "Heading level 1..6"},
            ],
            enabled=True,
            description="Docs: insert heading",
            tab="docs",
        )
        plugin.add_cmd(
            "docs_export",
            instruction="Export Google Doc to file",
            params=[
                {"name": "document_id", "type": "str", "required": False, "description": "Document ID"},
                {"name": "path", "type": "str", "required": False, "description": "Drive path (alternative)"},
                {"name": "mime", "type": "str", "required": False, "description": "application/pdf, text/plain, docx"},
                {"name": "out", "type": "str", "required": False, "description": "Local output path"},
            ],
            enabled=True,
            description="Docs: export document",
            tab="docs",
        )
        plugin.add_cmd(
            "docs_copy_from_template",
            instruction="Make a copy of template Google Doc",
            params=[
                {"name": "template_id", "type": "str", "required": False, "description": "Template Doc ID"},
                {"name": "template_path", "type": "str", "required": False, "description": "Template Drive path"},
                {"name": "title", "type": "str", "required": False, "description": "New document title"},
            ],
            enabled=True,
            description="Docs: copy from template",
            tab="docs",
        )

        # Google Maps
        plugin.add_cmd(
            "maps_geocode",
            instruction="Geocode an address",
            params=[
                {"name": "address", "type": "str", "required": True, "description": "Address to geocode"},
                {"name": "language", "type": "str", "required": False, "description": "Response language"},
                {"name": "region", "type": "str", "required": False, "description": "Region bias, e.g. 'pl'"},
            ],
            enabled=True,
            description="Maps: geocode",
            tab="maps",
        )
        plugin.add_cmd(
            "maps_reverse_geocode",
            instruction="Reverse geocode coordinates",
            params=[
                {"name": "lat", "type": "str", "required": True, "description": "Latitude"},
                {"name": "lng", "type": "str", "required": True, "description": "Longitude"},
                {"name": "language", "type": "str", "required": False, "description": "Response language"},
            ],
            enabled=True,
            description="Maps: reverse geocode",
            tab="maps",
        )
        plugin.add_cmd(
            "maps_directions",
            instruction="Get directions between origin and destination",
            params=[
                {"name": "origin", "type": "str", "required": True, "description": "Origin (address or 'lat,lng')"},
                {"name": "destination", "type": "str", "required": True,
                 "description": "Destination (address or 'lat,lng')"},
                {"name": "mode", "type": "str", "required": False, "description": "driving|walking|bicycling|transit"},
                {"name": "departure_time", "type": "str", "required": False, "description": "'now' or epoch seconds"},
                {"name": "waypoints", "type": "list", "required": False, "description": "List of waypoints"},
            ],
            enabled=True,
            description="Maps: directions",
            tab="maps",
        )
        plugin.add_cmd(
            "maps_distance_matrix",
            instruction="Distance Matrix for origins and destinations",
            params=[
                {"name": "origins", "type": "list", "required": True, "description": "List of origins"},
                {"name": "destinations", "type": "list", "required": True, "description": "List of destinations"},
                {"name": "mode", "type": "str", "required": False, "description": "driving|walking|bicycling|transit"},
            ],
            enabled=True,
            description="Maps: distance matrix",
            tab="maps",
        )
        plugin.add_cmd(
            "maps_places_textsearch",
            instruction="Places Text Search",
            params=[
                {"name": "query", "type": "str", "required": True, "description": "Free-form query, e.g. 'coffee'"},
                {"name": "location", "type": "str", "required": False, "description": "Bias 'lat,lng'"},
                {"name": "radius", "type": "int", "required": False, "description": "Radius in meters"},
                {"name": "type", "type": "str", "required": False, "description": "Place type"},
                {"name": "opennow", "type": "bool", "required": False, "description": "Open now filter"},
            ],
            enabled=True,
            description="Maps: places text search",
            tab="maps",
        )
        plugin.add_cmd(
            "maps_places_nearby",
            instruction="Nearby Places",
            params=[
                {"name": "location", "type": "str", "required": True, "description": "'lat,lng'"},
                {"name": "radius", "type": "int", "required": True, "description": "Radius in meters"},
                {"name": "keyword", "type": "str", "required": False, "description": "Keyword"},
                {"name": "type", "type": "str", "required": False, "description": "Place type"},
            ],
            enabled=True,
            description="Maps: places nearby",
            tab="maps",
        )
        plugin.add_cmd(
            "maps_static_map",
            instruction="Generate Static Map image",
            params=[
                {"name": "center", "type": "str", "required": False,
                 "description": "Center 'lat,lng' (optional if markers)"},
                {"name": "zoom", "type": "int", "required": False, "description": "Zoom level (default 13)"},
                {"name": "size", "type": "str", "required": False, "description": "WxH, e.g. 600x400"},
                {"name": "markers", "type": "list", "required": False, "description": "List of 'lat,lng'"},
                {"name": "maptype", "type": "str", "required": False,
                 "description": "roadmap|satellite|terrain|hybrid"},
                {"name": "out", "type": "str", "required": False, "description": "Local output path (png)"},
            ],
            enabled=True,
            description="Maps: static map",
            tab="maps",
        )

        # Google Colab
        plugin.add_cmd(
            "colab_list_notebooks",
            instruction="List Colab notebooks on Drive",
            params=[
                {"name": "q", "type": "str", "required": False, "description": "Name contains"},
                {"name": "page_size", "type": "int", "required": False, "description": "Default 100"},
            ],
            enabled=True,
            description="Colab: list notebooks",
            tab="colab",
        )
        plugin.add_cmd(
            "colab_create_notebook",
            instruction="Create new Colab notebook",
            params=[
                {"name": "name", "type": "str", "required": True, "description": "Filename, e.g. notebook.ipynb"},
                {"name": "remote_parent_path", "type": "str", "required": False,
                 "description": "Target Drive folder path"},
                {"name": "markdown", "type": "str", "required": False, "description": "Initial markdown cell"},
                {"name": "code", "type": "str", "required": False, "description": "Initial code cell"},
            ],
            enabled=True,
            description="Colab: create notebook",
            tab="colab",
        )
        plugin.add_cmd(
            "colab_add_code_cell",
            instruction="Add code cell to notebook",
            params=[
                {"name": "file_id", "type": "str", "required": False, "description": "Notebook file ID"},
                {"name": "path", "type": "str", "required": False, "description": "Drive path (alternative)"},
                {"name": "code", "type": "str", "required": True, "description": "Code source"},
                {"name": "position", "type": "int", "required": False,
                 "description": "Insert index (append if omitted)"},
            ],
            enabled=True,
            description="Colab: add code cell",
            tab="colab",
        )
        plugin.add_cmd(
            "colab_add_markdown_cell",
            instruction="Add markdown cell to notebook",
            params=[
                {"name": "file_id", "type": "str", "required": False, "description": "Notebook file ID"},
                {"name": "path", "type": "str", "required": False, "description": "Drive path (alternative)"},
                {"name": "markdown", "type": "str", "required": True, "description": "Markdown source"},
                {"name": "position", "type": "int", "required": False,
                 "description": "Insert index (append if omitted)"},
            ],
            enabled=True,
            description="Colab: add markdown cell",
            tab="colab",
        )
        plugin.add_cmd(
            "colab_get_link",
            instruction="Get Colab edit link",
            params=[
                {"name": "file_id", "type": "str", "required": False, "description": "Notebook file ID"},
                {"name": "path", "type": "str", "required": False, "description": "Drive path (alternative)"},
            ],
            enabled=True,
            description="Colab: get link",
            tab="colab",
        )
        plugin.add_cmd(
            "colab_rename",
            instruction="Rename notebook",
            params=[
                {"name": "file_id", "type": "str", "required": False, "description": "Notebook file ID"},
                {"name": "path", "type": "str", "required": False, "description": "Drive path (alternative)"},
                {"name": "name", "type": "str", "required": True, "description": "New filename"},
            ],
            enabled=True,
            description="Colab: rename notebook",
            tab="colab",
        )
        plugin.add_cmd(
            "colab_duplicate",
            instruction="Duplicate notebook",
            params=[
                {"name": "file_id", "type": "str", "required": False, "description": "Notebook file ID"},
                {"name": "path", "type": "str", "required": False, "description": "Drive path (alternative)"},
                {"name": "name", "type": "str", "required": False, "description": "New name (default Copy.ipynb)"},
                {"name": "remote_parent_path", "type": "str", "required": False,
                 "description": "Target Drive folder path"},
            ],
            enabled=True,
            description="Colab: duplicate notebook",
            tab="colab",
        )