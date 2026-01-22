#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.22 16:00:00                  #
# ================================================== #

import json
import time
from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class NotepadItem:
    id: int = 0
    uuid: Optional[object] = None
    idx: int = 0
    title: str = ""
    content: str = ""
    deleted: bool = False
    created: int = 0
    updated: int = 0
    initialized: bool = False
    highlights: Optional[list] = None
    scroll_pos: int = -1

    def __init__(self):
        self.id = 0
        self.uuid = None
        self.idx = 0
        self.title = ""
        self.content = ""
        self.deleted = False
        ts = int(time.time())
        self.created = ts
        self.updated = ts
        self.initialized = False
        self.highlights = []
        self.scroll_pos = -1

    def to_dict(self):
        return {
            'id': self.id,
            'uuid': str(self.uuid),
            'idx': self.idx,
            'title': self.title,
            'content': self.content,
            'deleted': self.deleted,
            'created': self.created,
            'updated': self.updated,
            'initialized': self.initialized,
            'highlights': self.highlights,
            'scroll_pos': self.scroll_pos,
        }

    def dump(self):
        """
        Dump item to string

        :return: serialized item
        :rtype: str
        """
        try:
            return json.dumps(self.to_dict())
        except Exception as e:
            pass
        return ""

    def __str__(self):
        """To string"""
        return self.dump()