#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.12.14 08:00:00                  #
# ================================================== #

from typing import Any, Optional


class Confirm:
    def __init__(self, window=None):
        """
        Confirmation dialogs controller

        :param window: Window instance
        """
        self.window = window

    def accept(
            self,
            type: str,
            id: Optional[str] = None,
            parent_object: Any = None
    ):
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
        elif type == 'ctx.delete_all_groups':
            self.window.controller.ctx.delete_history_groups(True)
        elif type == 'ctx.delete_item':
            self.window.controller.ctx.delete_item(id, True)
        elif type == 'ctx.replay_item':
            self.window.controller.ctx.extra.replay_item(id, True)
        elif type == 'ctx.join_item':
            self.window.controller.ctx.extra.join_item(id, True)
        elif type == 'ctx.group.delete':
            self.window.controller.ctx.delete_group(id, True)  # group delete
        elif type == 'ctx.group.delete.all':
            self.window.controller.ctx.delete_group_all(id, True)  # group delete + items
        elif type == 'ctx.reset_meta':
            self.window.controller.ctx.common.reset(id, True)

        # images
        elif type == 'img_delete':
            self.window.tools.get("viewer").delete(id, True)

        # agent infinity loop run
        elif type == 'agent.infinity.run':
            self.window.controller.chat.input.send_input(force=True)

        # interpreter
        elif type == 'interpreter.clear':
            self.window.tools.get("interpreter").clear(force=True)

        # html canvas
        elif type == 'html_canvas.clear':
            self.window.tools.get("html_canvas").clear(force=True)

        # audio transcribe
        elif type == 'audio.transcribe':
            self.window.tools.get("transcriber").transcribe(id, force=True)
        elif type == 'audio.transcribe.clear':
            self.window.tools.get("transcriber").clear(True)

        # audio cache clear
        elif type == 'audio.cache.clear':
            self.window.controller.audio.clear_cache(True)

        # restore default CSS
        elif type == 'restore.css':
            self.window.controller.layout.restore_default_css(force=True)

        # profiles
        elif type == 'profile.reset':
            self.window.controller.settings.profile.reset_by_idx(id, True)
        elif type == 'profile.delete':
            self.window.controller.settings.profile.delete_by_idx(id, True)
        elif type == 'profile.delete.all':
            self.window.controller.settings.profile.delete_all_by_idx(id, True)

        # db viewer
        elif type == 'db.delete_row':
            try:
                self.window.core.db.viewer.delete_row(data=id)  # dict: {table, row_id}
            except Exception as e:
                self.window.core.debug.error(e)
                self.window.ui.dialogs.alert(e)
        elif type == 'db.update_row':
            try:
                self.window.core.db.viewer.update_row(data=id)  # dict: {table, id, field, value}
            except Exception as e:
                self.window.core.debug.error(e)
                self.window.ui.dialogs.alert(e)
        elif type == 'db.delete_all':
            try:
                self.window.core.db.viewer.truncate_table(data=id)  # dict: {table}
            except Exception as e:
                self.window.core.debug.error(e)
                self.window.ui.dialogs.alert(e)
        elif type == 'db.truncate_table':
            try:
                self.window.core.db.viewer.truncate_table(data=id, reset=True)  # dict: {table}
            except Exception as e:
                self.window.core.debug.error(e)
                self.window.ui.dialogs.alert(e)

        # attachments
        elif type == 'attachments.delete':
            self.window.controller.attachment.delete(id, force=True, remove_local=True)
        elif type == 'attachments.uploaded.clear':
            self.window.controller.assistant.files.clear(True)
        elif type == 'attachments.uploaded.delete':
            self.window.controller.assistant.files.delete(id, True)
        elif type == 'attachments.clear':
            self.window.controller.attachment.clear(force=True, remove_local=True)
        elif type == 'attachments.ctx.clear':
            self.window.controller.chat.attachment.clear(force=True, remove_local=True)
        elif type == 'attachments.ctx.delete':
            self.window.controller.chat.attachment.delete_by_idx(id, force=True, remove_local=True)

        # files
        elif type == 'files.delete':
            self.window.controller.files.delete(id, True)
        elif type == 'files.delete.recursive':
            self.window.controller.files.delete_recursive(id, True)

        # workdir change dialog
        elif type == 'workdir.change':
            self.window.controller.settings.workdir.migrate(id, True)
        elif type == 'workdir.update':
            self.window.controller.settings.workdir.update(id, True)

        # tab close all
        elif type == 'tab.close_all':
            self.window.controller.ui.tabs.close_all(id, 0, True)  # by type

        # editor
        elif type == 'editor.changed.clear':
            self.window.tools.get("editor").clear(id=id, force=True, save=True)
        elif type == 'editor.changed.open':
            self.window.tools.get("editor").open_file(id=id, force=True, save=True)
        elif type == 'editor.changed.close':
            self.window.tools.get("editor").close(id, save=True)
        elif type == 'editor.changed.restore':
            self.window.tools.get("editor").restore(id=id, force=True, save=True)

        # assistants
        elif type == 'assistant.delete':
            self.window.controller.assistant.delete(id, True)
        elif type == 'assistant.import':
            self.window.controller.assistant.batch.import_assistants(True)
        elif type == 'assistant.files.import.all':
            self.window.controller.assistant.batch.import_files(True)
        elif type == 'assistant.files.import.store':
            self.window.controller.assistant.batch.import_store_files(id, True)  # by store_id
        elif type == 'assistant.files.truncate':
            self.window.controller.assistant.batch.truncate_files(True)
        elif type == 'assistant.files.truncate.store':
            self.window.controller.assistant.batch.truncate_store_files(id, True)  # by store_id
        elif type == 'assistant.files.clear.all':
            self.window.controller.assistant.batch.clear_files(True)
        elif type == 'assistant.files.clear.store':
            self.window.controller.assistant.batch.clear_store_files(id, True)  # by store_id
        elif type == 'assistant.files.upload':
            self.window.controller.assistant.batch.upload(True)
        elif type == 'assistant.functions.import':
            self.window.controller.assistant.editor.import_functions(True)
        elif type == 'assistant.functions.clear':
            self.window.controller.assistant.editor.clear_functions(True)

        # assistants vector stores
        elif type == 'assistant.store.delete':
            self.window.controller.assistant.store.delete(id, True)  # by store_id
        elif type == 'assistant.store.import':
            self.window.controller.assistant.batch.import_stores(True)
        elif type == 'assistant.store.truncate':
            self.window.controller.assistant.batch.truncate_stores(True)
        elif type == 'assistant.store.clear':
            self.window.controller.assistant.batch.clear_stores(True)
        elif type == 'assistant.store.refresh':
            self.window.controller.assistant.batch.refresh_stores(True)

        # settings
        elif type == 'settings.defaults.user':
            self.window.controller.settings.editor.load_defaults_user(True)
        elif type == 'settings.defaults.app':
            self.window.controller.settings.editor.load_defaults_app(True)
        elif type == 'settings.dict.delete':
            self.window.controller.config.dictionary.delete_item(parent_object, id, True)

        # settings / file editor
        elif type == 'settings.editor.defaults.user':
            self.window.controller.settings.editor.load_editor_defaults_user(True)
        elif type == 'settings.editor.defaults.app':
            self.window.controller.settings.editor.load_editor_defaults_app(True)

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

        # index tool
        elif type == 'idx.tool.truncate':
            self.window.tools.get("indexer").delete_db_idx(id, True)
        elif type == 'idx.tool.index':
            self.window.tools.get("indexer").index_data(True)

        # prompt delete
        elif type == 'prompt.custom.delete':
            self.window.controller.presets.delete_prompt(id, True)

    def dismiss(
            self,
            type: str,
            id: Any
    ):
        """
        Confirm dialog dismiss

        :param type: dialog type
        :param id: dialog object id
        """
        # editor
        if type == 'editor.changed.clear':
            self.window.tools.get("editor").clear(id=id, force=True)
        elif type == 'editor.changed.open':
            self.window.tools.get("editor").open_file(id=id, force=True)
        elif type == 'editor.changed.close':
            self.window.tools.get("editor").close(id)
        elif type == 'editor.changed.restore':
            self.window.tools.get("editor").restore(id=id, force=True)

        self.window.ui.dialog['confirm'].close()

    def accept_rename(
            self,
            type: str,
            id: Any,
            name: str
    ):
        """
        Update name of object

        :param type: dialog type
        :param id: dialog object id
        :param name: new name
        """
        # ctx
        if type == 'ctx':
            self.window.controller.ctx.update_name(id, name)
        elif type == 'ctx.group':
            self.window.controller.ctx.update_group_name(id, name, True)

        # tab
        elif type == 'tab':
            self.window.controller.ui.tabs.update_name(id, name, True)

        # attachments and files
        elif type == 'attachment':
            self.window.controller.attachment.update_name(id, name)
        elif type == 'attachment_uploaded':
            self.window.controller.assistant.files.update_name(id, name)
        elif type == 'output_file':
            self.window.controller.files.update_name(id, name)

        # notepad
        elif type == 'notepad':
            self.window.controller.notepad.update_name(id, name, True)

        # plugin presets
        elif type == 'plugin.preset':
            self.window.controller.plugins.presets.update_name(id, name)

        # custom prompt templates rename
        elif type == 'prompt.custom.rename':
            self.window.controller.presets.rename_prompt(id, name, True)

        # custom prompt templates new
        elif type == 'prompt.custom.new':
            self.window.controller.presets.save_prompt(name, True)

    def accept_create(
            self,
            type: str,
            id: any,
            name: str
    ):
        """
        Create new object

        :param type: dialog type
        :param id: dialog object id
        :param name: name
        """
        # filesystem
        if type == 'mkdir':
            self.window.controller.files.make_dir(id, name)
        if type == 'touch':
            self.window.controller.files.touch_file(id, name, True)
        elif type == 'duplicate':
            self.window.controller.files.duplicate_local(id, name, True)

        # plugin presets
        elif type == 'plugin.preset':
            self.window.controller.plugins.presets.create(id, name)

        # ctx groups
        elif type == 'ctx.group':
            self.window.controller.ctx.create_group(name, id)

    def accept_url(
            self,
            type: str,
            id: any,
            url: str
    ):
        """
        Update URL provided

        :param type: dialog type
        :param id: dialog object id
        :param url: URL
        """
        # add attachment
        if type == 'attachment':
            self.window.controller.attachment.add_url(url)

    def dismiss_rename(self):
        """Dismiss rename dialog"""
        self.window.ui.dialog['rename'].close()

    def dismiss_create(self):
        """Dismiss create dialog"""
        self.window.ui.dialog['create'].close()

    def dismiss_url(self):
        """Dismiss url dialog"""
        self.window.ui.dialog['url'].close()
