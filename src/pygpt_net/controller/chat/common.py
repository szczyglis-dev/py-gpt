#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.09.01 23:00:00                  #
# ================================================== #

import os

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QFileDialog, QApplication

from pygpt_net.core.events import Event, AppEvent, RenderEvent, KernelEvent
from pygpt_net.core.types import MODE_ASSISTANT, MODE_AUDIO
from pygpt_net.item.ctx import CtxItem
from pygpt_net.item.model import ModelItem
from pygpt_net.utils import trans


class Common:
    def __init__(self, window=None):
        """
        Chat common controller

        :param window: Window instance
        """
        self.window = window
        self.initialized = False

    def setup(self):
        """Set up UI"""
        nodes = self.window.ui.nodes
        config = self.window.core.config

        # stream mode
        if config.get('stream'):
            nodes['input.stream'].setChecked(True)
        else:
            nodes['input.stream'].setChecked(False)

        # send clear
        if config.get('send_clear'):
            nodes['input.send_clear'].setChecked(True)
        else:
            nodes['input.send_clear'].setChecked(False)

        # send with enter/shift/disabled
        mode = config.get('send_mode')
        if mode == 2:
            nodes['input.send_shift_enter'].setChecked(True)
            nodes['input.send_enter'].setChecked(False)
            nodes['input.send_none'].setChecked(False)
        elif mode == 1:
            nodes['input.send_enter'].setChecked(True)
            nodes['input.send_shift_enter'].setChecked(False)
            nodes['input.send_none'].setChecked(False)
        elif mode == 0:
            nodes['input.send_enter'].setChecked(False)
            nodes['input.send_shift_enter'].setChecked(False)
            nodes['input.send_none'].setChecked(True)

        # cmd enabled
        if config.get('cmd'):
            nodes['cmd.enabled'].setChecked(True)
        else:
            nodes['cmd.enabled'].setChecked(False)

        # output timestamps
        is_timestamp = config.get('output_timestamp')
        nodes['output.timestamp'].setChecked(is_timestamp)
        if is_timestamp:
            data = {
                "initialized": self.initialized,
            }
            event = RenderEvent(RenderEvent.ON_TS_ENABLE, data)
            self.window.dispatch(event)

        # raw (plain) output
        plain = config.get('render.plain')
        nodes['output.raw'].setChecked(plain)
        if plain:
            nodes['output.timestamp'].setVisible(True)
            for pid in nodes['output']:
                try:
                    nodes['output'][pid].setVisible(False)
                    nodes['output_plain'][pid].setVisible(True)
                except Exception as e:
                    pass
        else:
            nodes['output.timestamp'].setVisible(False)
            for pid in nodes['output']:
                try:
                    nodes['output'][pid].setVisible(True)
                    nodes['output_plain'][pid].setVisible(False)
                except Exception as e:
                    pass

        event = RenderEvent(RenderEvent.ON_SWITCH)
        self.window.dispatch(event)  # switch renderer if needed

        # set focus to input
        nodes['input'].setFocus()
        self.initialized = True

    def append_to_input(
            self,
            text: str,
            separator: str = "\n"
    ):
        """
        Append text to input

        :param text: text to append
        :param separator: text separator
        """
        node = self.window.ui.nodes['input']
        prev_text = node.toPlainText()
        cur = node.textCursor()
        cur.movePosition(QTextCursor.End)
        text = str(text).strip()
        if prev_text.strip() != "":
            text = f"{separator}{text}"
        s = text
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertBlock()
        cur.movePosition(QTextCursor.End)  # Move cursor to end of text
        node.setTextCursor(cur)  # Update visible cursor
        node.setFocus()  # Set focus to input

        # update tokens counter
        self.window.controller.ui.update_tokens()

    def clear_input(self):
        """Clear input"""
        self.window.ui.nodes['input'].clear()

    def toggle_stream(self, value: bool):
        """
        Toggle stream

        :param value: True if enabled
        """
        self.window.core.config.set('stream', value)

    def toggle_cmd(self, value: bool):
        """
        Toggle cmd enabled

        :param value: True if enabled
        """
        self.window.core.config.set('cmd', value)

        # stop commands thread if running
        if not value:
            self.window.controller.command.stop = True
        else:
            self.window.controller.command.stop = False

        self.window.controller.ui.update()  # update tokens counters

    def toggle_send_clear(self, value: bool):
        """
        Toggle send clear

        :param value: True if enabled
        """
        self.window.core.config.set('send_clear', value)

    def toggle_send_shift(self, value: bool):
        """
        Toggle send with shift

        :param value: True if enabled
        """
        nodes = self.window.ui.nodes
        if value == 0:
            nodes['input.send_none'].setChecked(True)
            nodes['input.send_shift_enter'].setChecked(False)
            nodes['input.send_enter'].setChecked(False)
        elif value == 1:
            nodes['input.send_enter'].setChecked(True)
            nodes['input.send_shift_enter'].setChecked(False)
            nodes['input.send_none'].setChecked(False)
        elif value == 2:
            nodes['input.send_shift_enter'].setChecked(True)
            nodes['input.send_enter'].setChecked(False)
            nodes['input.send_none'].setChecked(False)
        self.window.core.config.set('send_mode', value)

    def focus_input(self):
        """Focus input"""
        self.window.ui.nodes['input'].setFocus()

    def lock_input(self):
        """Lock input"""
        self.window.controller.chat.input.locked = True
        self.window.ui.nodes['input.send_btn'].setEnabled(False)
        self.window.ui.nodes['input.stop_btn'].setVisible(True)

    def unlock_input(self):
        """Unlock input"""
        self.window.controller.chat.input.locked = False
        self.window.controller.chat.input.generating = False  # unlock
        self.window.ui.nodes['input.send_btn'].setEnabled(True)
        self.window.ui.nodes['input.stop_btn'].setVisible(False)

    def can_unlock(self, ctx: CtxItem) -> bool:
        """
        Check if input can be unlocked

        :param ctx: CtxItem
        :return: True if input can be unlocked
        """
        unlock = True
        mode = self.window.core.config.get('mode')
        if mode == "assistant":
            finish = False
        if (self.window.controller.agent.legacy.enabled() and
                (not self.window.controller.agent.legacy.finished or self.window.controller.agent.legacy.stop)):
            unlock = False
        if ((self.window.controller.agent.experts.enabled()
             or self.window.controller.agent.legacy.enabled(check_inline=False)) and
                self.window.core.experts.has_calls(ctx)):
            unlock = False
        if self.window.controller.kernel.stack.waiting():
            unlock = False
        if ctx.has_commands():
            unlock = False
        return unlock

    def handle_stop(self):
        """Handle stop"""
        # stop voice recording if active
        if self.window.controller.access.voice.is_recording:
            self.window.controller.access.voice.stop_recording(timeout=True)

        if self.window.core.plugins.get("audio_input").handler_simple.is_recording:
            self.window.dispatch(Event(Event.AUDIO_INPUT_RECORD_TOGGLE))
            return

        # stop audio output if playing
        self.window.controller.audio.stop_output()

        # stop generating if active
        self.window.controller.kernel.stop()

    def auto_unlock(self, ctx: CtxItem) -> bool:
        """
        Auto unlock input after end

        :param ctx: CtxItem
        :return: True if unlocked
        """
        # don't unlock input and leave stop btn if assistant mode or if agent/autonomous is enabled
        # send btn will be unlocked in agent mode on stop
        mode = self.window.core.config.get('mode')
        if self.can_unlock(ctx) and mode != MODE_AUDIO:
            if not self.window.controller.kernel.stopped():
                self.unlock_input()  # unlock input
                return True
        return False

    def stop(self, exit: bool = False):
        """
        Stop all

        :param exit: True if called on app exit
        """
        QApplication.processEvents()

        core = self.window.core
        controller = self.window.controller
        dispatch = self.window.dispatch
        dispatch(Event(Event.FORCE_STOP, {
            "value": True,
        })) # stop event

        controller.kernel.stack.clear()  # pause reply stack
        controller.agent.experts.stop()
        controller.agent.legacy.on_stop()
        controller.assistant.threads.stop = True
        controller.assistant.threads.reset()  # reset run and func calls
        dispatch(Event(Event.AUDIO_INPUT_TOGGLE, {
            "value": False,
        }))  # stop audio input
        controller.kernel.halt = True
        dispatch(RenderEvent(RenderEvent.TOOL_END))  # show waiting
        self.unlock_input()

        controller.chat.input.generating = False
        self.window.update_status(trans('status.stopped'))
        dispatch(KernelEvent(KernelEvent.STATE_IDLE))  # state: idle

        # remotely stop assistant
        mode = core.config.get('mode')
        if mode == MODE_ASSISTANT and not exit:
            try:
                controller.assistant.run_stop()
            except Exception as e:
                core.debug.log(e)

        if not exit:
            dispatch(AppEvent(AppEvent.INPUT_STOPPED))  # app event

        self.stop_client()  # stop clients

    def stop_client(self):
        """Stop all clients"""
        return # TODO: make it work without connection error after close
        self.window.core.api.openai.safe_close()
        self.window.core.api.google.safe_close()

    def check_api_key(
            self,
            mode: str,
            model: ModelItem,
            monit: bool = True
    ) -> bool:
        """
        Check if API KEY is set

        :param mode: current mode
        :param model: ModelItem instance
        :param monit: True if monitor should be shown
        :return: True if API KEY is set, False otherwise
        """
        if model is None:
            return True

        config = self.window.core.config
        provider_keys = {
            "openai": config.get('api_key', None),
            "azure_openai": config.get('api_key', None),
            "anthropic": config.get('api_key_anthropic', None),
            "google": config.get('api_key_google', None),
            "x_ai": config.get('api_key_xai', None),
            "perplexity": config.get('api_key_perplexity', None),
            "deepseek_api": config.get('api_key_deepseek', None),
            "mistral_ai": config.get('api_key_mistral', None),
        }

        if model.provider in provider_keys:
            api_key = provider_keys[model.provider]
            name = self.window.core.llm.get_provider_name(model.provider)
            if model.provider == 'openai':
                # allow empty key for models other than GPT
                if model.is_gpt() and (api_key is None or api_key == ''):
                    if monit:
                        self.window.ui.nodes['start.api_key.provider'].setText(name)
                        self.window.controller.launcher.show_api_monit()
                    self.window.update_status(f"Missing API KEY for provider: {name}")
                    return False
            else:
                if api_key is None or api_key == '':
                    if monit:
                        self.window.ui.nodes['start.api_key.provider'].setText(name)
                        self.window.controller.launcher.show_api_monit()
                    self.window.update_status(f"Missing API KEY for provider: {name}")
                    return False
        return True

    def toggle_timestamp(self, value: bool):
        """
        Toggle timestamp display

        :param value: value of the checkbox
        """
        self.window.core.config.set('output_timestamp', value)
        self.window.core.config.save()
        data = {
            "initialized": True
        }
        if value:
            event = RenderEvent(RenderEvent.ON_TS_ENABLE, data)
        else:
            event = RenderEvent(RenderEvent.ON_TS_DISABLE, data)
        self.window.dispatch(event)

    def toggle_edit_icons(self, value: bool):
        """
        Toggle edit icons

        :param value: value of the checkbox
        """
        self.window.core.config.set('ctx.edit_icons', value)
        self.window.core.config.save()
        data = {
            "initialized": True,
        }
        if value:
            event = RenderEvent(RenderEvent.ON_EDIT_ENABLE, data)
        else:
            event = RenderEvent(RenderEvent.ON_EDIT_DISABLE, data)
        self.window.dispatch(event)

    def toggle_raw(self, value: bool):
        """
        Toggle raw (plain) output

        :param value: value of the checkbox
        """
        self.window.core.config.set('render.plain', value)
        self.window.core.config.save()

        # update checkbox in settings dialog
        self.window.controller.config.checkbox.apply(
            'config',
            'render.plain',
            {
                'value': value
            },
        )
        event = RenderEvent(RenderEvent.ON_SWITCH)
        self.window.dispatch(event)

        # restore previous font size
        self.window.controller.ui.update_font_size()

    def save_text(
            self,
            text: str,
            type: str = "txt"
    ):
        """
        Save text to file

        :param text: text to save
        :param type: file type
        """
        last_dir = self.window.core.config.get_last_used_dir()
        options = QFileDialog.Options()
        if type == "html":
            selected_filter = "HTML Files (*.html)"
        else:
            selected_filter = "Text Files (*.txt)"
        file_name, _ = QFileDialog.getSaveFileName(
            self.window,
            "Save as text file",
            last_dir,
            "All Files (*);;Text Files (*.txt);;HTML Files (*.html);;Python Files (*.py);;Markdown Files (*.md)",
            selected_filter,
            options,
        )
        if file_name:
            # convert text to plain text
            self.window.core.config.set_last_used_dir(
                os.path.dirname(file_name),
            )
            with open(file_name, 'w', encoding="utf-8") as f:
                f.write(str(text).strip())
            self.window.update_status(f"{trans('status.saved')}: {os.path.basename(file_name)}")

    def show_response_tokens(self, ctx: CtxItem):
        """
        Update response tokens

        :param ctx: CtxItem
        """
        extra_data = ""
        if ctx.is_vision:
            extra_data = " (VISION)"
        self.window.update_status(
            f"{trans('status.tokens')}: {ctx.input_tokens} + {ctx.output_tokens} = {ctx.total_tokens}{extra_data}"
        )