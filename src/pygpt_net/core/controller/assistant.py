#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2023.12.14 19:00:00                  #
# ================================================== #
import os
import threading
import time
import webbrowser

from PySide6.QtCore import QObject, Signal, Slot

from ..utils import trans
from ..assistants import Assistants


class Assistant:
    def __init__(self, window=None):
        """
        Assistants controller

        :param window: main window object
        """
        self.window = window
        self.assistants = Assistants(self.window.config)
        self.thread_run = None
        self.thread_run_started = False
        self.force_stop = False

    def setup(self):
        """Setup assistants"""
        self.assistants.load()
        self.update()

    def update(self):
        """Updates assistants list"""
        self.update_list()
        self.update_uploaded()
        self.select_assistant_by_current()

    def update_list(self):
        """Updates assistants list"""
        items = self.assistants.get_all()
        self.window.ui.toolbox.update_list_assistants('assistants', items)

    def update_uploaded(self):
        """Updates uploaded files list"""
        assistant_id = self.window.config.get('assistant')
        if assistant_id is None or assistant_id == "":
            return
        assistant = self.assistants.get_by_id(assistant_id)
        items = assistant.files
        self.window.ui.attachments_uploaded.update_list('attachments_uploaded', items)
        self.update_tab_label()

    def update_tab_label(self):
        """
        Updates tab label

        :param mode: mode
        """
        assistant_id = self.window.config.get('assistant')
        if assistant_id is None or assistant_id == "":
            self.window.tabs['input'].setTabText(2, trans('attachments_uploaded.tab'))
            return

        assistant = self.assistants.get_by_id(assistant_id)
        items = assistant.files
        num_files = len(items)
        suffix = ''
        if num_files > 0:
            suffix = f' ({num_files})'
        self.window.tabs['input'].setTabText(2, trans('attachments_uploaded.tab') + suffix)

    def select(self, idx):
        """
        Selects assistant on the list

        :param idx: IDx on the list
        """
        # mark assistant as selected
        id = self.assistants.get_by_idx(idx)
        self.window.config.set('assistant', id)

        # update attachments list with list of attachments from assistant
        mode = self.window.config.get('mode')
        assistant = self.assistants.get_by_id(id)
        self.window.controller.attachment.import_from_assistant(mode, assistant)
        self.window.controller.attachment.update()
        self.update()

    def update_field(self, id, value, assistant_id=None, current=False):
        """
        Updates assistant field from editor

        :param id: field id
        :param value: field value
        :param assistant_id: assistant ID
        :param current: if True, updates current assistant
        """
        if assistant_id is not None and assistant_id != "":
            if self.assistants.has(assistant_id):
                assistant = self.assistants.get_by_id(assistant_id)
                if id == 'assistant.name':
                    assistant.name = value
                elif id == 'assistant.description':
                    assistant.description = value
                elif id == 'assistant.instructions':
                    assistant.instructions = value
                elif id == 'assistant.model':
                    assistant.model = value

        self.window.controller.ui.update()

    def edit(self, idx=None):
        """
        Opens assistant editor

        :param idx: assistant index (row index)
        """
        id = None
        if idx is not None:
            id = self.assistants.get_by_idx(idx)

        self.init_editor(id)
        self.window.ui.dialogs.open_editor('editor.assistants', idx)

    def init_editor(self, id=None):
        """
        Initializes assistant editor

        :param id: assistant ID
        """
        assistant = self.assistants.create()
        assistant.model = "gpt-4-1106-preview"  # default model

        # if editing existing assistant
        if id is not None and id != "":
            if self.assistants.has(id):
                assistant = self.assistants.get_by_id(id)
        else:
            # default instructions
            assistant.instructions = 'You are a helpful assistant.'

        if assistant.name is None:
            assistant.name = ""
        if assistant.description is None:
            assistant.description = ""
        if assistant.instructions is None:
            assistant.instructions = ""
        if assistant.model is None:
            assistant.model = ""

        self.window.config_option['assistant.id'].setText(id)
        self.config_change('assistant.name', assistant.name, 'assistant.editor')
        self.config_change('assistant.description', assistant.description, 'assistant.editor')
        self.config_change('assistant.instructions', assistant.instructions, 'assistant.editor')
        self.config_change('assistant.model', assistant.model, 'assistant.editor')

        if assistant.has_tool('code_interpreter'):
            self.config_toggle('assistant.tool.code_interpreter', True, 'assistant.editor')
        else:
            self.config_toggle('assistant.tool.code_interpreter', False, 'assistant.editor')

        if assistant.has_tool('retrieval'):
            self.config_toggle('assistant.tool.retrieval', True, 'assistant.editor')
        else:
            self.config_toggle('assistant.tool.retrieval', False, 'assistant.editor')

        # restore functions
        if assistant.has_functions():
            functions = assistant.get_functions()
            values = []
            for function in functions:
                values.append({"name": function['name'], "params": function['params'], "desc": function['desc']})
            self.window.config_option['assistant.tool.function'].items = values
            self.window.config_option['assistant.tool.function'].model.updateData(values)
        else:
            self.window.config_option['assistant.tool.function'].items = []
            self.window.config_option['assistant.tool.function'].model.updateData([])

        # set focus to name field
        self.window.config_option['assistant.name'].setFocus()

    def save(self):
        """
        Saves assistant
        """
        created = False
        id = self.window.config_option['assistant.id'].text()
        name = self.window.config_option['assistant.name'].text()
        model = self.window.config_option['assistant.model'].text()

        # check name
        if name is None or name == "" or model is None or model == "":
            self.window.ui.dialogs.alert(trans('assistant.form.empty.fields'))
            return

        if id is None or id == "" or not self.assistants.has(id):
            assistant = self.create()  # id created in API
            if assistant is None:
                print("Assistant not created")
                return
            id = assistant.id
            self.assistants.add(assistant)
            self.window.config_option['assistant.id'].setText(id)
            created = True
        else:
            assistant = self.assistants.get_by_id(id)

        # assign data from fields to assistant
        self.assign_data(assistant)

        # update in API
        if not created:
            self.assistant_update(assistant)

        # save file
        self.assistants.save()
        self.window.controller.model.update()
        self.update()

        self.window.ui.dialogs.close('editor.assistants')
        self.window.set_status(trans('status.assistant.saved'))

    def create(self):
        """
        Creates assistant
        """
        assistant = self.assistants.create()
        self.assign_data(assistant)
        try:
            return self.window.gpt.assistant_create(assistant)
        except Exception as e:
            self.window.ui.dialogs.alert(str(e))

    def assistant_update(self, assistant):
        """
        Update assistant
        """
        self.assign_data(assistant)
        try:
            return self.window.gpt.assistant_update(assistant)
        except Exception as e:
            self.window.ui.dialogs.alert(str(e))

    def import_assistants(self, force=False):
        """
        Imports all remote assistants from API

        :param force: if True, imports without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm('assistant_import', '', trans('confirm.assistant.import'))
            return

        try:
            # import assistants
            items = self.assistants.get_all()
            self.window.gpt.assistant_import(items)
            self.assistants.items = items
            self.assistants.save()

            # import uploaded files
            for assistant_id in self.assistants.items:
                assistant = self.assistants.get_by_id(assistant_id)
                self.import_files(assistant)
            # status
            self.window.set_status("Imported assistants: " + str(len(items)))
        except Exception as e:
            print("Error importing assistants")
            print(e)
            self.window.ui.dialogs.alert(str(e))
        self.update()

    def import_files(self, assistant):
        """
        Imports assistant files

        :param assistant: assistant
        """
        try:
            files = self.window.gpt.assistant_file_list(assistant.id)
            self.assistants.import_files(assistant, files)
            self.assistants.save()
            self.update()
            self.window.set_status("Imported files: " + str(len(files)))
        except Exception as e:
            print("Error importing assistant files")
            print(e)
            self.window.ui.dialogs.alert(str(e))

    def assign_data(self, assistant):
        """
        Assigns data from fields to assistant

        :param assistant: assistant
        """
        assistant.name = self.window.config_option['assistant.name'].text()
        assistant.model = self.window.config_option['assistant.model'].text()
        assistant.description = self.window.config_option['assistant.description'].text()
        assistant.instructions = self.window.config_option['assistant.instructions'].toPlainText()
        assistant.tools = {
            'code_interpreter': self.window.config_option['assistant.tool.code_interpreter'].box.isChecked(),
            'retrieval': self.window.config_option['assistant.tool.retrieval'].box.isChecked(),
            'function': [],  # functions are assigned separately
        }

        # assign functions
        functions = []
        for function in self.window.config_option['assistant.tool.function'].items:
            name = function['name']
            params = function['params']
            desc = function['desc']
            if name is None or name == "":
                continue
            if params is None or params == "":
                params = '{"type": "object", "properties": {}}'
            if desc is None:
                desc = ""
            functions.append({"name": name, "params": params, "desc": desc})
        if len(functions) > 0:
            assistant.tools['function'] = functions
        else:
            assistant.tools['function'] = []

    def clear(self, force=False):
        """
        Clears assistant data

        :param force: force clear data
        """
        id = self.window.config.get('assistant')

        if not force:
            self.window.ui.dialogs.confirm('assistant_clear', '', trans('confirm.assistant.clear'))
            return

        if id is not None and id != "":
            if self.assistants.has(id):
                assistant = self.assistants.get_by_id(id)
                assistant.reset()

        self.window.set_status(trans('status.assistant.cleared'))
        self.update()

    def select_file(self, idx):
        """
        Selects file

        :param idx: index of file
        """
        assistant_id = self.window.config.get('assistant')
        if assistant_id is None or assistant_id == "":
            return
        assistant = self.assistants.get_by_id(assistant_id)
        if assistant is None:
            return
        self.assistants.current_file = self.assistants.get_file_id_by_idx(assistant, idx)

    def sync_files(self, force=False):
        """
        Syncs files with API

        :param force: force sync files
        """
        if not force:
            self.window.ui.dialogs.confirm('assistant_import_files', '', trans('confirm.assistant.import_files'))
            return

        assistant_id = self.window.config.get('assistant')
        if assistant_id is None or assistant_id == "":
            return
        assistant = self.assistants.get_by_id(assistant_id)
        if assistant is None:
            return
        try:
            self.import_files(assistant)
        except Exception as e:
            print(e)
            self.window.ui.dialogs.alert(str(e))

    def clear_files(self, force=False):
        """
        Deletes all files

        :param force: force clear files
        """
        if not force:
            self.window.ui.dialogs.confirm('attachments_uploaded.clear', -1, trans('attachments_uploaded.clear.confirm'))
            return

        assistant_id = self.window.config.get('assistant')
        if assistant_id is None or assistant_id == "":
            return

        # delete all files
        if self.assistants.has(assistant_id):
            assistant = self.assistants.get_by_id(assistant_id)
            for file_id in list(assistant.files):
                try:
                    self.window.gpt.assistant_file_delete(assistant_id, file_id)
                    assistant.delete_file(file_id)
                except Exception as e:
                    self.window.ui.dialogs.alert(str(e))

                # delete file
                if assistant.has_file(file_id):
                    assistant.delete_file(file_id)
                # delete attachment
                if assistant.has_attachment(file_id):
                    assistant.delete_attachment(file_id)

            self.assistants.save()
            self.update()

    def delete(self, idx=None, force=False):
        """
        Deletes assistant

        :param idx: assistant index (row index)
        :param force: force delete without confirmation
        """
        if idx is not None:
            id = self.assistants.get_by_idx(idx)
            if id is not None and id != "":
                if self.assistants.has(id):
                    # if exists then show confirmation dialog
                    if not force:
                        self.window.ui.dialogs.confirm('assistant_delete', idx, trans('confirm.assistant.delete'))
                        return

                    # clear if this is current assistant
                    if id == self.window.config.get('assistant'):
                        self.window.config.set('assistant', None)
                        self.window.config.set('assistant_thread', None)

                    # delete in API
                    try:
                        self.window.gpt.assistant_delete(id)
                    except Exception as e:
                        self.window.ui.dialogs.alert(str(e))

                    self.assistants.delete(id)
                    self.update()
                    self.window.set_status(trans('status.assistant.deleted'))

    def config_toggle(self, id, value, section=None):
        """
        Toggles checkbox

        :param id: checkbox option id
        :param value: checkbox option value
        :param section: settings section
        """
        assistant_id = self.window.config.get('assistant')  # current assistant
        is_current = True
        if section == 'assistant.editor':
            assistant_id = self.window.config_option['assistant.id']  # editing assistant
            is_current = False
        self.update_field(id, value, assistant_id, is_current)

    def config_change(self, id, value, section=None):
        """
        Changes input value

        :param id: input option id
        :param value: input option value
        :param section: settings section
        """
        # validate filename
        if id == 'assistant.id':
            self.window.config_option[id].setText(value)

        assistant_id = self.window.config.get('assistant')  # current assistant
        is_current = True
        if section == 'assistant.editor':
            assistant_id = self.window.config_option['assistant.id']  # editing assistant
            is_current = False
        self.update_field(id, value, assistant_id, is_current)
        self.window.config_option[id].setText('{}'.format(value))

    def rename_file(self, idx):
        """
        Renames file

        :param idx: selected attachment index
        """
        assistant_id = self.window.config.get('assistant')
        if assistant_id is None or assistant_id == "":
            return
        assistant = self.assistants.get_by_id(assistant_id)
        if assistant is None:
            return

        # get attachment ID by index
        file_id = self.assistants.get_file_id_by_idx(assistant, idx)

        # get attachment object by ID
        data = self.assistants.get_file_by_id(assistant, file_id)
        if data is None:
            return

        # set dialog and show
        self.window.dialog['rename'].id = 'attachment_uploaded'
        self.window.dialog['rename'].input.setText(data['name'])
        self.window.dialog['rename'].current = file_id
        self.window.dialog['rename'].show()
        self.update()

    def update_file_name(self, file_id, name):
        """
        Renames uploaded remote file name

        :param file_id: file_id
        :param name: new name
        """
        assistant_id = self.window.config.get('assistant')
        if assistant_id is None or assistant_id == "":
            self.close_rename_file()
            return
        assistant = self.assistants.get_by_id(assistant_id)
        if assistant is None:
            self.close_rename_file()
            return
        self.assistants.rename_file(assistant, file_id, name)
        self.close_rename_file()

    def close_rename_file(self):
        # close rename dialog and update attachments list
        self.window.dialog['rename'].close()
        self.update()

    def delete_file(self, idx, force=False):
        """
        Deletes file

        :param idx: file idx
        :param force: force delete without confirmation
        """
        if not force:
            self.window.ui.dialogs.confirm('attachments_uploaded.delete', idx, trans('attachments_uploaded.delete.confirm'))
            return

        # get current assistant
        assistant_id = self.window.config.get('assistant')
        if assistant_id is None or assistant_id == "":
            return
        assistant = self.assistants.get_by_id(assistant_id)
        if assistant is None:
            return

        # get attachment ID by index
        file_id = self.assistants.get_file_id_by_idx(assistant, idx)

        # delete file in API
        try:
            self.window.gpt.assistant_file_delete(assistant_id, file_id)
        except Exception as e:
            self.window.ui.dialogs.alert(str(e))
            return  # do not delete locally if not deleted in API

        # delete locally
        if self.assistants.has(assistant_id):
            need_save = False
            # delete file
            if assistant.has_file(file_id):
                assistant.delete_file(file_id)
                need_save = True
            # delete attachment
            if assistant.has_attachment(file_id):
                assistant.delete_attachment(file_id)
                need_save = True
            # save assistants and update assistants list
            if need_save:
                self.assistants.save()
                self.update()

    def clear_attachments(self, assistant):
        """
        Clears attachments

        :param assistant: assistant object
        """
        assistant.clear_attachments()
        self.assistants.save()
        self.update()

    def count_upload_attachments(self, attachments):
        """
        Counts uploaded attachments

        :param attachments: attachments list
        :return: number of uploaded files
        """
        num = 0
        for id in list(attachments):
            attachment = attachments[id]
            if not attachment.send:
                num += 1  # increment uploaded files counter
        return num

    def upload_attachments(self, mode, attachments):
        """
        Uploads attachments to assistant

        :param mode: mode
        :param attachments: attachments list
        :return: number of uploaded files
        """
        # get current chosen assistant
        assistant_id = self.window.config.get('assistant')
        if assistant_id is None:
            return 0
        assistant = self.assistants.get_by_id(assistant_id)

        num = 0
        # loop on attachments
        for id in list(attachments):
            attachment = attachments[id]
            old_id = attachment.id  # tmp id

            # check if not already uploaded (ignore already uploaded files)
            if not attachment.send:
                print("Uploading file: {}".format(attachment.path))
                # check if file exists
                if not os.path.exists(attachment.path):
                    continue

                # upload local attachment file and get new ID (file_id)
                new_id = self.window.gpt.assistant_file_upload(assistant_id, attachment.path)
                if new_id is not None:
                    # mark as already uploaded
                    attachment.send = True
                    attachment.id = new_id
                    attachment.remote = new_id

                    # replace old ID with new one
                    self.window.controller.attachment.attachments.replace_id(mode, old_id, attachment)

                    # update assistant remote files list
                    assistant.files[new_id] = {
                        'id': new_id,
                        'name': attachment.name,
                        'path': attachment.path,
                    }

                    # update assistant attachments list
                    self.assistants.replace_attachment(assistant, attachment, old_id, new_id)
                    num += 1  # increment uploaded files counter

        # update assistants list
        self.assistants.save()

        # update attachments UI
        self.window.controller.attachment.update()

        # update uploaded list
        if num > 0:
            self.update_uploaded()  # update uploaded list UI

        return num

    def append_attachment(self, assistant, attachment):
        """
        Appends attachment to assistant

        :param attachment: attachment
        :param assistant: assistant object
        """
        # get current chosen assistant
        assistant.add_attachment(attachment)  # append attachment
        self.assistants.save()  # save assistants

    def goto_online(self):
        """Opens Assistants page"""
        webbrowser.open('https://platform.openai.com/assistants')

    def create_thread(self):
        """
        Creates assistant thread

        :return: thread_id
        """
        thread_id = self.window.gpt.assistant_thread_create()
        self.window.config.set('assistant_thread', thread_id)
        self.window.gpt.context.append_thread(thread_id)
        return thread_id

    def select_assistant_by_current(self):
        """Selects assistant by current"""
        assistant_id = self.window.config.get('assistant')
        items = self.window.controller.assistant.assistants.get_all()
        if assistant_id in items:
            idx = list(items.keys()).index(assistant_id)
            current = self.window.models['assistants'].index(idx, 0)
            self.window.data['assistants'].setCurrentIndex(current)

    def handle_message_files(self, msg):
        """
        Handles (download) message files

        :param msg: message
        """
        num_downloaded = 0
        paths = []
        for file_id in msg.file_ids:
            path = self.window.controller.attachment.download(file_id)
            if path is not None:
                paths.append(path)
                num_downloaded += 1
        if num_downloaded > 0:
            # show alert with downloaded files
            msg = "Downloaded {} file(s): {}".format(num_downloaded, ", ".join(paths))
            self.window.ui.dialogs.alert(msg)

    def handle_run_messages(self, ctx):
        """
        Handles run messages

        :param ctx: context
        """
        data = self.window.gpt.assistant_msg_list(ctx.thread)
        for msg in data:
            if msg.role == "assistant":
                ctx.set_output(msg.content[0].text.value)
                self.handle_message_files(msg)
                self.window.controller.input.handle_response(ctx, 'assistant', False)
                self.window.controller.input.handle_commands(ctx)
                break

    def handle_run(self, ctx):
        """
        Handles assistant's run

        :param ctx: context
        """
        listener = AssistantRunThread(window=self.window, ctx=ctx)
        listener.updated.connect(self.handle_status)
        listener.destroyed.connect(self.handle_destroy)
        listener.started.connect(self.handle_started)

        self.thread_run = threading.Thread(target=listener.run)
        self.thread_run.start()
        self.thread_run_started = True

    @Slot(str, object)
    def handle_status(self, status, ctx):
        """
        Insert text to input and send

        :param status: status
        :param ctx: context
        """
        print("Run status: {}".format(status))
        if status != "queued" and status != "in_progress":
            self.window.controller.input.unlock_input()  # unlock input
        if status == "completed":
            self.force_stop = False
            self.handle_run_messages(ctx)
            self.window.statusChanged.emit(trans('assistant.run.completed'))
        elif status == "failed":
            self.force_stop = False
            self.window.controller.input.unlock_input()
            self.window.statusChanged.emit(trans('assistant.run.failed'))

    @Slot()
    def handle_destroy(self):
        """
        Insert text to input and send
        """
        self.thread_run_started = False
        self.force_stop = False

    @Slot()
    def handle_started(self):
        """
        Handle listening started
        """
        print("Run: assistant is listening status...")
        self.window.statusChanged.emit(trans('assistant.run.listening'))


class AssistantRunThread(QObject):
    updated = Signal(object, object)
    destroyed = Signal()
    started = Signal()

    def __init__(self, window=None, ctx=None):
        """
        Run assistant run status check thread

        :param window: window
        :param ctx: context
        """
        super().__init__()
        self.window = window
        self.ctx = ctx
        self.check = True
        self.stop_reasons = ["cancelling", "cancelled", "failed", "completed", "expired", "requires_action"]

    def run(self):
        """Run thread"""
        try:
            self.started.emit()
            while self.check \
                    and not self.window.is_closing \
                    and not self.window.controller.assistant.force_stop:
                status = self.window.gpt.assistant_run_status(self.ctx.thread, self.ctx.run_id)
                self.updated.emit(status, self.ctx)
                # finished or failed
                if status in self.stop_reasons:
                    self.check = False
                    self.destroyed.emit()
                    break
                time.sleep(1)
            self.destroyed.emit()
        except Exception as e:
            print(e)
            self.destroyed.emit()
