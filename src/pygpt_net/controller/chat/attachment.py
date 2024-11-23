#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.11.23 21:00:00                  #
# ================================================== #

import os

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
        self.mode = self.MODE_QUERY_CONTEXT
        self.uploaded = False
        self.archives_allowed = [".zip", ".tar", ".gz", ".bz2"]

    def has(self, mode: str) -> bool:
        """
        Check if has attachments

        :param mode: Work mode
        :return: True if has attachments
        """
        # check if has attachments
        if self.window.core.attachments.has(mode):
            files = self.window.core.attachments.get_all(mode, only_files=True)
            for id in files:
                file = files[id]
                if self.is_allowed(file.path):
                    return True
        return False

    def setup(self):
        """Setup attachments"""
        self.mode = self.window.core.config.get("ctx.attachment.mode", self.MODE_QUERY_CONTEXT)
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

    def handle(self, mode: str, text: str):
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
        worker.signals.error.connect(self.handle_attachment_error)
        worker.signals.success.connect(self.handle_attachment_success)
        self.window.threadpool.start(worker)

    def is_allowed(self, path: str) -> bool:
        """
        Check if path is allowed for indexing

        :param path: Path to file
        :return: True if excluded
        """
        allow_images = self.window.core.config.get("ctx.attachment.img", False)
        allowed = self.window.core.idx.indexing.is_allowed(path)
        if allowed or path.endswith(tuple(self.archives_allowed)):
            if not self.window.core.filesystem.types.is_image(path) or allow_images:
                return True
        return False

    def upload(self, meta: CtxMeta, mode: str, prompt: str) -> bool:
        """
        Upload attachments for meta

        :param meta: CtxMeta
        :param mode: str
        :param prompt: user input prompt
        :return: True if uploaded
        """
        # upload on chat input send, handle to index, etc.
        self.uploaded = False
        attachments = self.window.core.attachments.get_all(mode, only_files=True)
        if self.window.core.config.get("ctx.attachment.verbose", False) and len(attachments) > 0:
            print("Uploading attachments...\nMode: {}".format(mode))
        for uuid in attachments:
            attachment = attachments[uuid]
            if not self.is_allowed(attachment.path):
                continue  # skip not allowed files
            if self.window.core.filesystem.packer.is_archive(attachment.path):
                tmp_path = self.window.core.filesystem.packer.unpack(attachment.path)
                if tmp_path:
                    for root, dirs, files in os.walk(tmp_path):
                        for file in files:
                            path = os.path.join(root, file)
                            sub_attachment = AttachmentItem()
                            sub_attachment.path = path
                            sub_attachment.name = os.path.basename(path)
                            sub_attachment.consumed = False
                            if self.is_allowed(str(path)):
                                item = self.window.core.attachments.context.upload(meta, sub_attachment, prompt)
                                if item:
                                    # prepare relative path to archive root
                                    file_path_relative = os.path.relpath(path, tmp_path)
                                    item["path"] = os.path.basename(attachment.path) + "/" + file_path_relative
                                    item["size"] = os.path.getsize(path)
                                    meta.additional_ctx.append(item)
                                    self.uploaded = True
                                    sub_attachment.consumed = True
                                    attachment.consumed = True
                    self.window.core.filesystem.packer.remove_tmp(tmp_path)  # clean
            else:
                item = self.window.core.attachments.context.upload(meta, attachment, prompt)
                if item:
                    meta.additional_ctx.append(item)
                    attachment.consumed = True  # allow for deletion
                    self.uploaded = True
        if self.uploaded:
            self.window.core.ctx.save(meta.id)  # save meta
        return self.uploaded

    def has_context(self, meta: CtxMeta) -> bool:
        """
        Check if has additional context for attachment

        :param meta: CtxMeta
        :return: True if has context
        """
        # check if has additional context for attachment
        return len(meta.additional_ctx) > 0

    def current_has_context(self) -> bool:
        """
        Check if current context has additional context from attachments

        :return: True if has context
        """
        meta = self.window.core.ctx.get_current_meta()
        return self.has_context(meta)

    def get_mode(self) -> str:
        """
        Get attachment mode

        :return: Attachment mode
        """
        return self.mode

    def get_context(self, ctx: CtxItem) -> str:
        """
        Get additional context for attachment

        :param ctx: CtxItem instance
        :return: Additional context
        """
        content = ""
        meta = ctx.meta
        if self.mode != self.MODE_DISABLED:
            if self.window.core.config.get("ctx.attachment.verbose", False):
                print("Getting additional context...\nMode: {}".format(self.mode))

        if self.mode == self.MODE_FULL_CONTEXT:
            content = self.get_full_context(ctx)
        elif self.mode == self.MODE_QUERY_CONTEXT:
            content = self.get_query_context(meta, str(ctx.input))
        elif self.mode == self.MODE_QUERY_CONTEXT_SUMMARY:
            content = self.get_context_summary(ctx)

        if content:
            if self.window.core.config.get("ctx.attachment.verbose", False):
                print("[OK] Appending additional context: {}".format(content))
            return "====================================\nADDITIONAL CONTEXT FROM ATTACHMENT(s): {}".format(content)
        return ""

    def get_full_context(self, ctx: CtxItem) -> str:
        """
        Get full context for attachment

        :param ctx: CtxItem
        :return: Full context
        """
        return self.window.core.attachments.context.get_context_text(ctx, filename=True)

    def get_query_context(self, meta: CtxMeta, query: str) -> str:
        """
        Get query context for attachment

        :param meta: CtxMeta
        :param query: Query string
        :return: Query context
        """
        return self.window.core.attachments.context.query_context(meta, query)

    def get_context_summary(self, ctx: CtxItem) -> str:
        """
        Get context summary

        :param ctx: CtxItem
        :return: Context summary
        """
        return self.window.core.attachments.context.summary_context(ctx, ctx.input)

    def get_uploaded_attachments(self, meta: CtxMeta):
        """
        Get uploaded attachments for meta

        :param meta: CtxMeta
        """
        # get uploaded attachments for meta
        return meta.additional_ctx

    def update(self):
        """
        Update attachments
        :return:
        """
        # update attachments
        mode = self.window.core.config.get("mode")
        if mode == MODE_ASSISTANT:
            self.hide_uploaded()  # hide uploaded attachments in Assistant mode
            return
        meta = self.window.core.ctx.get_current_meta()
        self.update_list(meta)

    def update_list(self, meta: CtxMeta):
        """
        Update list of attachments
        """
        # update list of attachments
        if meta is None or meta.additional_ctx is None:
            items = []
        else:
            items = self.window.core.attachments.context.get_all(meta)
        self.window.ui.chat.input.attachments_ctx.update(items)
        self.update_tab(meta)

    def update_tab(self, meta: CtxMeta):
        """
        Update tab label

        :param meta: CtxMeta
        """
        if meta is None or meta.additional_ctx is None:
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

    def show_uploaded(self):
        """Show uploaded attachments"""
        self.window.ui.tabs['input'].setTabVisible(3, True)

    def hide_uploaded(self):
        """Hide uploaded attachments"""
        self.window.ui.tabs['input'].setTabVisible(3, False)

    def delete_by_idx(self, idx: int, force: bool = False, remove_local=True):
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
        # delete by index
        meta = self.window.core.ctx.get_current_meta()
        if meta is None or meta.additional_ctx is None:
            return
        items = self.window.core.attachments.context.get_all(meta)
        if idx < len(items):
            item = items[idx]
            self.window.core.attachments.context.delete(meta, item, delete_files=remove_local)
            self.update_list(meta)

    def clear(self, force: bool = False, remove_local=False, auto: bool = False):
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
        if meta is None or meta.additional_ctx is None:
            return
        self.window.core.attachments.context.clear(meta, delete_files=remove_local)
        self.update_list(meta)

    @Slot(object)
    def handle_attachment_error(self, error: Exception):
        """
        Handle attachment error

        :param error: Exception
        """
        self.window.dispatch(KernelEvent(KernelEvent.STATE_ERROR, {
            "id": "chat",
            "msg": "Error reading attachments: {}".format(str(error))
        }))

    @Slot(str)
    def handle_attachment_success(self, text: str):
        """
        Handle attachment success

        :param text: Input prompt text
        """
        # event: handle input
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
        # switch attachment mode
        self.mode = mode
        self.window.core.config.set("ctx.attachment.mode", mode)
        self.window.core.config.save()