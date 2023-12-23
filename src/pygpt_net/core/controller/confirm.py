#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.17 22:00:00                  #
# ================================================== #

class Confirm:
    def __init__(self, window=None):
        """
        Confirm dialog controller

        :param window: Window instance
        """
        self.window = window

    def accept(self, type, id=None, parent_object=None):
        """
        Confirm dialog accept

        :param type: dialog type
        :param id: dialog object id
        :param parent_object: dialog parent object
        """
        if type == 'preset_exists':
            self.window.controller.presets.save(True)
        elif type == 'preset_delete':
            self.window.controller.presets.delete(id, True)
        elif type == 'preset_clear':
            self.window.controller.presets.clear(True)
        elif type == 'ctx_delete':
            self.window.controller.ctx.delete(id, True)
        elif type == 'ctx_delete_all':
            self.window.controller.ctx.delete_history(True)
        elif type == 'img_delete':
            self.window.controller.image.img_action_delete(id, True)
        elif type == 'attachments.delete':
            self.window.controller.attachment.delete(id, True)
        elif type == 'attachments_uploaded.delete':
            self.window.controller.assistant_files.delete_file(id, True)
        elif type == 'attachments.clear':
            self.window.controller.attachment.clear(True)
        elif type == 'attachments_uploaded.clear':
            self.window.controller.assistant_files.clear_files(True)
        elif type == 'files.delete':
            self.window.controller.files.delete(id, True)
        elif type == 'assistant_delete':
            self.window.controller.assistant.delete(id, True)
        elif type == 'assistant_import':
            self.window.controller.assistant.import_assistants(True)
        elif type == 'assistant_import_files':
            self.window.controller.assistant_files.sync_files(True)
        elif type == 'settings.defaults.user':
            self.window.controller.settings.load_defaults_user(True)
        elif type == 'settings.defaults.app':
            self.window.controller.settings.load_defaults_app(True)
        elif type == 'settings.dict.delete':
            self.window.controller.settings.delete_item(parent_object, id, True)
        elif type == 'plugin.settings.defaults.user':
            self.window.controller.plugins.load_defaults_user(True)
        elif type == 'plugin.settings.defaults.app':
            self.window.controller.plugins.load_defaults_app(True)

        self.window.ui.dialog['confirm'].close()

    def dismiss(self, type, id):
        """
        Confirm dialog dismiss

        :param type: dialog type
        :param id: dialog object id
        """
        self.window.ui.dialog['confirm'].close()

    def accept_rename(self, type, id, name):
        """
        Update name of object
        """
        if type == 'ctx':
            self.window.controller.ctx.update_name(id, name)
        elif type == 'attachment':
            self.window.controller.attachment.update_name(id, name)
        elif type == 'attachment_uploaded':
            self.window.controller.assistant_files.update_file_name(id, name)
        elif type == 'output_file':
            self.window.controller.files.update_name(id, name)

    def dismiss_rename(self):
        """Dismiss rename dialog"""
        self.window.ui.dialog['rename'].close()
