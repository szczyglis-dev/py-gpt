#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.02.26 23:00:00                  #
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
        self.window.ui.nodes[id].backup_selection()
        self.window.ui.models[id].removeRows(0, self.window.ui.models[id].rowCount())

        if self.window.core.config.get("ctx.records.folders.top"):
            self.update_items_pinned(id, data)
            self.update_groups(id, data)
            self.update_items(id, data)
        else:
            self.update_items_pinned(id, data)
            self.update_items(id, data)
            self.update_groups(id, data)

    def update_items(self, id, data):
        """
        Update items

        :param id: ID of the list
        :param data: Data to update
        """
        i = 0
        last_dt_str = None
        separators = self.window.core.config.get("ctx.records.separators")
        pinned_separators = self.window.core.config.get("ctx.records.pinned.separators")
        for meta_id in data:
            if data[meta_id].group_id is None or data[meta_id].group_id == 0:
                if data[meta_id].important:
                    continue
                item = self.build_item(meta_id, data[meta_id], is_group=False)
                if separators:
                    if not item.isPinned or pinned_separators:
                        if i == 0 or last_dt_str != item.dt:
                            section = self.build_date_section(item.dt, group=False)
                            if section:
                                self.window.ui.models[id].appendRow(section)
                        last_dt_str = item.dt
                self.window.ui.models[id].appendRow(item)
                i += 1

    def update_items_pinned(self, id, data):
        """
        Update items pinned

        :param id: ID of the list
        :param data: Data to update
        """
        i = 0
        last_dt_str = None
        separators = self.window.core.config.get("ctx.records.separators")
        pinned_separators = self.window.core.config.get("ctx.records.pinned.separators")
        for meta_id in data:
            if data[meta_id].group_id is None or data[meta_id].group_id == 0:
                if not data[meta_id].important:
                    continue
                item = self.build_item(meta_id, data[meta_id], is_group=False)
                if separators:
                    if pinned_separators:
                        if i == 0 or last_dt_str != item.dt:
                            section = self.build_date_section(item.dt, group=False)
                            if section:
                                self.window.ui.models[id].appendRow(section)
                        last_dt_str = item.dt
                self.window.ui.models[id].appendRow(item)
                i += 1

    def update_groups(self, id, data):
        """
        Update groups

        :param id: ID of the list
        :param data: Data to update
        """
        groups = self.window.core.ctx.get_groups()  # get groups
        for group_id in groups:
            last_dt_str = None
            group = groups[group_id]
            c = self.count_in_group(group.id, data)
            if (c == 0 and self.window.core.ctx.get_search_string() is not None
                    and self.window.core.ctx.get_search_string() != ""):
                continue  # skip empty groups when searching

            suffix = ""
            if c > 0:
                suffix = " (" + str(c) + ")"
            is_attachment = group.has_additional_ctx()
            group_name = group.name + suffix
            group_item = GroupItem(QIcon(":/icons/folder_filled.svg"), group_name, group.id)
            group_item.hasAttachments = group.has_additional_ctx()
            custom_data = {
                "is_group": True,
                "is_attachment": is_attachment,
            }
            if is_attachment:
                files = group.get_attachment_names()
                num = len(files)
                files_str = ", ".join(files)
                if len(files_str) > 40:
                    files_str = files_str[:40] + '...'
                tooltip_str = trans("attachments.ctx.tooltip.list").format(num=num) + ": " + files_str
                group_item.setToolTip(tooltip_str)

            group_item.setData(custom_data, QtCore.Qt.ItemDataRole.UserRole)

            i = 0
            for meta_id in data:
                if data[meta_id].group_id != group.id:
                    continue  # skip not in group
                item = self.build_item(meta_id, data[meta_id], is_group=True)
                if self.window.core.config.get("ctx.records.groups.separators"):
                    if not item.isPinned or self.window.core.config.get("ctx.records.pinned.separators"):
                        if i == 0 or last_dt_str != item.dt:
                            section = self.build_date_section(item.dt, group=True)
                            if section:
                                group_item.appendRow(section)
                        last_dt_str = item.dt
                group_item.appendRow(item)
                i += 1

            self.window.ui.models[id].appendRow(group_item)

            # expand group
            if group.id in self.window.ui.nodes[id].expanded_items:
                self.window.ui.nodes[id].setExpanded(group_item.index(), True)
            else:
                self.window.ui.nodes[id].setExpanded(group_item.index(), False)

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
        is_important = False
        is_attachment = False
        in_group = False
        label = data.label
        if data.important:
            is_important = True
        if data.has_additional_ctx():
            is_attachment = True
        if data.group:
            in_group = True

        if is_group:
            if self.window.core.config.get("ctx.records.groups.separators"):
                append_dt = False
        else:
            if self.window.core.config.get("ctx.records.separators"):
                append_dt = False
        dt = self.convert_date(data.updated)
        date_time_str = datetime.fromtimestamp(data.updated).strftime("%Y-%m-%d %H:%M")
        title = data.name
        # truncate to max 40 chars
        if len(title) > 80:
            title = title[:80] + '...'

        # append date suffix to title
        if append_dt:
            name = title.replace("\n", "") + ' (' + dt + ')'
        else:
            name = title.replace("\n", "")

        mode_str = ''
        if data.last_mode is not None:
            mode_str = " ({})".format(trans('mode.' + data.last_mode))
        tooltip_text = "{}: {}{} #{}".format(
            date_time_str,
            data.name,
            mode_str,
            id,
        )

        # append attachments to tooltip
        if is_attachment:
            files = data.get_attachment_names()
            num = len(files)
            files_str = ", ".join(files)
            if len(files_str) > 40:
                files_str = files_str[:40] + '...'
            tooltip_str = trans("attachments.ctx.tooltip.list").format(num=num) + ": " + files_str
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
        # item.setToolTip(dt)
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
