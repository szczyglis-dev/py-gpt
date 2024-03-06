#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.06 22:00:00                  #
# ================================================== #

class Confirm:
    def __init__(self, window=None):
        """
        Confirmation dialogs controller

        :param window: Window instance
        """
        self.window = window

    def accept(self, type: str, id: any = None, parent_object=None):
        """
        Confirm dialog accept

        :param type: dialog type
        :param id: dialog object id
        :param parent_object: dialog parent object
        """
        self.window.ui.dialog['confirm'].close()

        # app
        if type == 'app.log.clear':
            self.window.ui.dialogs.app_log.clear(force=True)

        # presets
        elif type == 'preset_exists':
            self.window.controller.presets.editor.save(True)
        elif type == 'preset_delete':
            self.window.controller.presets.delete(id, True)
        elif type == 'preset_clear':
            self.window.controller.presets.clear(True)
        elif type == 'preset_restore':
            self.window.controller.presets.restore(True)

        # ctx
        elif type == 'ctx.delete':
            self.window.controller.ctx.delete(id, True)
        elif type == 'ctx.delete_all':
            self.window.controller.ctx.delete_history(True)
        elif type == 'ctx.delete_item':
            self.window.controller.ctx.delete_item(id, True)

        # images
        elif type == 'img_delete':
            self.window.controller.chat.image.delete(id, True)

        # agent infinity loop run
        elif type == 'agent.infinity.run':
            self.window.controller.chat.input.send_input(force=True)

        # db viewer
        elif type == 'db.delete_row':
            try:
                self.window.core.db.viewer.delete_row(data=id)  # dict: {table, row_id}
            except Exception as e:
                self.window.core.debug.error(e)
                self.window.ui.dialogs.alert(str(e))
        elif type == 'db.update_row':
            try:
                self.window.core.db.viewer.update_row(data=id)  # dict: {table, id, field, value}
            except Exception as e:
                self.window.core.debug.error(e)
                self.window.ui.dialogs.alert(str(e))
        elif type == 'db.delete_all':
            try:
                self.window.core.db.viewer.truncate_table(data=id)  # dict: {table}
            except Exception as e:
                self.window.core.debug.error(e)
                self.window.ui.dialogs.alert(str(e))
        elif type == 'db.truncate_table':
            try:
                self.window.core.db.viewer.truncate_table(data=id, reset=True)  # dict: {table}
            except Exception as e:
                self.window.core.debug.error(e)
                self.window.ui.dialogs.alert(str(e))

        # attachments
        elif type == 'attachments.delete':
            self.window.controller.attachment.delete(id, force=True, remove_local=True)
        elif type == 'attachments_uploaded.clear':
            self.window.controller.assistant.files.clear_files(True)
        elif type == 'attachments_uploaded.delete':
            self.window.controller.assistant.files.delete(id, True)
        elif type == 'attachments.clear':
            self.window.controller.attachment.clear(force=True, remove_local=True)

        # files
        elif type == 'files.delete':
            self.window.controller.files.delete(id, True)
        elif type == 'files.delete.recursive':
            self.window.controller.files.delete_recursive(id, True)

        # assistants
        elif type == 'assistant_delete':
            self.window.controller.assistant.delete(id, True)
        elif type == 'assistant_import':
            self.window.controller.assistant.import_api(True)
        elif type == 'assistant_import_files':
            self.window.controller.assistant.files.sync(True)

        # settings
        elif type == 'settings.defaults.user':
            self.window.controller.settings.editor.load_defaults_user(True)
        elif type == 'settings.defaults.app':
            self.window.controller.settings.editor.load_defaults_app(True)
        elif type == 'settings.dict.delete':
            self.window.controller.config.dictionary.delete_item(parent_object, id, True)

        # plugins
        elif type == 'plugin.settings.defaults.user':
            self.window.controller.plugins.settings.load_defaults_user(True)
        elif type == 'plugin.settings.defaults.app':
            self.window.controller.plugins.settings.load_defaults_app(True)

        # plugins presets
        elif type == 'plugin.presets.delete':
            self.window.controller.plugins.presets.delete_by_idx(id, True)
        elif type == 'plugin.presets.reset':
            self.window.controller.plugins.presets.reset_by_idx(id, True)

        # models
        elif type == 'models.editor.delete':
            self.window.controller.model.editor.delete_by_idx(id, True)
        elif type == 'models.editor.defaults.user':
            self.window.controller.model.editor.load_defaults_user(True)
        elif type == 'models.editor.defaults.app':
            self.window.controller.model.editor.load_defaults_app(True)

        # index
        elif type == 'idx.index.file':
            self.window.controller.idx.indexer.index_file_confirm(id)  # id = path
        elif type == 'idx.index.files.all':
            self.window.controller.idx.indexer.index_all_files(id, True)
        elif type == 'idx.index.file.remove':
            self.window.controller.idx.indexer.index_file_remove_confirm(id)  # id = path
        elif type == 'idx.index.ctx.remove':
            self.window.controller.idx.indexer.index_ctx_meta_remove(idx="", meta_id=id, force=True)  # id = ctx meta id
        elif type == 'idx.index.db':
            self.window.controller.idx.indexer.index_ctx_meta_confirm(id)  # id = ctx_id
        elif type == 'idx.index.db.all':
            self.window.controller.idx.indexer.index_ctx_from_ts_confirm(id)
        elif type == 'idx.clear':
            self.window.controller.idx.indexer.clear(id, True)
        elif type == 'idx.truncate':
            self.window.controller.idx.indexer.truncate(id, True)

    def dismiss(self, type: str, id: any):
        """
        Confirm dialog dismiss

        :param type: dialog type
        :param id: dialog object id
        """
        self.window.ui.dialog['confirm'].close()

    def accept_rename(self, type: str, id: any, name: str):
        """
        Update name of object

        :param type: dialog type
        :param id: dialog object id
        :param name: new name
        """
        if type == 'ctx':
            self.window.controller.ctx.update_name(id, name)
        elif type == 'attachment':
            self.window.controller.attachment.update_name(id, name)
        elif type == 'attachment_uploaded':
            self.window.controller.assistant.files.update_name(id, name)
        elif type == 'output_file':
            self.window.controller.files.update_name(id, name)
        elif type == 'notepad':
            self.window.controller.notepad.update_name(id, name, True)
        elif type == 'plugin.preset':
            self.window.controller.plugins.presets.update_name(id, name)

    def accept_create(self, type: str, id: any, name: str):
        """
        Create new object

        :param type: dialog type
        :param id: dialog object id
        :param name: name
        """
        if type == 'mkdir':
            self.window.controller.files.make_dir(id, name)
        if type == 'touch':
            self.window.controller.files.touch_file(id, name, True)
        elif type == 'duplicate':
            self.window.controller.files.duplicate_local(id, name, True)
        elif type == 'plugin.preset':
            self.window.controller.plugins.presets.create(id, name)

    def dismiss_rename(self):
        """Dismiss rename dialog"""
        self.window.ui.dialog['rename'].close()

    def dismiss_create(self):
        """Dismiss create dialog"""
        self.window.ui.dialog['create'].close()
