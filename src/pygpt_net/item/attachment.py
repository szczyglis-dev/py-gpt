#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.05 18:00:00                  #
# ================================================== #

import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass(slots=True)
class AttachmentItem:

    TYPE_FILE = 'file'
    TYPE_URL = 'url'

    name: Optional[str] = None
    id: Optional[str] = None
    uuid: Optional[str] = None
    path: Optional[str] = None
    remote: Optional[str] = None
    vector_store_ids: list = field(default_factory=list)
    meta_id: Optional[int] = None
    ctx: bool = False
    consumed: bool = False
    size: int = 0
    send: bool = False
    type: str = TYPE_FILE
    extra: dict = field(default_factory=dict)

    def serialize(self) -> dict:
        """
        Serialize item to dict

        :return: serialized item
        """
        return {
            'id': self.id,
            'uuid': str(self.uuid),
            'name': self.name,
            'path': self.path,
            'size': self.size,
            'remote': self.remote,
            'ctx': self.ctx,
            'vector_store_ids': self.vector_store_ids,
            'type': self.type,
            'extra': self.extra,
            'meta_id': self.meta_id,
            'send': self.send
        }

    def deserialize(self, data: dict):
        """
        Deserialize item from dict

        :param data: serialized item
        """
        if 'id' in data:
            self.id = data['id']
        if 'uuid' in data:
            self.uuid = data['uuid']
        if 'name' in data:
            self.name = data['name']
        if 'path' in data:
            self.path = data['path']
        if 'size' in data:
            self.size = data['size']
        if 'remote' in data:
            self.remote = data['remote']
        elif 'remote_id' in data:
            self.remote = data['remote_id']
        if 'ctx' in data:
            self.ctx = data['ctx']
        if 'vector_store_ids' in data:
            self.vector_store_ids = data['vector_store_ids']
        if 'type' in data:
            self.type = data['type']
        if 'extra' in data:
            self.extra = data['extra']
        if 'meta_id' in data:
            self.meta_id = data['meta_id']
        if 'send' in data:
            self.send = data['send']

    def dump(self) -> str:
        """
        Dump item to string

        :return: serialized item
        """
        try:
            return json.dumps(self.serialize())
        except Exception as e:
            pass
        return ""

    def __str__(self):
        """To string"""
        return self.dump()