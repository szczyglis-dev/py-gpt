#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.16 01:00:00                  #
# ================================================== #

import copy
from typing import Optional, List, Dict

from packaging.version import Version

from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxMeta
from pygpt_net.provider.core.attachment.json_file import JsonFileProvider

from .context import Context


class Attachments:
    def __init__(self, window=None):
        """
        Attachments core

        :param window: Window instance
        """
        self.window = window
        self.provider = JsonFileProvider(window)
        self.context = Context(window)
        self.items = {}
        self.current = None

    def install(self):
        """Install provider data"""
        self.provider.install()

    def patch(self, app_version: Version) -> bool:
        """
        Patch provider data

        :param app_version: app version
        :return: True if data was patched
        """
        return self.provider.patch(app_version)

    def select(self, mode: str, id: str):
        """
        Select attachment by uuid

        :param mode: mode
        :param id: id
        """
        if mode not in self.items:
            self.items[mode] = {}

        if id in self.items[mode]:
            self.current = id

    def count(self, mode: str) -> int:
        """
        Count attachments in mode

        :param mode: mode
        :return: attachments count
        """
        if mode not in self.items:
            self.items[mode] = {}

        return len(self.items[mode])

    def get_ids(self, mode: str) -> list:
        """
        Get items IDs in mode

        :param mode: mode
        :return: items UUIDs
        """
        if mode not in self.items:
            self.items[mode] = {}

        return list(self.items[mode].keys())

    def get_id_by_idx(self, mode: str, idx: int) -> Optional[str]:
        """
        Get ID by index in mode

        :param mode: mode
        :param idx: index
        :return: file ID
        """
        i = 0
        for id in self.get_ids(mode):
            if i == idx:
                return id
            i += 1

    def get_by_id(self, mode: str, id: str) -> Optional[AttachmentItem]:
        """
        Return attachment by ID in mode

        :param mode: mode
        :param id: file id
        :return: AttachmentItem
        """
        if mode not in self.items:
            self.items[mode] = {}

        if id in self.items[mode]:
            return self.items[mode][id]

    def get_by_idx(self, mode: str, idx: int) -> Optional[AttachmentItem]:
        """
        Return item by index in mode

        :param mode: mode
        :param idx: item index
        :return: AttachmentItem or None
        """
        id = self.get_id_by_idx(mode, idx)
        if id is not None:
            return self.items[mode][id]

    def get_all(
            self,
            mode: str,
            only_files: bool = True
    ) -> dict:
        """
        Return all items in mode

        :param mode: mode
        :param only_files: only files
        :return: attachments items dict
        """
        if mode not in self.items:
            self.items[mode] = {}

        current = self.items[mode]
        if not only_files:
            additional = self.get_from_meta_ctx(mode, self.window.core.ctx.get_current_meta())
            for attachment in additional:
                current[attachment.id] = attachment
        return current

    def get_from_meta_ctx(
            self,
            mode: str,
            meta: CtxMeta
    ) -> List[AttachmentItem]:
        """
        Get attachments from meta context

        :param mode: mode
        :param meta: meta context
        :return: attachments
        """
        if meta is None:
            return []
        attachments = []
        for attachment in meta.get_additional_ctx():
            item = AttachmentItem()
            if 'uuid' not in attachment:
                continue
            item.id = attachment['uuid']
            if 'name' in attachment:
                item.name = attachment['name']
            else:
                item.name = 'No name'
            if 'path' in attachment:
                item.path = attachment['path']
            else:
                item.path = '-'
            item.ctx = True
            item.meta_id = meta.id
            attachments.append(item)
        return attachments


    def new(
            self,
            mode: str,
            name: Optional[str] = None,
            path: Optional[str] = None,
            auto_save: bool = True,
            type: str = AttachmentItem.TYPE_FILE,
            extra: Optional[dict] = None
    ) -> AttachmentItem:
        """
        Create new attachment

        :param mode: mode
        :param name: name
        :param path: path
        :param auto_save: auto_save
        :param type: type
        :param extra: extra data
        :return: AttachmentItem
        """
        # make local copy of external attachment if enabled
        if type == AttachmentItem.TYPE_FILE and path is not None:
            if self.window.core.config.get("upload.store"):
                if not self.window.core.filesystem.in_work_dir(path):
                    path = self.window.core.filesystem.store_upload(path)

        attachment = self.create()
        attachment.name = name
        attachment.path = path
        attachment.type = type

        if extra is not None:
            attachment.extra = extra

        if mode not in self.items:
            self.items[mode] = {}

        self.items[mode][attachment.id] = attachment
        self.current = attachment.id

        if auto_save:
            self.save()

        return attachment

    def build(self) -> AttachmentItem:
        """
        Build attachment

        :return: AttachmentItem
        """
        attachment = AttachmentItem()
        attachment.name = None
        attachment.path = None
        return attachment

    def create(self) -> AttachmentItem:
        """
        Create attachment item

        :return: AttachmentItem
        """
        attachment = self.build()
        id = self.provider.create(attachment)
        attachment.id = id
        return attachment

    def add(
            self,
            mode: str,
            item: AttachmentItem
    ):
        """
        Add item to attachments

        :param mode: mode
        :param item: item to add to attachments
        """
        if mode not in self.items:
            self.items[mode] = {}

        id = item.id
        self.items[mode][id] = item  # add item to attachments

        # save attachments
        self.save()

    def has(self, mode: str) -> bool:
        """
        Check id mode has attachments

        :param mode: mode
        :return: True if exists
        """
        if mode not in self.items:
            self.items[mode] = {}

        return len(self.items[mode]) > 0

    def delete(
            self,
            mode: str,
            id: str,
            remove_local: bool = False
    ):
        """
        Delete attachment by file_id

        :param mode: mode
        :param id: file id
        :param remove_local: remove local copy
        """
        if mode not in self.items:
            self.items[mode] = {}

        if id in self.items[mode]:
            if remove_local:
                self.window.core.filesystem.remove_upload(
                    self.items[mode][id].path,
                )
            del self.items[mode][id]
            self.save()

    def delete_all(
            self,
            mode: str,
            remove_local: bool = False,
            auto: bool = False,
            force: bool = False
    ):
        """
        Delete all attachments

        :param mode: mode
        :param remove_local: remove local copy
        :param auto: auto delete
        :param force: force delete
        """
        if mode not in self.items:
            self.items[mode] = {}

        for id in list(self.items[mode].keys()):
            if (not self.items[mode][id].consumed and auto) and not force:
                continue
            if remove_local:
                self.window.core.filesystem.remove_upload(
                    self.items[mode][id].path,
                )
            del self.items[mode][id]
            self.save()

    def clear(
            self,
            mode: str,
            remove_local: bool = False
    ):
        """
        Clear all attachments in mode

        :param mode: mode
        :param remove_local: remove local copy
        """
        if mode not in self.items:
            self.items[mode] = {}
        if remove_local:
            for id in self.items[mode]:
                self.window.core.filesystem.remove_upload(
                    self.items[mode][id].path,
                )
        self.items[mode] = {}

    def clear_all(self):
        """Clear all attachments"""
        self.items = {}

    def replace_id(
            self,
            mode: str,
            tmp_id: str,
            attachment: AttachmentItem
    ):
        """
        Replace temporary id with real one

        :param mode: mode
        :param tmp_id: temporary id
        :param attachment: attachment
        """
        if mode not in self.items:
            self.items[mode] = {}

        if tmp_id in self.items[mode]:
            self.items[mode][attachment.id] = self.items[mode][tmp_id]
            del self.items[mode][tmp_id]
            self.save()

    def rename_file(self, mode: str, id: str, name: str):
        """
        Update name

        :param mode: mode
        :param id: file id
        :param name: new name
        """
        data = self.get_by_id(mode, id)
        data.name = name
        self.save()

    def make_json_list(
            self,
            attachments: Dict[str, AttachmentItem]
    ) -> Dict[str, dict]:
        """
        Make json list

        :param attachments: attachments
        :return: json list
        """
        result = {}
        for id in attachments:
            attachment = attachments[id]
            result[id] = {
                'name': attachment.name,
                'path': attachment.path,
            }
        return result

    def from_files(
            self,
            mode: str,
            files: Dict[str, dict]
    ):
        """
        Load current from assistant files

        :param mode: mode
        :param files: files dict
        """
        self.clear(mode)
        for id in files:
            file = files[id]
            item = AttachmentItem()
            item.name = id

            if 'name' in file \
                    and file['name'] is not None and file['name'] != "":
                item.name = file['name']
            if 'path' in file \
                    and file['path'] is not None and file['path'] != "":
                item.path = file['path']

            item.id = id
            item.remote = id
            item.send = True
            self.add(mode, item)

    def from_attachments(
            self,
            mode: str,
            attachments: Dict[str, AttachmentItem]
    ):
        """
        Load current from attachments

        :param mode: mode
        :param attachments: attachments
        """
        self.clear(mode)
        for id in attachments:
            attachment = attachments[id]
            self.add(mode, attachment)

    def load(self):
        """Load attachments"""
        self.items = self.provider.load()
        # replace workdir placeholder with current workdir
        for mode in self.items:
            for id in self.items[mode]:
                attachment = self.items[mode][id]
                if attachment.path is not None and attachment.type == AttachmentItem.TYPE_FILE:
                    attachment.path = self.window.core.filesystem.to_workdir(
                        attachment.path,
                    )

    def save(self):
        """Save attachments"""
        # replace current workdir with placeholder
        data = copy.deepcopy(self.items)  # copy to avoid changing original data
        for mode in data:
            for id in data[mode]:
                attachment = data[mode][id]
                if attachment.path is not None and attachment.type == AttachmentItem.TYPE_FILE:
                    attachment.path = self.window.core.filesystem.make_local(
                        attachment.path,
                    )
        self.provider.save(data)
