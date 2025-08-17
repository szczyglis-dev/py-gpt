#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.15 23:00:00                  #
# ================================================== #


from pygpt_net.plugin.base.plugin import BasePlugin
from pygpt_net.core.events import Event
from pygpt_net.item.ctx import CtxItem

from .config import Config


class Plugin(BasePlugin):
    def __init__(self, *args, **kwargs):
        super(Plugin, self).__init__(*args, **kwargs)
        self.id = "google"
        self.name = "Google"
        self.description = "Access Gmail, Drive, Calendar, Contacts, YouTube, Keep for managing emails, files, events, notes, video info, and contacts."
        self.prefix = "API"
        self.order = 100
        self.allowed_cmds =  [
            "gmail_list_recent",
            "gmail_list_all",
            "gmail_search",
            "gmail_get_by_id",
            "gmail_send",
            "calendar_events_recent",
            "calendar_events_today",
            "calendar_events_tomorrow",
            "calendar_events_all",
            "calendar_events_by_date",
            "calendar_add_event",
            "calendar_delete_event",
            "keep_list_notes",
            "keep_add_note",
            "drive_list_files",
            "drive_find_by_path",
            "drive_download_file",
            "drive_upload_file",
            "youtube_video_info",
            "youtube_transcript",
            "contacts_list",
            "contacts_add",
            "docs_create",
            "docs_get",
            "docs_list",
            "docs_append_text",
            "docs_replace_text",
            "docs_insert_heading",
            "docs_export",
            "docs_copy_from_template",
            "maps_geocode",
            "maps_reverse_geocode",
            "maps_directions",
            "maps_distance_matrix",
            "maps_places_textsearch",
            "maps_places_nearby",
            "maps_static_map",
            "colab_list_notebooks",
            "colab_create_notebook",
            "colab_add_code_cell",
            "colab_add_markdown_cell",
            "colab_get_link",
            "colab_rename",
            "colab_duplicate",
        ]
        self.use_locale = False
        self.worker = None
        self.config = Config(self)
        self.init_options()

    def init_options(self):
        """Initialize options"""
        self.config.from_defaults(self)

    def handle(self, event: Event, *args, **kwargs):
        """
        Handle dispatched event

        :param event: event object
        :param args: event args
        :param kwargs: event kwargs
        """
        name = event.name
        data = event.data
        ctx = event.ctx

        if name == Event.CMD_SYNTAX:
            self.cmd_syntax(data)

        elif name == Event.CMD_EXECUTE:
            self.cmd(
                ctx,
                data['commands'],
            )

    def cmd_syntax(self, data: dict):
        """
        Event: CMD_SYNTAX

        :param data: event data dict
        """
        for option in self.allowed_cmds:
            if self.has_cmd(option):
                data['cmd'].append(self.get_cmd(option))  # append command

    def cmd(self, ctx: CtxItem, cmds: list):
        """
        Event: CMD_EXECUTE

        :param ctx: CtxItem
        :param cmds: commands dict
        """
        from .worker import Worker

        is_cmd = False
        my_commands = []
        for item in cmds:
            if item["cmd"] in self.allowed_cmds:
                my_commands.append(item)
                is_cmd = True

        if not is_cmd:
            return

        # set state: busy
        self.cmd_prepare(ctx, my_commands)

        try:
            worker = Worker()
            worker.from_defaults(self)
            worker.cmds = my_commands
            worker.ctx = ctx

            if not self.is_async(ctx):
                worker.run()
                return
            worker.run_async()

        except Exception as e:
            self.error(e)
