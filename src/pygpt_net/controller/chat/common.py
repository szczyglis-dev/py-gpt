#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.10 19:00:00                  #
# ================================================== #

import os

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QFileDialog, QApplication

from pygpt_net.core.events import Event, AppEvent, RenderEvent
from pygpt_net.item.ctx import CtxItem
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
        # stream mode
        if self.window.core.config.get('stream'):
            self.window.ui.nodes['input.stream'].setChecked(True)
        else:
            self.window.ui.nodes['input.stream'].setChecked(False)

        # send clear
        if self.window.core.config.get('send_clear'):
            self.window.ui.nodes['input.send_clear'].setChecked(True)
        else:
            self.window.ui.nodes['input.send_clear'].setChecked(False)

        # send with enter/shift/disabled
        mode = self.window.core.config.get('send_mode')
        if mode == 2:
            self.window.ui.nodes['input.send_shift_enter'].setChecked(True)
            self.window.ui.nodes['input.send_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(False)
        elif mode == 1:
            self.window.ui.nodes['input.send_enter'].setChecked(True)
            self.window.ui.nodes['input.send_shift_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(False)
        elif mode == 0:
            self.window.ui.nodes['input.send_enter'].setChecked(False)
            self.window.ui.nodes['input.send_shift_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(True)

        # cmd enabled
        if self.window.core.config.get('cmd'):
            self.window.ui.nodes['cmd.enabled'].setChecked(True)
        else:
            self.window.ui.nodes['cmd.enabled'].setChecked(False)

        # output timestamps
        is_timestamp = self.window.core.config.get('output_timestamp')
        self.window.ui.nodes['output.timestamp'].setChecked(is_timestamp)
        if is_timestamp:
            data = {
                "initialized": self.initialized,
            }
            event = RenderEvent(RenderEvent.ON_TS_ENABLE, data)
            self.window.dispatch(event)

        # raw (plain) output
        plain = self.window.core.config.get('render.plain')
        self.window.ui.nodes['output.raw'].setChecked(plain)
        if plain:
            self.window.ui.nodes['output.timestamp'].setVisible(True)
            for pid in self.window.ui.nodes['output']:
                self.window.ui.nodes['output'][pid].setVisible(False)
                self.window.ui.nodes['output_plain'][pid].setVisible(True)
        else:
            self.window.ui.nodes['output.timestamp'].setVisible(False)
            for pid in self.window.ui.nodes['output']:
                self.window.ui.nodes['output'][pid].setVisible(True)
                self.window.ui.nodes['output_plain'][pid].setVisible(False)

        event = RenderEvent(RenderEvent.ON_SWITCH)
        self.window.dispatch(event)  # switch renderer if needed

        # edit icons
        """
        if self.window.core.config.has('ctx.edit_icons'):
            self.window.ui.nodes['output.edit'].setChecked(self.window.core.config.get('ctx.edit_icons'))
            data = {
                "initialized": self.initialized,
            }
            if self.window.core.config.get('ctx.edit_icons'):
                event = RenderEvent(RenderEvent.ON_EDIT_ENABLE, data)
            else:
                event = RenderEvent(RenderEvent.ON_EDIT_DISABLE, data)
            self.window.dispatch(event)
        """

        # images generation
        if self.window.core.config.get('img_raw'):
            self.window.ui.config['global']['img_raw'].setChecked(True)
        else:
            self.window.ui.config['global']['img_raw'].setChecked(False)

        # set focus to input
        self.window.ui.nodes['input'].setFocus()
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
        prev_text = self.window.ui.nodes['input'].toPlainText()
        cur = self.window.ui.nodes['input'].textCursor()
        cur.movePosition(QTextCursor.End)
        text = str(text).strip()
        if prev_text.strip() != "":
            text = separator + text
        s = text
        while s:
            head, sep, s = s.partition("\n")  # Split line at LF
            cur.insertText(head)  # Insert text at cursor
            if sep:  # New line if LF
                cur.insertBlock()
        cur.movePosition(QTextCursor.End)  # Move cursor to end of text
        self.window.ui.nodes['input'].setTextCursor(cur)  # Update visible cursor
        self.window.ui.nodes['input'].setFocus()  # Set focus to input

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
        if value == 0:
            self.window.ui.nodes['input.send_none'].setChecked(True)
            self.window.ui.nodes['input.send_shift_enter'].setChecked(False)
            self.window.ui.nodes['input.send_enter'].setChecked(False)
        elif value == 1:
            self.window.ui.nodes['input.send_enter'].setChecked(True)
            self.window.ui.nodes['input.send_shift_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(False)
        elif value == 2:
            self.window.ui.nodes['input.send_shift_enter'].setChecked(True)
            self.window.ui.nodes['input.send_enter'].setChecked(False)
            self.window.ui.nodes['input.send_none'].setChecked(False)
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
        if (self.window.controller.agent.experts.enabled() and
                self.window.core.experts.has_calls(ctx)):
            unlock = False
        if self.window.controller.kernel.stack.waiting():
            unlock = False
        if ctx.has_commands():
            unlock = False
        return unlock

    def stop(self, exit: bool = False):
        """
        Stop all

        :param exit: True if called on app exit
        """
        QApplication.processEvents()
        mode = self.window.core.config.get('mode')
        event = Event(Event.FORCE_STOP, {
            "value": True,
        })
        self.window.dispatch(event)  # stop event
        event = Event(Event.AUDIO_INPUT_TOGGLE, {
            "value": False,
        })
        self.window.controller.kernel.stack.clear()  # pause reply stack
        self.window.controller.agent.experts.stop()
        self.window.controller.agent.legacy.on_stop()
        self.window.controller.assistant.threads.stop = True
        self.window.controller.assistant.threads.reset()  # reset run and func calls
        self.window.dispatch(event)  # stop audio input
        self.window.controller.kernel.halt = True

        event = RenderEvent(RenderEvent.TOOL_END)
        self.window.dispatch(event)  # show waiting

        self.window.core.gpt.stop()
        self.unlock_input()

        self.window.controller.chat.input.generating = False
        self.window.update_status(trans('status.stopped'))
        self.window.stateChanged.emit(self.window.STATE_IDLE)

        # remotely stop assistant
        if mode == "assistant" and not exit:
            try:
                self.window.controller.assistant.run_stop()
            except Exception as e:
                self.window.core.debug.log(e)

        if not exit:
            self.window.dispatch(AppEvent(AppEvent.INPUT_STOPPED))  # app event

    def check_api_key(self, monit: bool = True) -> bool:
        """
        Check if API KEY is set

        :param monit: True if monitor should be shown
        :return: True if API KEY is set, False otherwise
        """
        result = True
        if self.window.core.config.get('api_key') is None or self.window.core.config.get('api_key') == '':
            if monit:
                self.window.controller.launcher.show_api_monit()
            self.window.update_status("Missing API KEY!")
            result = False
        return result

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

    def img_enable_raw(self):
        """Enable help for images"""
        self.window.core.config.set('img_raw', True)
        self.window.core.config.save()

    def img_disable_raw(self):
        """Disable help for images"""
        self.window.core.config.set('img_raw', False)
        self.window.core.config.save()

    def img_toggle_raw(self, state: bool):
        """
        Toggle help for images

        :param state: state of checkbox
        """
        if not state:
            self.img_disable_raw()
        else:
            self.img_enable_raw()

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
            self.window.update_status(trans('status.saved') + ": " + os.path.basename(file_name))

    def show_response_tokens(self, ctx: CtxItem):
        """
        Update response tokens

        :param ctx: CtxItem
        """
        extra_data = ""
        if ctx.is_vision:
            extra_data = " (VISION)"
        self.window.update_status(
            trans('status.tokens') + ": {} + {} = {}{}".
            format(
                ctx.input_tokens,
                ctx.output_tokens,
                ctx.total_tokens,
                extra_data,
            ))

