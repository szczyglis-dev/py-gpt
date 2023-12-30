#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.30 20:00:00                  #
# ================================================== #

from pygpt_net.utils import trans


class Files:
    def __init__(self, window=None):
        """
        Input controller

        :param window: Window instance
        """
        self.window = window

    def upload(self, mode):
        self.window.core.gpt.assistants.file_ids = []  # clear file ids
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
                    self.window.set_status(trans('status.uploading'))
                    num_uploaded = self.window.controller.assistant.files.upload(mode, attachments)
                    self.window.core.gpt.assistants.file_ids = self.window.core.attachments.get_ids(mode)
                    attachments_list = self.window.core.gpt.attachments.make_json_list(attachments)

                # show uploaded status
                if is_upload and num_uploaded > 0:
                    self.window.set_status(trans('status.uploaded'))

            except Exception as e:
                self.window.core.debug.log(e)
                self.window.ui.dialogs.alert(str(e))

            # create or get current thread, it is required here, TODO: move to separate method
            if self.window.core.config.get('assistant_thread') is None:
                try:
                    self.window.set_status(trans('status.starting'))
                    self.window.core.config.set('assistant_thread',
                                                self.window.controller.assistant.threads.create_thread())
                except Exception as e:
                    self.window.core.debug.log(e)
                    self.window.ui.dialogs.alert(str(e))

        return attachments_list
