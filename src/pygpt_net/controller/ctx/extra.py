#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.07.12 00:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QApplication

from pygpt_net.core.events import KernelEvent, RenderEvent
from pygpt_net.core.bridge.context import BridgeContext
from pygpt_net.utils import trans


class Extra:
    def __init__(self, window=None):
        """
        Extra actions controller

        :param window: Window instance
        """
        self.window = window
        self.audio_play_id = None

    def delete_item(self, item_id: int):
        """
        Delete ctx item

        :param item_id: Item id
        """
        self.window.controller.ctx.delete_item(item_id)

    def copy_item(self, item_id: int):
        """
        Copy ctx item to clipboard

        :param item_id: Item id
        """
        item = self.window.core.ctx.get_item_by_id(item_id)
        if item is not None and item.output is not None:
            QApplication.clipboard().setText(item.output.strip())
            self.window.update_status(trans("clipboard.copied"))

    def copy_code_block(self, id: int):
        """
        Copy code block to clipboard

        :param id: block id
        """
        blocks = self.window.controller.chat.render.instance().parser.get_code_blocks()
        if id not in blocks:
            print("Code block not found: ", id)
            return
        value = blocks.get(id)
        QApplication.clipboard().setText(value.strip())
        suffix = value[:30] + "..." if len(value) > 20 else value
        self.window.update_status(trans("clipboard.copied_to") + " " + suffix)

    def copy_code_text(self, value: str):
        """
        Copy code block to clipboard

        :param value: block text
        """
        QApplication.clipboard().setText(value.strip())
        suffix = value[:20] + "..." if len(value) > 20 else value
        self.window.update_status(trans("clipboard.copied_to") + " " + suffix)

    def preview_code_text(self, value: str):
        """
        Copy code block to clipboard

        :param value: block text
        """
        self.window.core.plugins.get("cmd_code_interpreter").handle_html_output(value)

    def edit_item(self, item_id: int):
        """
        Edit ctx item

        :param item_id: Item id
        """
        item = self.window.core.ctx.get_item_by_id(item_id)
        if item is not None and item.meta is not None:
            input_text = item.input
            meta_id = item.meta.id

            # store edit id
            self.window.controller.ctx.edit_meta_id = meta_id
            self.window.controller.ctx.edit_item_id = item_id

            # send to input
            self.window.controller.chat.common.clear_input()
            self.window.controller.chat.common.append_to_input(input_text)

            # show update icons (hide send, show update i cancel)
            self.edit_show()

    def edit_show(self):
        """Show edit buttons"""
        self.window.ui.nodes['input.send_btn'].setVisible(False)
        self.window.ui.nodes['input.update_btn'].setVisible(True)
        self.window.ui.nodes['input.cancel_btn'].setVisible(True)

    def edit_hide(self):
        """Hide edit buttons"""
        self.window.ui.nodes['input.send_btn'].setVisible(True)
        self.window.ui.nodes['input.update_btn'].setVisible(False)
        self.window.ui.nodes['input.cancel_btn'].setVisible(False)

    def edit_submit(self):
        """Submit edit"""
        item_id = self.window.controller.ctx.edit_item_id
        meta_id = self.window.controller.ctx.edit_meta_id
        current_meta_id = self.window.core.ctx.get_current()
        if meta_id != current_meta_id:
            self.window.controller.ctx.select(meta_id)
        item = self.window.core.ctx.get_item_by_id(item_id)
        if item is not None:
            meta_id = item.meta.id
            self.window.core.ctx.remove_items_from(meta_id, item_id)
            model = self.window.core.config.get('model')
            self.window.core.ctx.set_model(model)
            data = {
                "ctx": item,
            }
            event = RenderEvent(RenderEvent.ACTION_EDIT_SUBMIT, data)
            self.window.dispatch(event)
            self.window.controller.ctx.edit_item_id = None
            self.window.controller.ctx.edit_meta_id = None
            mode = self.window.core.config.get('mode')
            self.window.controller.model.set(mode, model)
            self.window.controller.chat.input.send_input(force=True)
        self.edit_hide()

    def is_editing(self) -> bool:
        """
        Check if editing ctx item is in progress

        :return: True if editing
        """
        return self.window.controller.ctx.edit_item_id is not None

    def edit_cancel(self):
        """Cancel edit"""
        self.window.controller.chat.common.clear_input()
        self.window.controller.ctx.edit_item_id = None
        self.window.controller.ctx.edit_meta_id = None
        self.edit_hide()

    def replay_item(
            self,
            item_id: int,
            force: bool = False
    ):
        """
        Regenerate ctx item

        :param item_id: ctx item id
        :param force: Force regenerate
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='ctx.replay_item',
                id=item_id,
                msg=trans('ctx.replay.item.confirm'),
            )
            return

        item = self.window.core.ctx.get_item_by_id(item_id)
        if item is not None:
            input_text = item.input
            meta_id = item.meta.id
            model = self.window.core.config.get('model')
            self.window.core.ctx.set_model(model)
            self.window.core.ctx.remove_items_from(meta_id, item_id)
            data = {
                "ctx": item,
            }
            event = RenderEvent(RenderEvent.ACTION_REGEN_SUBMIT, data)
            self.window.dispatch(event)
            mode = self.window.core.config.get('mode')
            self.window.controller.model.set(mode, model)

            context = BridgeContext()
            context.ctx = item
            context.prompt = input_text
            event = KernelEvent(KernelEvent.INPUT_SYSTEM, {
                'context': context,
                'extra': {},
            })
            self.window.dispatch(event)

    def audio_read_item(self, item_id: int):
        """
        Read ctx item audio

        :param item_id: ctx item id
        """
        item = self.window.core.ctx.get_item_by_id(item_id)
        if item is not None:
            if self.audio_play_id is None or self.audio_play_id != item_id:
                self.window.controller.audio.stop_output()
                self.window.controller.audio.read_text(item.output)
                self.audio_play_id = item_id
            elif self.audio_play_id == item_id:
                if not self.window.controller.audio.is_playing():
                    self.window.controller.audio.read_text(item.output)
                else:
                    self.window.controller.audio.stop_output()
                    self.window.controller.audio.on_stop()
                    self.audio_play_id = None

    def join_item(
            self,
            item_id: int,
            force: bool = False
    ):
        """
        Join ctx items

        :param item_id: ctx item id
        :param force: Force join
        """
        if not force:
            self.window.ui.dialogs.confirm(
                type='ctx.join_item',
                id=item_id,
                msg=trans('ctx.join.item.confirm'),
            )
            return
        prev_item = self.window.core.ctx.get_previous_item(item_id)
        current_item = self.window.core.ctx.get_item_by_id(item_id)
        if prev_item is not None and current_item is not None:
            prev_item.output += "\n\n" + current_item.output
            self.window.core.ctx.update_item(prev_item)
            self.window.core.ctx.remove_item(current_item.id)
            self.window.controller.ctx.refresh()