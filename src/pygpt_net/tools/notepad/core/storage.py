#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #
"""Notepad repository using the existing SQLite schema and profile database."""
import uuid
from types import SimpleNamespace

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.item.notepad import NotepadItem
from pygpt_net.provider.core.notepad.db_sqlite import DbSqliteProvider
from pygpt_net.provider.core.notepad.db_sqlite.storage import Storage as SqlStorage
from pygpt_net.utils import trans

class Storage:
    def __init__(self, tool):
        self.tool = tool
        self.items = {}
        self.provider = None
        self._database = None
        self._loaded = False

    def attach(self):
        self.provider = DbSqliteProvider(self.tool.window)

    def install(self):
        self.provider.install()

    def patch(self, version):
        return self.provider.patch(version)

    def ensure_loaded(self):
        database = self.tool.window.core.db.get_db()
        if not self._loaded or database is not self._database:
            self.items = self.provider.load_all()
            self._database = database
            self._loaded = True
        return self.items

    def reset(self):
        self.items = {}
        self._loaded = False

    def get_by_id(self, idx):
        return self.ensure_loaded().get(idx)

    def get_all(self):
        return self.ensure_loaded()

    def allocate(self, idx=None):
        items = self.ensure_loaded()
        if idx is None:
            # IDs are persistent note slots, not an ever-growing creation counter.
            # Reopening a free slot restores its saved document from the database.
            idx = 1
            while idx in self.tool.documents.opened:
                idx += 1
        item = items.get(idx)
        if item is None:
            item = NotepadItem()
            item.idx = idx
            items[idx] = item
        return item

    def writer(self):
        """Bind a writer to the owning profile, even when global DB switches later."""
        database = self.tool.window.core.db.get_db()
        window = SimpleNamespace(core=SimpleNamespace(db=SimpleNamespace(get_db=lambda: database)))
        return SqlStorage(window)

    def import_from_db(self):
        return {idx: dict(uuid=uuid.uuid4(), pid=0, idx=idx, type=Tab.TAB_TOOL,
                          tool_id='notepad', data_id=idx,
                          title=item.title or trans('output.tab.notepad'))
                for idx, item in self.ensure_loaded().items()}
