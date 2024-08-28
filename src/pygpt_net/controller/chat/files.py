#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.08.28 16:00:00                  #
# ================================================== #

from pygpt_net.item.ctx import CtxItem
from pygpt_net.utils import trans


class Files:
    def __init__(self, window=None):
        """
        Chat files/attachments controller

        :param window: Window instance
        """
        self.window = window

    def send(self, mode: str, ctx: CtxItem):
        """
        Send attachments

        :param mode: mode
        :param ctx: CtxItem instance
        """
        # upload assistant attachments (only assistant mode here)
        attachments = self.upload(mode)  # current thread is already in global config
        if len(attachments) > 0:
            ctx.attachments = attachments
            self.window.ui.status(trans('status.sending'))
            self.window.controller.chat.text.log("Uploaded attachments (Assistant): {}".format(len(attachments)))
        return attachments

    def upload(self, mode: str) -> dict:
        """
        Upload attachments

        :param mode: mode
        :return: uploaded attachments list
        """
        attachments_list = {}

        if mode == 'assistant':
            is_upload = False
            num_uploaded = 0
            try:
                # upload only new attachments (not uploaded yet to remote)
                attachments = self.window.core.attachments.get_all(mode)
                c = self.window.controller.assistant.files.count_upload(attachments)
                if c > 0:
                    is_upload = True
                    self.window.ui.status(trans('status.uploading'))
                    num_uploaded = self.window.controller.assistant.files.upload(
                        mode,
                        attachments,
                    )
                    self.window.controller.files.uploaded_ids = self.window.core.attachments.get_ids(mode)
                    attachments_list = self.window.core.attachments.make_json_list(attachments)

                # show uploaded status
                if is_upload and num_uploaded > 0:
                    self.window.ui.status(trans('status.uploaded'))

            except Exception as e:
                self.window.core.debug.log(e)
                self.window.ui.dialogs.alert(e)

        return attachments_list
