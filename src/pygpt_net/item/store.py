#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.01.02 20:00:00                  #
# ================================================== #

import json
import time
from dataclasses import dataclass, field
from typing import Optional

from pygpt_net.item.attachment import AttachmentItem


@dataclass(slots=True)
class RemoteStoreItem:
    id: Optional[object] = None
    record_id: Optional[object] = None
    uuid: Optional[object] = None
    name: Optional[object] = None
    provider: Optional[object] = None
    description: Optional[object] = None
    status: dict = field(default_factory=dict)
    last_status: str = ""
    expire_days: int = 0
    usage_bytes: int = 0
    bytes: int = 0
    num_files: int = 0
    is_thread: bool = False
    created: int = 0
    updated: int = 0
    last_active: int = 0
    last_sync: int = 0
    file_ids: list = field(default_factory=list)

    def __init__(self):
        """Assistant vector store item"""
        self.id = None
        self.record_id = None
        self.uuid = None
        self.name = None
        self.provider = None
        self.description = None
        self.status = {}
        self.last_status = ""
        self.expire_days = 0
        self.usage_bytes = 0
        self.bytes = 0
        self.num_files = 0
        self.is_thread = False
        self.created = int(time.time())
        self.updated = int(time.time())
        self.last_active = int(time.time())
        self.last_sync = int(time.time())

    def reset(self):
        """Reset store"""
        self.id = None
        self.record_id = None
        self.uuid = None
        self.name = None
        self.provider = None
        self.description = None
        self.status = {}
        self.last_status = ""
        self.expire_days = 0
        self.usage_bytes = 0
        self.num_files = 0
        self.bytes = 0
        self.is_thread = False
        self.last_active = int(time.time())
        self.last_sync = int(time.time())

    def to_dict(self) -> dict:
        """
        Return as dictionary

        :return: dictionary
        """
        return {
            "id": self.id,
            "uuid": self.uuid,
            "name": self.name,
            "provider": self.provider,
            "description": self.description,
            "last_status": self.last_status,
            "expire_days": self.expire_days,
            "usage_bytes": self.usage_bytes,
            "num_files": self.num_files,
            "status": self.status,
            "is_thread": self.is_thread,
        }

    def from_dict(self, data: dict):
        """
        Load from dictionary

        :param data: dictionary
        """
        self.id = data.get('id', None)
        self.name = data.get('name', None)
        self.provider = data.get('provider', None)
        self.uuid = data.get('uuid', None)
        self.expire_days = data.get('expire_days', 0)
        self.status = data.get('status', {})

    def get_file_count(self):
        """
        Return number of files in store

        :return: number of files
        """
        num = self.num_files
        if self.status and isinstance(self.status, dict) and 'file_counts' in self.status:
            if 'completed' in self.status['file_counts']:
                num = int(self.status['file_counts']['completed'] or 0)
        return num

    def dump(self) -> str:
        """
        Dump item to string

        :return: serialized item
        """
        try:
            return json.dumps(self.to_dict())
        except Exception as e:
            pass
        return ""

    def __str__(self):
        """To string"""
        return self.dump()


@dataclass(slots=True)
class RemoteFileItem:
    id: Optional[object] = None
    record_id: Optional[object] = None
    name: Optional[object] = None
    provider: Optional[object] = None
    path: Optional[object] = None
    file_id: Optional[object] = None
    store_id: Optional[object] = None
    thread_id: Optional[object] = None
    uuid: Optional[object] = None
    size: int = 0
    created: int = 0
    updated: int = 0

    def __init__(self):
        """Assistant file item"""
        self.id = None
        self.record_id = None
        self.name = None
        self.provider = None
        self.path = None
        self.file_id = None
        self.store_id = None
        self.thread_id = None
        self.uuid = None
        self.size = 0
        self.created = 0
        self.updated = 0

    def reset(self):
        """Reset store"""
        self.id = None
        self.record_id = None
        self.name = None
        self.provider = None
        self.path = None
        self.file_id = None
        self.store_id = None
        self.thread_id = None
        self.uuid = None
        self.size = 0
        self.created = 0
        self.updated = 0

    def to_dict(self) -> dict:
        """
        Return as dictionary

        :return: dictionary
        """
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "path": self.path,
            "file_id": self.file_id,
            "store_id": self.store_id,
            "thread_id": self.thread_id,
            "uuid": self.uuid,
            "size": self.size,
            "created": self.created,
            "updated": self.updated,
        }

    def from_dict(self, data: dict):
        """
        Load from dictionary

        :param data: dictionary
        """
        self.id = data.get('id', None)
        self.name = data.get('name', None)
        self.provider = data.get('provider', None)
        self.path = data.get('path', None)
        self.file_id = data.get('file_id', None)
        self.store_id = data.get('store_id', None)
        self.thread_id = data.get('thread_id', None)
        self.uuid = data.get('uuid', None)
        self.size = data.get('size', 0)
        self.created = data.get('created', 0)
        self.updated = data.get('updated', 0)

    def dump(self) -> str:
        """
        Dump item to string

        :return: serialized item
        """
        try:
            return json.dumps(self.to_dict())
        except Exception as e:
            pass
        return ""

    def __str__(self):
        """To string"""
        return self.dump()