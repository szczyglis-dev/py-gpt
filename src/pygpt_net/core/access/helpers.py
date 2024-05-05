#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.05.05 12:00:00                  #
# ================================================== #

from datetime import datetime, timedelta

from pygpt_net.utils import trans


class Helpers:
    def __init__(self, window=None):
        """
        Helpers - voice get data

        :param window: Window instance
        """
        self.window = window

    def get_status(self) -> str:
        """
        Get the current application status

        :return: status, text to read
        """
        ctx = ""
        total = self.window.core.ctx.count_meta()
        meta = self.window.core.ctx.get_current_meta()
        mode = trans("mode." + self.window.core.config.get("mode"))
        mode += " " + self.get_selected_model()
        mode += " " + self.get_selected_preset()
        tab = self.window.controller.ui.get_current_tab_name()
        last = ""
        msg = ""
        if meta is not None:
            ctx = meta.name
            last = self.convert_date(meta.updated)
        try:
            msg = trans("event.audio.app.status").format(
                mode=mode,
                tab=tab,
                ctx=ctx,
                last=last,
                total=total,
            )
        except Exception as e:
            pass
        return msg

    def get_current_ctx(self) -> str:
        """
        Get current context

        :return: text to read
        """
        meta = self.window.core.ctx.get_current_meta()
        if meta is not None:
            name = meta.name
            updated = self.convert_date(meta.updated)
            try:
                msg = trans("event.audio.ctx.current").format(
                    ctx=name,
                    last=updated,
                )
            except Exception as e:
                msg = ""
            return msg
        return ""

    def get_selected_ctx(self) -> str:
        """
        Get current context

        :return: text to read
        """
        meta = self.window.core.ctx.get_current_meta()
        if meta is not None:
            name = meta.name
            updated = self.convert_date(meta.updated)
            try:
                msg = trans("event.audio.ctx.selected").format(
                    ctx=name,
                    last=updated,
                )
            except Exception as e:
                msg = ""
            return msg
        return ""

    def get_selected_tab(self) -> str:
        """
        Get current tab

        :return: text to read
        """
        msg = ""
        tab = self.window.controller.ui.get_current_tab_name()
        try:
            msg = trans("event.audio.tab.switch").format(
                tab=tab,
            )
        except Exception as e:
            pass
        return msg

    def get_selected_mode(self) -> str:
        """
        Get current mode

        :return: text to read
        """
        mode = self.window.core.config.get("mode")
        if mode is None:
            return ""
        try:
            msg = trans("event.audio.mode.selected").format(
                mode=trans("mode." + mode),
            )
        except Exception as e:
            msg = ""
        return msg

    def get_selected_model(self) -> str:
        """
        Get current model

        :return: text to read
        """
        model = self.window.core.config.get("model")
        if model is None:
            return ""
        try:
            msg = trans("event.audio.model.selected").format(
                model=model,
            )
        except Exception as e:
            msg = ""
        return msg

    def get_selected_preset(self) -> str:
        """
        Get current preset

        :return: text to read
        """
        preset_id = self.window.core.config.get("preset")
        if preset_id is None:
            return ""
        mode = self.window.core.config.get("mode")
        preset = self.window.core.presets.get_by_id(mode, preset_id)
        if preset is None:
            return ""
        try:
            msg = trans("event.audio.preset.selected").format(
                preset=preset.name,
            )
        except Exception as e:
            msg = ""
        return msg

    def get_last_ctx_item(self) -> str:
        """
        Get last context item

        :return: text to read
        """
        text = ""
        item = self.window.core.ctx.get_last()
        if item is not None:
            try:
                text = trans("event.audio.ctx.last").format(
                    input=item.input,
                    output=item.output,
                )
            except Exception as e:
                pass
        return text

    def get_all_ctx_items(self) -> str:
        """
        Get all context items

        :return: text to read
        """
        text = ""
        entries = []
        items = self.window.core.ctx.get_all_items(ignore_first=False)
        for item in items:
            try:
                entries.append(trans("event.audio.ctx.last").format(
                    input=item.input,
                    output=item.output,
                ))
            except Exception as e:
                pass
        if len(entries) > 0:
            text = "\n".join(entries)
        return text

    def convert_date(self, timestamp: int) -> str:
        """
        Convert timestamp to human readable format

        :param timestamp: timestamp
        :return: string
        """
        today = datetime.today().date()
        yesterday = today - timedelta(days=1)
        date = datetime.fromtimestamp(timestamp).date()
        hour_min = datetime.fromtimestamp(timestamp).strftime("%H:%M")

        days_ago = (today - date).days
        weeks_ago = days_ago // 7

        if date == today:
            return trans('dt.today') + " " + hour_min
        elif date == yesterday:
            return trans('dt.yesterday') + " " + hour_min
        elif weeks_ago == 1:
            return trans('dt.week')
        elif 1 < weeks_ago < 4:
            return f"{weeks_ago} " + trans('dt.weeks')
        elif days_ago < 30:
            return f"{days_ago} " + trans('dt.days_ago')
        elif 30 <= days_ago < 32:
            return trans('dt.month')
        else:
            return date.strftime("%Y-%m-%d")