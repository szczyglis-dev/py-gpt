#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.28 12:00:00                  #
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


class CtxList:
    def __init__(self, window=None):
        """
        Context list UI

        :param window: Window instance
        """
        self.window = window
        self.search_input = SearchInput(window)
        self._group_separators = False
        self._pinned_separators = False

    def setup(self) -> QWidget:
        """
        Setup list

        :return: QWidget
        """
        ctx_id = 'ctx.list'
        ui = self.window.ui
        nodes = ui.nodes
        models = ui.models

        widget = QWidget()
        widget.setContentsMargins(0, 0, 0, 0)

        new_btn = NewCtxButton(trans('ctx.new'), self.window)
        new_btn.setContentsMargins(0, 0, 0, 0)
        nodes['ctx.new'] = new_btn

        ctx_list = ContextList(self.window, ctx_id)
        ctx_list.selection_locked = self.window.controller.ctx.context_change_locked
        nodes[ctx_id] = ctx_list

        nodes['ctx.label'] = TitleLabel(trans("ctx.list.label"))
        search_input = self.search_input.setup()

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(new_btn)
        layout.addWidget(search_input)
        layout.addWidget(ctx_list)

        model = self.create_model(self.window)
        models[ctx_id] = model
        ctx_list.setModel(model)

        # Expose force scroll on model as a thin proxy to the view method for external callers
        try:
            def _model_force_scroll_to_current(*args, **kwargs):
                return ctx_list.force_scroll_to_current(*args, **kwargs)
            setattr(model, "force_scroll_to_current", _model_force_scroll_to_current)
        except Exception:
            pass

        ctx = self.window.controller.ctx
        ctx_list.selectionModel().selectionChanged.connect(lambda *_: ctx.selection_change())

        self._group_separators = self.window.core.config.get("ctx.records.groups.separators")
        self._pinned_separators = self.window.core.config.get("ctx.records.pinned.separators")

        return widget

    def create_model(self, parent) -> QStandardItemModel:
        """
        Create model

        :param parent: parent widget
        :return: QStandardItemModel
        """
        return QStandardItemModel(0, 1, parent)

    def update(self, id, data, expand: bool = True):
        """
        Update ctx list

        :param id: ID of the list
        :param data: Data to update
        :param expand: Whether to expand groups
        """
        node = self.window.ui.nodes[id]
        node.backup_selection()

        self._group_separators = self.window.core.config.get("ctx.records.groups.separators")
        self._pinned_separators = self.window.core.config.get("ctx.records.pinned.separators")

        model = self.window.ui.models.get(id)
        if model is not None:
            node.setUpdatesEnabled(False)
            try:
                model.clear()
                if self.window.core.config.get("ctx.records.folders.top"):
                    self.update_items_pinned(id, data)
                    self.update_groups(id, data, expand=expand)
                    self.update_items(id, data)
                else:
                    self.update_items_pinned(id, data)
                    self.update_items(id, data)
                    self.update_groups(id, data, expand=expand)

                # APPLY PENDING SCROLL BEFORE RE-ENABLING UPDATES (prevents top flicker)
                try:
                    node.apply_pending_scroll()
                    node.clear_pending_scroll()
                except Exception:
                    pass
            finally:
                node.setUpdatesEnabled(True)

    def _find_first_group_row(self, model) -> int:
        """Find the row index of the first GroupItem; return -1 if none."""
        for r in range(model.rowCount()):
            it = model.item(r)
            if isinstance(it, GroupItem):
                return r
        return -1

    def append_unpaginated(self, id: str, data: dict, add_ids: list[int]):
        """
        Append more ungrouped and not pinned items without rebuilding the model.
        Keeps scroll position perfectly stable.
        """
        if not add_ids:
            return
        node = self.window.ui.nodes[id]
        model = self.window.ui.models[id]

        folders_top = bool(self.window.core.config.get("ctx.records.folders.top"))
        # decide insertion point: at the end, or just before the first group row
        insert_pos = model.rowCount()
        if not folders_top:
            grp_idx = self._find_first_group_row(model)
            insert_pos = grp_idx if grp_idx >= 0 else model.rowCount()

        # find last dt of existing ungrouped area before insertion point (for date sections)
        last_dt_str = None
        for r in range(insert_pos - 1, -1, -1):
            it = model.item(r)
            if isinstance(it, Item):
                data_role = it.data(QtCore.Qt.ItemDataRole.UserRole) or {}
                if not data_role.get("in_group", False) and not data_role.get("is_important", False):
                    last_dt_str = getattr(it, "dt", None)
                    break
            elif isinstance(it, GroupItem):
                break  # hit groups boundary going upwards
            else:
                # SectionItem or others – skip
                continue

        node.setUpdatesEnabled(False)
        try:
            # append strictly in the order provided by add_ids (older first)
            for mid in add_ids:
                meta = data.get(mid)
                if meta is None:
                    continue
                item = self.build_item(mid, meta, is_group=False)

                # Optional date sections (same logic as in update_items)
                if self._group_separators and (not item.isPinned or self._pinned_separators):
                    if last_dt_str is None or last_dt_str != item.dt:
                        section = self.build_date_section(item.dt, group=False)
                        if section:
                            model.insertRow(insert_pos, section)
                            insert_pos += 1
                        last_dt_str = item.dt

                model.insertRow(insert_pos, item)
                insert_pos += 1
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
        model = self.window.ui.models[id]
        for meta_id, meta in data.items():
            gid = meta.group_id
            if (gid is None or gid == 0) and not meta.important:
                item = self.build_item(meta_id, meta, is_group=False)
                if self._group_separators and (not item.isPinned or self._pinned_separators):
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

        for meta_id, meta in data.items():
            gid = meta.group_id
            if (gid is None or gid == 0) and meta.important:
                item = self.build_item(meta_id, meta, is_group=False)
                if self._group_separators and self._pinned_separators:
                    if i == 0 or last_dt_str != item.dt:
                        section = self.build_date_section(item.dt, group=False)
                        if section:
                            model.appendRow(section)
                    last_dt_str = item.dt
                model.appendRow(item)
                i += 1

    def update_groups(self, id, data, expand: bool = True):
        """
        Update groups

        :param id: ID of the list
        :param data: Data to update
        :param expand: Whether to expand groups
        """
        model = self.window.ui.models[id]
        groups = self.window.core.ctx.get_groups()
        search_string = self.window.core.ctx.get_search_string()
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

            # Display only the group name; the counter is drawn by delegate on the right
            is_attachment = group.has_additional_ctx()
            group_name = group.name
            group_item = GroupItem(folder_icon, group_name, group.id)
            group_item.hasAttachments = is_attachment

            # Provide all metadata required by the delegate
            custom_data = {
                "is_group": True,
                "is_attachment": is_attachment,
                "count": c,
            }

            if is_attachment:
                files = group.get_attachment_names()
                files_str = ", ".join(files)
                if len(files_str) > 40:
                    files_str = files_str[:40] + '...'
                tooltip_str = f"{trans('attachments.ctx.tooltip.list').format(num=len(files))}: {files_str}"
                group_item.setToolTip(tooltip_str)

            group_item.setData(custom_data, QtCore.Qt.ItemDataRole.UserRole)

            i = 0
            for meta_id, meta in items_in_group:
                item = self.build_item(meta_id, meta, is_group=True)
                if self._group_separators and (not item.isPinned or self._pinned_separators):
                    if i == 0 or last_dt_str != item.dt:
                        section = self.build_date_section(item.dt, group=True)
                        if section:
                            group_item.appendRow(section)
                    last_dt_str = item.dt
                group_item.appendRow(item)
                i += 1

            model.appendRow(group_item)

            # Always reflect persisted expansion state so groups stay open after actions
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
        append_dt = False if (is_group and self._group_separators) or ((not is_group) and self._group_separators) else append_dt

        dt = self.convert_date(data.updated)
        date_time_str = datetime.fromtimestamp(data.updated).strftime("%Y-%m-%d %H:%M")
        title = data.name
        if len(title) > 80:
            title = title[:80] + '...'
        clean_title = title.replace("\n", "")

        name = f"{clean_title} ({dt})" if append_dt else clean_title
        mode_str = f" ({trans('mode.' + data.last_mode)})" if data.last_mode is not None else ""
        tooltip_text = f"{date_time_str}: {data.name}{mode_str} #{id}"

        if is_attachment:
            files = data.get_attachment_names()
            files_str = ", ".join(files)
            if len(files_str) > 40:
                files_str = files_str[:40] + '...'
            tooltip_text += f"\n{trans('attachments.ctx.tooltip.list').format(num=len(files))}: {files_str}"

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
        return SectionItem(dt, group=group)

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