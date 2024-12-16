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

import os
from typing import List, Dict, Any

from PySide6.QtCore import Slot, QObject

from pygpt_net.core.types import (
    MODE_ASSISTANT,
)
from pygpt_net.core.events import KernelEvent
from pygpt_net.core.bridge import BridgeContext
from pygpt_net.core.attachments.worker import AttachmentWorker
from pygpt_net.item.attachment import AttachmentItem
from pygpt_net.item.ctx import CtxMeta, CtxItem
from pygpt_net.utils import trans


class Attachment(QObject):

    MODE_FULL_CONTEXT = 'full'  # attach full context to system prompt
    MODE_QUERY_CONTEXT = 'query'  # query context only
    MODE_QUERY_CONTEXT_SUMMARY = 'summary'  # summary full context and attach summary to system prompt
    MODE_DISABLED = 'disabled'  # disabled

    def __init__(self, window=None):
        """
        Attachment controller

        :param window: Window instance
        """
        super(Attachment, self).__init__()
        self.window = window
        self.mode = self.MODE_FULL_CONTEXT
        self.uploaded = False
        self.uploaded_tab_idx = 3

    def has(self, mode: str) -> bool:
        """
        Check if has attachments

        :param mode: Work mode
        :return: True if has attachments
        """
        if self.window.core.attachments.has(mode):
            files = self.window.core.attachments.get_all(mode, only_files=True)
            for id in files:
                file = files[id]
                if self.is_allowed(file.path):
                    return True
        return False

    def setup(self):
        """Setup attachments"""
        self.mode = self.window.core.config.get("ctx.attachment.mode", self.MODE_FULL_CONTEXT)
        if self.mode == self.MODE_QUERY_CONTEXT:
            self.window.ui.nodes['input.attachments.ctx.mode.query'].setChecked(True)
        elif self.mode == self.MODE_QUERY_CONTEXT_SUMMARY:
            self.window.ui.nodes['input.attachments.ctx.mode.query_summary'].setChecked(True)
        elif self.mode == self.MODE_FULL_CONTEXT:
            self.window.ui.nodes['input.attachments.ctx.mode.full'].setChecked(True)
        elif self.mode == self.MODE_DISABLED:
            self.window.ui.nodes['input.attachments.ctx.mode.off'].setChecked(True)

    def reload(self):
        """Reload attachments"""
        self.setup()

    def handle(
            self,
            mode: str,
            text: str
    ):
        """
        Handle attachment upload

        :param mode: mode
        :param text: input prompt text
        """
        worker = AttachmentWorker(self.window)
        worker.window = self.window
        worker.meta = self.window.core.ctx.get_current_meta()
        worker.mode = mode
        worker.prompt = text
        worker.signals.error.connect(self.handle_upload_error)
        worker.signals.success.connect(self.handle_upload_success)
        self.window.threadpool.start(worker)

    def is_allowed(self, path: str) -> bool:
        """
        Check if path is allowed for indexing

        :param path: Path to file
        :return: True if allowed
        """
        allow_images = self.window.core.config.get("ctx.attachment.img", False)
        ext_allowed = self.window.core.idx.indexing.is_allowed(path)
        if ext_allowed or self.window.core.filesystem.packer.is_archive(path):
            if not self.window.core.filesystem.types.is_image(path) or allow_images:
                return True
        return False

    def upload(
            self,
            meta: CtxMeta,
            mode: str,
            prompt: str
    ) -> bool:
        """
        Upload attachments for meta

        :param meta: CtxMeta
        :param mode: str
        :param prompt: user input prompt
        :return: True if uploaded
        """
        self.uploaded = False
        auto_index = self.window.core.config.get("attachments_auto_index", False)
        attachments = self.window.core.attachments.get_all(mode, only_files=True)

        if self.is_verbose() and len(attachments) > 0:
            print("\nUploading attachments...\nWork Mode: {}".format(mode))

        for uuid in attachments:
            attachment = attachments[uuid]
            if attachment.type == AttachmentItem.TYPE_FILE:
                result = self.upload_file(
                    attachment=attachment,
                    meta=meta,
                    prompt=prompt,
                    auto_index=auto_index,
                )
                if result:
                    self.uploaded = True
            elif attachment.type == AttachmentItem.TYPE_URL:
                result = self.upload_web(
                    attachment=attachment,
                    meta=meta,
                    prompt=prompt,
                    auto_index=auto_index,
                )
                if result:
                    self.uploaded = True
        if self.uploaded:
            self.window.core.ctx.save(meta.id)  # save meta
        return self.uploaded

    def upload_file(
            self,
            attachment: AttachmentItem,
            meta: CtxMeta,
            prompt: str,
            auto_index: bool
    ) -> bool:
        """
        Upload file attachment

        :param attachment: AttachmentItem
        :param meta: CtxMeta
        :param prompt: User input prompt
        :param auto_index: Auto index
        :return: True if uploaded
        """
        uploaded = False
        if not self.is_allowed(attachment.path):
            return False
        if self.window.core.filesystem.packer.is_archive(attachment.path):
            if self.is_verbose():
                print("Unpacking archive: {}".format(attachment.path))
            tmp_path = self.window.core.filesystem.packer.unpack(attachment.path)
            if tmp_path:
                for root, dirs, files in os.walk(tmp_path):
                    for file in files:
                        path = str(os.path.join(root, file))
                        sub_attachment = AttachmentItem()
                        sub_attachment.path = path
                        sub_attachment.name = os.path.basename(path)
                        sub_attachment.consumed = False
                        path_relative = os.path.relpath(path, tmp_path)
                        if self.is_allowed(str(path)):
                            if self.is_verbose():
                                print("Uploading unpacked from archive: {}".format(path_relative))
                            item = self.window.core.attachments.context.upload(
                                meta=meta,
                                attachment=sub_attachment,
                                prompt=prompt,
                                real_path=attachment.path,
                                auto_index=auto_index,
                            )
                            if item:
                                item["path"] = os.path.basename(attachment.path) + "/" + str(path_relative)
                                item["size"] = os.path.getsize(path)
                                self.append_to_meta(meta, item)
                                uploaded = True
                                sub_attachment.consumed = True
                                attachment.consumed = True
                self.window.core.filesystem.packer.remove_tmp(tmp_path)  # clean
        else:
            item = self.window.core.attachments.context.upload(
                meta=meta,
                attachment=attachment,
                prompt=prompt,
                real_path=attachment.path,
                auto_index=auto_index,
            )
            if item:
                self.append_to_meta(meta, item)
                attachment.consumed = True  # allow for deletion
                uploaded = True
        return uploaded

    def append_to_meta(self, meta: CtxMeta, item: Dict[str, Any]):
        """
        Append item to meta

        :param meta: CtxMeta instance
        :param item: Attachment item
        """
        if meta.group:
            if meta.group.additional_ctx is None:
                meta.group.additional_ctx = []
            meta.group.additional_ctx.append(item)
            return
        if meta.additional_ctx is None:
            meta.additional_ctx = []
        meta.additional_ctx.append(item)

    def upload_web(
            self,
            attachment: AttachmentItem,
            meta: CtxMeta,
            prompt: str,
            auto_index: bool
    ) -> bool:
        """
        Upload web attachment

        :param attachment: AttachmentItem
        :param meta: CtxMeta
        :param prompt: User input prompt
        :param auto_index: Auto index
        :return: True if uploaded
        """
        return self.upload_file(attachment, meta, prompt, auto_index)

    def has_context(self, meta: CtxMeta) -> bool:
        """
        Check if has additional context for attachment

        :param meta: CtxMeta
        :return: True if has context
        """
        if meta is None:
            return False
        return meta.has_additional_ctx()

    def current_has_context(self) -> bool:
        """
        Check if current context has additional context from attachments

        :return: True if has context
        """
        meta = self.window.core.ctx.get_current_meta()
        if meta is None:
            return False
        return self.has_context(meta)

    def get_mode(self) -> str:
        """
        Get additional context append mode

        :return: Additional context append mode
        """
        return self.mode

    def get_context(
            self,
            ctx: CtxItem,
            history: List[CtxItem]
    ) -> str:
        """
        Get additional context for attachment

        :param ctx: CtxItem instance
        :param history Context items (history)
        :return: Additional context
        """
        if self.mode != self.MODE_DISABLED:
            if self.is_verbose():
                print("\nPreparing additional context...\nContext Mode: {}".format(self.mode))

        self.window.core.attachments.context.reset()  # reset used files and urls

        # get additional context from attachments
        content = self.window.core.attachments.context.get_context(self.mode, ctx, history)

        # append used files and urls to context
        files = self.window.core.attachments.context.get_used_files()
        urls = self.window.core.attachments.context.get_used_urls()
        if files:
            ctx.files = files
        if urls:
            ctx.urls = urls

        if content:
            if self.is_verbose():
                print("\n--- Using additional context ---\n\n{}".format(content))
            return "====================================\nADDITIONAL CONTEXT FROM ATTACHMENT(s): {}".format(content)
        return ""

    def update(self):
        """Update attachments list"""
        mode = self.window.core.config.get("mode")
        if mode == MODE_ASSISTANT:
            self.hide_uploaded()  # hide uploaded attachments in Assistant mode
            return
        meta = self.window.core.ctx.get_current_meta()
        self.update_list(meta)

    def update_list(self, meta: CtxMeta):
        """
        Update list of attachments

        :param meta: CtxMeta instance
        """
        # update list of attachments
        if meta is None or not meta.has_additional_ctx():
            items = []
        else:
            items = self.window.core.attachments.context.get_all(meta)
        self.window.ui.chat.input.attachments_ctx.update(items)
        self.update_tab(meta)

    def update_tab(self, meta: CtxMeta):
        """
        Update tab label

        :param meta: CtxMeta instance
        """
        if meta is None or not meta.has_additional_ctx():
            num_files = 0
        else:
            num_files = self.window.core.attachments.context.count(meta)
        suffix = ''
        if num_files > 0:
            suffix = f' ({num_files})'
        self.window.ui.tabs['input'].setTabText(
            3,
            trans('attachments_uploaded.tab') + suffix,
        )
        """
        if num_files > 0:
           self.show_uploaded()
        else:
           self.hide_uploaded()
        """

    def is_verbose(self) -> bool:
        """
        Check if verbose mode is enabled

        :return: True if verbose mode is enabled
        """
        return self.window.core.config.get("ctx.attachment.verbose", False)

    def show_uploaded(self):
        """Show uploaded attachments"""
        self.window.ui.tabs['input'].setTabVisible(self.uploaded_tab_idx, True)

    def hide_uploaded(self):
        """Hide uploaded attachments"""
        self.window.ui.tabs['input'].setTabVisible(self.uploaded_tab_idx, False)

    def delete_by_idx(
            self,
            idx: int,
            force: bool = False,
            remove_local: bool = True
    ):
        """
        Delete attachment by index

        :param idx: Index on list
        :param force: Force delete
        :param remove_local: Remove local copies
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='attachments.ctx.delete',
                id=idx,
                msg=trans('attachments.delete.confirm'),
            )
            return
        meta = self.window.core.ctx.get_current_meta()
        if meta is None or not meta.has_additional_ctx():
            return
        items = self.window.core.attachments.context.get_all(meta)
        if idx < len(items):
            item = items[idx]
            self.window.core.attachments.context.delete(meta, item, delete_files=remove_local)
            self.update_list(meta)
            self.window.controller.ctx.update()

    def clear(
            self,
            force: bool = False,
            remove_local: bool = False,
            auto: bool = False
    ):
        """
        Clear attachments list

        :param force: force clear
        :param remove_local: remove local copies
        :param auto: auto clear
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='attachments.ctx.clear',
                id=-1,
                msg=trans('attachments.clear.confirm'),
            )
            return

        meta = self.window.core.ctx.get_current_meta()
        if meta is None or not meta.has_additional_ctx():
            return
        self.window.core.attachments.context.clear(meta, delete_files=remove_local)
        self.update_list(meta)
        self.window.controller.ctx.update()

    def select(self, idx: int):
        """
        Select uploaded file

        :param idx: index of file
        """
        pass

    def open_by_idx(self, idx: int):
        """
        Open attachment by index

        :param idx: Index on list
        """
        meta = self.window.core.ctx.get_current_meta()
        if meta is None or not meta.has_additional_ctx():
            return
        items = self.window.core.attachments.context.get_all(meta)
        if idx < len(items):
            item = items[idx]
            path = item["path"]
            if "real_path" in item:
                path = item["real_path"]
            if os.path.exists(path) and os.path.isfile(path):
                print("Opening attachment: {}".format(path))
                self.window.controller.files.open(path)

    def open_dir_src_by_idx(self, idx: int):
        """
        Open source directory by index

        :param idx: Index on list
        """
        meta = self.window.core.ctx.get_current_meta()
        if meta is None or not meta.has_additional_ctx():
            return
        items = self.window.core.attachments.context.get_all(meta)
        if idx < len(items):
            item = items[idx]
            path = item["path"]
            if "real_path" in item:
                path = item["real_path"]
            dir = os.path.dirname(path)
            if os.path.exists(dir) and os.path.isdir(dir):
                print("Opening source directory: {}".format(dir))
                self.window.controller.files.open(dir)

    def open_dir_dest_by_idx(self, idx: int):
        """
        Open destination directory by index

        :param idx: Index on list
        """
        meta = self.window.core.ctx.get_current_meta()
        if meta is None or not meta.has_additional_ctx():
            return
        items = self.window.core.attachments.context.get_all(meta)
        if idx < len(items):
            item = items[idx]
            root_dir = self.window.core.attachments.context.get_dir(meta)
            dir = os.path.join(root_dir, item["uuid"])
            if os.path.exists(dir) and os.path.isdir(dir):
                self.window.controller.files.open(dir)
                print("Opening destination directory: {}".format(dir))

    def has_file_by_idx(self, idx: int) -> bool:
        """
        Check if has file by index

        :param idx: Index on list
        :return: True if has file
        """
        meta = self.window.core.ctx.get_current_meta()
        if meta is None or not meta.has_additional_ctx():
            return False
        items = self.window.core.attachments.context.get_all(meta)
        if idx < len(items):
            item = items[idx]
            path = item["path"]
            if "real_path" in item:
                path = item["real_path"]
            return os.path.exists(path) and os.path.isfile(path)
        return False

    def has_src_by_idx(self, idx: int) -> bool:
        """
        Check if has source directory by index

        :param idx: Index on list
        :return: True if has source directory
        """
        meta = self.window.core.ctx.get_current_meta()
        if meta is None or not meta.has_additional_ctx():
            return False
        items = self.window.core.attachments.context.get_all(meta)
        if idx < len(items):
            item = items[idx]
            path = item["path"]
            if "real_path" in item:
                path = item["real_path"]
            dir = os.path.dirname(path)
            return os.path.exists(dir) and os.path.isdir(dir)
        return False

    def has_dest_by_idx(self, idx: int) -> bool:
        """
        Check if has destination directory by index

        :param idx: Index on list
        :return: True if has destination directory
        """
        meta = self.window.core.ctx.get_current_meta()
        if meta is None or not meta.has_additional_ctx():
            return False
        items = self.window.core.attachments.context.get_all(meta)
        if idx < len(items):
            item = items[idx]
            root_dir = self.window.core.attachments.context.get_dir(meta)
            dir = os.path.join(root_dir, item["uuid"])
            return os.path.exists(dir) and os.path.isdir(dir)
        return False

    def get_current_tokens(self) -> int:
        """
        Get current tokens

        :return: Current attachments tokens
        """
        if self.mode != self.MODE_FULL_CONTEXT:
            return 0
        meta = self.window.core.ctx.get_current_meta()
        if meta is None:
            return 0
        if not meta.has_additional_ctx():
            return 0
        tokens = 0
        for item in meta.get_additional_ctx():
            if "tokens" in item:
                try:
                    tokens += int(item["tokens"])
                except Exception as e:
                    pass
        return tokens

    @Slot(object)
    def handle_upload_error(self, error: Exception):
        """
        Handle upload error

        :param error: Exception
        """
        self.window.dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
            "id": "chat",
            "msg": "Error reading attachments: {}".format(str(error))
        }))

    @Slot(str)
    def handle_upload_success(self, text: str):
        """
        Handle upload success

        :param text: Input prompt text
        """
        context = BridgeContext()
        context.prompt = text
        event = KernelEvent(KernelEvent.INPUT_USER, {
            'context': context,
            'extra': {},
        })
        self.window.dispatch(event)

    def switch_mode(self, mode: str):
        """
        Switch context mode

        :param mode: context mode
        """
        self.mode = mode
        self.window.core.config.set("ctx.attachment.mode", mode)
        self.window.core.config.save()
        self.window.controller.ui.update_tokens()