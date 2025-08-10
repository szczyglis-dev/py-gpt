#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.11 00:00:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtGui import QStandardItemModel, QIcon
from PySide6.QtWidgets import QVBoxLayout, QWidget
from datetime import datetime, timedelta

from pygpt_net.item.ctx import CtxMeta
from pygpt_net.ui.layout.ctx.search_input import SearchInput
from pygpt_net.ui.widget.element.button import NewCtxButton
from pygpt_net.ui.widget.element.labels import TitleLabel
from pygpt_net.ui.widget.lists.context import ContextList, Item, GroupItem, SectionItem
from pygpt_net.utils import trans
import pygpt_net.icons_rc


class CtxList:
    def __init__(self, window=None):
        """
        Context list UI

        :param window: Window instance
        """
        self.window = window
        self.search_input = SearchInput(window)

    def setup(self) -> QWidget:
        """
        Setup list

        :return: QWidget
        """
        id = 'ctx.list'
        self.window.ui.nodes['ctx.new'] = NewCtxButton(trans('ctx.new'), self.window)
        self.window.ui.nodes[id] = ContextList(self.window, id)
        self.window.ui.nodes[id].selection_locked = self.window.controller.ctx.context_change_locked
        self.window.ui.nodes['ctx.label'] = TitleLabel(trans("ctx.list.label"))
        self.window.ui.nodes['ctx.new'].setContentsMargins(0,0,0,0)
        search_input = self.search_input.setup()

        layout = QVBoxLayout()
        layout.addWidget(self.window.ui.nodes['ctx.new'])
        layout.addWidget(search_input)
        layout.addWidget(self.window.ui.nodes[id])
        layout.setContentsMargins(0, 0, 0, 0)

        self.window.ui.models[id] = self.create_model(self.window)
        self.window.ui.nodes[id].setModel(self.window.ui.models[id])
        self.window.ui.nodes[id].selectionModel().selectionChanged.connect(
            lambda: self.window.controller.ctx.selection_change()
        )
        widget = QWidget()
        widget.setLayout(layout)
        widget.setContentsMargins(0, 0, 0, 0)

        return widget

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        return QStandardItemModel(0, 1, parent)

    def update(self, id, data):
        """
        Update ctx list

        :param id: ID of the list
        :param data: Data to update
        """
        node = self.window.ui.nodes[id]
        node.backup_selection()

        model = self.window.ui.models.get(id)
        if model is not None:
            node.setUpdatesEnabled(False)
            try:
                model.clear()
                if self.window.core.config.get("ctx.records.folders.top"):
                    self.update_items_pinned(id, data)
                    self.update_groups(id, data)
                    self.update_items(id, data)
                else:
                    self.update_items_pinned(id, data)
                    self.update_items(id, data)
                    self.update_groups(id, data)
            finally:
                node.setUpdatesEnabled(True)

    def update_items(self, id, data):
        """
        Update items

        :param id: ID of the list
        :param data: Data to update
        """
        i = 0
        last_dt_str = None
        config = self.window.core.config
        separators = config.get("ctx.records.separators")
        pinned_separators = config.get("ctx.records.pinned.separators")
        model = self.window.ui.models[id]

        for meta_id, meta in data.items():
            gid = meta.group_id
            if (gid is None or gid == 0) and not meta.important:
                item = self.build_item(meta_id, meta, is_group=False)
                if separators and (not item.isPinned or pinned_separators):
                    if i == 0 or last_dt_str != item.dt:
                        section = self.build_date_section(item.dt, group=False)
                        if section:
                            model.appendRow(section)
                    last_dt_str = item.dt
                model.appendRow(item)
                i += 1

    def update_items_pinned(self, id, data):
        """
        Update items pinned

        :param id: ID of the list
        :param data: Data to update
        """
        i = 0
        last_dt_str = None
        model = self.window.ui.models[id]
        config = self.window.core.config
        separators = config.get("ctx.records.separators")
        pinned_separators = config.get("ctx.records.pinned.separators")

        for meta_id, meta in data.items():
            gid = meta.group_id
            if (gid is None or gid == 0) and meta.important:
                item = self.build_item(meta_id, meta, is_group=False)
                if separators and pinned_separators:
                    if i == 0 or last_dt_str != item.dt:
                        section = self.build_date_section(item.dt, group=False)
                        if section:
                            model.appendRow(section)
                    last_dt_str = item.dt
                model.appendRow(item)
                i += 1

    def update_groups(self, id, data):
        """
        Update groups

        :param id: ID of the list
        :param data: Data to update
        """
        model = self.window.ui.models[id]
        groups = self.window.core.ctx.get_groups()
        search_string = self.window.core.ctx.get_search_string()
        config = self.window.core.config
        is_group_separators = config.get("ctx.records.groups.separators")
        is_pinned_separators = config.get("ctx.records.pinned.separators")

        grouped = {}
        for meta_id, meta in data.items():
            gid = meta.group_id
            if gid is not None and gid != 0:
                grouped.setdefault(gid, []).append((meta_id, meta))

        folder_icon = getattr(self, "_folder_icon", None)
        if folder_icon is None:
            from PySide6.QtGui import QIcon
            folder_icon = self._folder_icon = QIcon(":/icons/folder_filled.svg")

        node = self.window.ui.nodes[id]

        for group_id in groups:
            last_dt_str = None
            group = groups[group_id]
            items_in_group = grouped.get(group.id, [])
            c = len(items_in_group)
            if c == 0 and search_string:
                continue

            suffix = f" ({c})" if c > 0 else ""
            is_attachment = group.has_additional_ctx()
            group_name = group.name + suffix
            group_item = GroupItem(folder_icon, group_name, group.id)
            group_item.hasAttachments = is_attachment
            custom_data = {
                "is_group": True,
                "is_attachment": is_attachment,
            }

            if is_attachment:
                files = group.get_attachment_names()
                files_str = ", ".join(files)
                if len(files_str) > 40:
                    files_str = files_str[:40] + '...'
                tooltip_str = trans("attachments.ctx.tooltip.list").format(num=len(files)) + ": " + files_str
                group_item.setToolTip(tooltip_str)

            group_item.setData(custom_data, QtCore.Qt.ItemDataRole.UserRole)

            i = 0
            for meta_id, meta in items_in_group:
                item = self.build_item(meta_id, meta, is_group=True)
                if is_group_separators and (not item.isPinned or is_pinned_separators):
                    if i == 0 or last_dt_str != item.dt:
                        section = self.build_date_section(item.dt, group=True)
                        if section:
                            group_item.appendRow(section)
                    last_dt_str = item.dt
                group_item.appendRow(item)
                i += 1

            model.appendRow(group_item)

            desired = group.id in node.expanded_items
            idx = group_item.index()
            if node.isExpanded(idx) != desired:
                node.setExpanded(idx, desired)

    def count_in_group(self, group_id: int, data: dict) -> int:
        """
        Count items in group

        :param group_id: group id
        :param data: context meta data
        :return: int
        """
        count = 0
        for meta_id in data:
            if data[meta_id].group_id == group_id:
                count += 1
        return count

    def build_item(self, id: int, data: CtxMeta, is_group: bool = False) -> Item:
        """
        Build item for list (child)

        :param id: context meta id
        :param data: context meta item
        :param is_group: is group
        :return: Item
        """
        append_dt = True
        label = data.label
        is_important = data.important
        is_attachment = data.has_additional_ctx()
        in_group = bool(data.group)

        if is_group:
            if self.window.core.config.get("ctx.records.groups.separators"):
                append_dt = False
        else:
            if self.window.core.config.get("ctx.records.separators"):
                append_dt = False

        dt = self.convert_date(data.updated)
        date_time_str = datetime.fromtimestamp(data.updated).strftime("%Y-%m-%d %H:%M")
        title = data.name
        if len(title) > 80:
            title = title[:80] + '...'
        clean_title = title.replace("\n", "")

        if append_dt:
            name = f"{clean_title} ({dt})"
        else:
            name = clean_title

        mode_str = ''
        if data.last_mode is not None:
            mode_str = f" ({trans('mode.' + data.last_mode)})"

        tooltip_text = f"{date_time_str}: {data.name}{mode_str} #{id}"

        if is_attachment:
            files = data.get_attachment_names()
            files_str = ", ".join(files)
            if len(files_str) > 40:
                files_str = files_str[:40] + '...'
            tooltip_str = trans("attachments.ctx.tooltip.list").format(num=len(files)) + ": " + files_str
            tooltip_text += "\n" + tooltip_str

        item = Item(name, id)
        item.id = id
        item.dt = dt
        item.isPinned = data.important
        item.setData(tooltip_text, QtCore.Qt.ToolTipRole)

        custom_data = {
            "label": label,
            "is_important": is_important,
            "is_attachment": is_attachment,
            "in_group": in_group,
        }
        item.setData(custom_data, QtCore.Qt.ItemDataRole.UserRole)
        item.setData(name)
        return item

    def build_date_section(self, dt: str, group: bool = False) -> SectionItem:
        """
        Build date section

        :param dt: date section string
        :param group: is group
        :return: SectionItem
        """
        item = SectionItem(dt, group=group)
        return item

    def convert_date(self, timestamp: int) -> str:
        """
        Convert timestamp to human readable format

        :param timestamp: timestamp
        :return: string
        """
        today = datetime.today().date()
        yesterday = today - timedelta(days=1)
        date = datetime.fromtimestamp(timestamp).date()

        days_ago = (today - date).days
        weeks_ago = days_ago // 7

        if date == today:
            return trans('dt.today')
        elif date == yesterday:
            return trans('dt.yesterday')
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
