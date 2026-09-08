#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.08 22:30:00                  #
# ================================================== #

from PySide6 import QtCore
from PySide6.QtGui import QStandardItemModel, QIcon
from PySide6.QtWidgets import QVBoxLayout, QWidget
from datetime import datetime, timedelta

from pygpt_net.item.ctx import CtxMeta, get_additional_ctx_display_names
from pygpt_net.ui.layout.ctx.search_input import SearchInput
from pygpt_net.ui.widget.element.button import NewCtxButton
from pygpt_net.ui.widget.element.labels import TitleLabel
from pygpt_net.ui.widget.lists.context import ContextList, Item, GroupItem, SectionItem, ShowMoreItem
from pygpt_net.utils import trans


# Context-list presentation limits. Project contexts are still loaded from the
# provider in full; these constants only cap how many rows are rendered until
# the user explicitly expands the corresponding list.
MAX_PROJECTS_DISPLAY = 10
MAX_PROJECT_CONTEXTS_DISPLAY = 10


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
        self._list_section_top_spacing = 12
        self._list_section_row_height = 28
        self._recent_section_inline_date = True

        # Cached icons for closed/open folder states
        self._folder_icon = None
        self._folder_open_icon = None

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

        # Switch group folder icon on expand/collapse
        try:
            ctx_list.expanded.connect(self.on_group_expanded)
            ctx_list.collapsed.connect(self.on_group_collapsed)
        except Exception:
            # View might not expose expanded/collapsed; ignore if not supported
            pass

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

                # Restore top-level section collapse state after every model
                # rebuild. Missing config means all sections stay expanded.
                node.apply_section_visibility()

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

            # Newly appended Recent rows inherit the persisted visibility
            # immediately when the section is collapsed.
            node.apply_section_visibility()
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
        recent_total = None
        for meta_id, meta in data.items():
            gid = meta.group_id
            if (gid is None or gid == 0) and not meta.important:
                item = self.build_item(meta_id, meta, is_group=False)
                inline_first_date = (
                    i == 0
                    and self._recent_section_inline_date
                    and self._group_separators
                    and (not item.isPinned or self._pinned_separators)
                )
                if i == 0:
                    recent_total = self._count_recent_total()
                    self.append_list_section(
                        model,
                        'ctx.list.section.recent',
                        right_text=item.dt if inline_first_date else None,
                        action='new_context',
                        section_count=recent_total,
                    )
                if self._group_separators and (not item.isPinned or self._pinned_separators):
                    if not inline_first_date and (i == 0 or last_dt_str != item.dt):
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
        pinned_total = sum(
            1
            for meta in data.values()
            if (meta.group_id is None or meta.group_id == 0) and meta.important
        )

        for meta_id, meta in data.items():
            gid = meta.group_id
            if (gid is None or gid == 0) and meta.important:
                item = self.build_item(meta_id, meta, is_group=False)
                if i == 0:
                    self.append_list_section(
                        model,
                        'ctx.list.section.pinned',
                        section_count=pinned_total,
                    )
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

        # Keep contexts inside every project newest-first. ``load_meta()``
        # intentionally loads grouped contexts without pagination, but pinned
        # and grouped result sets are merged before reaching the UI, so sort
        # explicitly here instead of depending on dict insertion order.
        for group_id in grouped:
            grouped[group_id].sort(
                key=lambda entry: (
                    int(getattr(entry[1], 'updated', 0) or 0),
                    int(entry[0] or 0),
                ),
                reverse=True,
            )

        # Projects are ordered by the newest updated context they contain.
        # Empty projects have no context activity and therefore stay at the end;
        # name/id provide a deterministic order for ties.
        project_rows = []
        for group_id in groups:
            group = groups[group_id]
            items_in_group = grouped.get(group.id, [])
            if not items_in_group and search_string:
                continue
            latest_ctx_updated = max(
                (int(getattr(meta, 'updated', 0) or 0) for _, meta in items_in_group),
                default=0,
            )
            project_rows.append((group, items_in_group, latest_ctx_updated))

        project_rows.sort(
            key=lambda row: (
                -row[2],
                str(row[0].name or '').casefold(),
                int(row[0].id or 0),
            )
        )
        project_total = len(project_rows)

        # Ensure icons for closed/open folder states are loaded once
        if getattr(self, "_folder_icon", None) is None:
            self._folder_icon = QIcon(":/icons/folder.svg")
        if getattr(self, "_folder_open_icon", None) is None:
            self._folder_open_icon = QIcon(":/icons/folder_open.svg")

        node = self.window.ui.nodes[id]
        section_added = False

        # If the active context belongs to a project which would otherwise be
        # outside the visual project limit, reveal all projects so the current
        # row never disappears from the left-hand navigation.
        current_group_id = None
        try:
            current_meta = self.window.core.ctx.get_current_meta()
            if current_meta is not None and current_meta.group_id:
                current_group_id = int(current_meta.group_id)
        except Exception:
            current_group_id = None

        max_projects = max(0, int(MAX_PROJECTS_DISPLAY or 0))
        if (
                max_projects > 0
                and not node.show_all_projects
                and not node.projects_limit_collapsed_by_user
                and current_group_id is not None
                and current_group_id not in [row[0].id for row in project_rows[:max_projects]]
        ):
            node.show_all_projects = True

        visible_project_rows = project_rows
        if max_projects > 0 and not node.show_all_projects:
            visible_project_rows = project_rows[:max_projects]

        for group, items_in_group, _latest_ctx_updated in visible_project_rows:
            last_dt_str = None
            c = len(items_in_group)

            if not section_added:
                self.append_list_section(
                    model,
                    'ctx.list.section.projects',
                    action='new_project',
                    section_count=project_total,
                )
                section_added = True

            # Project attachment marker is meaningful only when project-wide
            # sharing is enabled. With per-chat attachments, the project row
            # must stay clean even if old shared metadata still exists.
            project_share = bool(
                self.window.core.config.get("ctx.attachment.project_share", False)
            )
            is_attachment = project_share and group.has_additional_ctx()
            group_name = group.name
            group_item = GroupItem(self._folder_icon, group_name, group.id)
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

            max_contexts = max(0, int(MAX_PROJECT_CONTEXTS_DISPLAY or 0))

            # As with projects, never hide the active context behind the visual
            # limiter. This matters after restoring an older context directly
            # from config/history.
            if (
                    max_contexts > 0
                    and group.id not in node.show_all_project_contexts
                    and group.id not in node.project_contexts_limit_collapsed_by_user
                    and current_group_id == int(group.id)
            ):
                try:
                    current_id = int(self.window.core.ctx.get_current())
                except Exception:
                    current_id = None
                if current_id is not None and current_id not in [entry[0] for entry in items_in_group[:max_contexts]]:
                    node.show_all_project_contexts.add(group.id)

            visible_items = items_in_group
            if max_contexts > 0 and group.id not in node.show_all_project_contexts:
                visible_items = items_in_group[:max_contexts]

            i = 0
            for meta_id, meta in visible_items:
                item = self.build_item(meta_id, meta, is_group=True)
                if self._group_separators and (not item.isPinned or self._pinned_separators):
                    if i == 0 or last_dt_str != item.dt:
                        section = self.build_date_section(item.dt, group=True)
                        if section:
                            group_item.appendRow(section)
                    last_dt_str = item.dt
                group_item.appendRow(item)
                i += 1

            hidden_contexts = c - len(visible_items)
            if hidden_contexts > 0:
                group_item.appendRow(ShowMoreItem(
                    trans('ctx.list.show_more').format(count=hidden_contexts),
                    scope=ShowMoreItem.PROJECT_CONTEXTS,
                    group_id=group.id,
                    remaining_count=hidden_contexts,
                ))
            elif max_contexts > 0 and c > max_contexts and group.id in node.show_all_project_contexts:
                group_item.appendRow(ShowMoreItem(
                    trans('ctx.list.less'),
                    scope=ShowMoreItem.PROJECT_CONTEXTS,
                    group_id=group.id,
                    collapse=True,
                ))

            model.appendRow(group_item)

            # Always reflect persisted expansion state so groups stay open after actions
            desired = group.id in node.expanded_items
            idx = group_item.index()
            if node.isExpanded(idx) != desired:
                node.setExpanded(idx, desired)
            self._set_group_icon_for_index(idx, desired)

        hidden_projects = project_total - len(visible_project_rows)
        if hidden_projects > 0:
            if not section_added:
                self.append_list_section(
                    model,
                    'ctx.list.section.projects',
                    action='new_project',
                    section_count=project_total,
                )
                section_added = True
            model.appendRow(ShowMoreItem(
                trans('ctx.list.show_more').format(count=hidden_projects),
                scope=ShowMoreItem.PROJECTS,
                remaining_count=hidden_projects,
            ))
        elif max_projects > 0 and project_total > max_projects and node.show_all_projects:
            model.appendRow(ShowMoreItem(
                trans('ctx.list.less'),
                scope=ShowMoreItem.PROJECTS,
                collapse=True,
            ))

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

    def _count_recent_total(self) -> int:
        """
        Count all matching ungrouped, non-pinned contexts in the provider.

        Recent is paginated in the UI, so counting rows already present in the
        model would only return the currently loaded page(s). Use the provider
        count API with the same active search/filter criteria instead.

        :return: total number of matching Recent contexts
        """
        ctx = self.window.core.ctx
        filters = ctx.get_parsed_filters()
        filters['is_important'] = {"mode": "=", "value": 0}
        filters['group_id'] = {"mode": "NULL_OR_ZERO", "value": 0}

        try:
            provider = ctx.get_provider()
            return int(provider.count_meta(
                search_string=ctx.get_search_string(),
                filters=filters,
                search_content=ctx.is_search_content(),
            ))
        except Exception:
            # Defensive fallback for legacy/custom providers which do not
            # implement count_meta yet. This preserves correct UI operation;
            # the standard SQLite provider uses an efficient COUNT query.
            count = 0
            try:
                for meta in ctx.get_meta().values():
                    gid = meta.group_id
                    if (gid is None or gid == 0) and not meta.important:
                        count += 1
            except Exception:
                pass
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
        in_group = bool(data.group)
        project_share = bool(
            self.window.core.config.get("ctx.attachment.project_share", False)
        )
        if in_group and not project_share:
            is_attachment = bool(data.additional_ctx)
        else:
            is_attachment = data.has_additional_ctx()
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
            if in_group and not project_share:
                files = get_additional_ctx_display_names(data.additional_ctx or [])
            else:
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

    def append_list_section(
        self,
        model: QStandardItemModel,
        translation_key: str,
        right_text: str | None = None,
        action: str | None = None,
        section_count: int | None = None,
    ):
        """
        Append a top-level list section heading. Add a small spacer above it
        when it is not the first section in the list. Optionally show a
        secondary label on the right side of the same row.

        :param model: context list model
        :param translation_key: translation key for the section title
        :param right_text: optional right-aligned text (e.g. first Recent date section)
        :param action: optional hover action handled by ContextList
        :param section_count: total number of elements contained by the section
        """
        if model.rowCount() > 0:
            spacer = SectionItem("", group=False)
            spacer.setSizeHint(QtCore.QSize(0, self._list_section_top_spacing))
            model.appendRow(spacer)
        section_key = translation_key.rsplit('.', 1)[-1]
        model.appendRow(self.build_list_section(
            translation_key,
            right_text=right_text,
            action=action,
            section_key=section_key,
            section_count=section_count,
        ))

    def build_list_section(
        self,
        translation_key: str,
        right_text: str | None = None,
        action: str | None = None,
        section_key: str | None = None,
        section_count: int | None = None,
    ) -> SectionItem:
        """
        Build a top-level list section heading using the same visual style
        as date separators, but aligned to the left.

        :param translation_key: translation key for the section title
        :param right_text: optional right-aligned text shown in the same row
        :param action: optional hover action handled by ContextList
        :param section_key: stable top-level section ID used for collapse state
        :param section_count: total number of elements contained by the section
        :return: SectionItem
        """
        section = SectionItem(
            trans(translation_key),
            group=False,
            right_text=right_text,
            action=action,
            section_key=section_key,
            section_count=section_count,
        )
        section.setTextAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        # Keep every top-level section header at the same fixed height. Pinned
        # also changes its right-side content when collapsed (the total count
        # appears), so relying on the implicit size hint would shift its label
        # slightly vertically when the counter is shown.
        section.setSizeHint(QtCore.QSize(0, self._list_section_row_height))
        return section

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

        days_ago = max(0, (today - date).days)
        weeks_ago = days_ago // 7

        def relative(key: str, count: int) -> str:
            label = trans(key)
            if "{n}" in label:
                return label.format(n=count)
            return f"{count} {label}"

        if date == today:
            return trans('dt.today')
        elif date == yesterday:
            return trans('dt.yesterday')
        elif weeks_ago == 1:
            return trans('dt.week')
        elif 1 < weeks_ago and days_ago < 30:
            return relative('dt.weeks', weeks_ago)
        elif days_ago < 30:
            return relative('dt.days_ago', days_ago)

        # Keep older context headers relative as well. The grouping becomes
        # intentionally wider with age: individual days/weeks above, then
        # months, and finally whole years. This avoids falling back to one
        # section per calendar date for old conversations.
        months_ago = (today.year - date.year) * 12 + today.month - date.month
        if date.day > today.day:
            months_ago -= 1
        months_ago = max(1, months_ago)

        if months_ago < 12:
            if months_ago == 1:
                return trans('dt.month')
            return relative('dt.months', months_ago)

        years_ago = max(1, months_ago // 12)
        if years_ago == 1:
            return trans('dt.year')
        return relative('dt.years', years_ago)

    # ===========================
    # Helpers for group icons
    # ===========================

    def _set_group_icon_for_index(self, index: QtCore.QModelIndex, expanded: bool):
        """
        Set folder icon for a group index based on expansion state.
        """
        try:
            if not index.isValid():
                return
            model = index.model()
            if not hasattr(model, "itemFromIndex"):
                return
            item = model.itemFromIndex(index)
            if not isinstance(item, GroupItem):
                return
            if getattr(self, "_folder_icon", None) is None:
                self._folder_icon = QIcon(":/icons/folder.svg")
            if getattr(self, "_folder_open_icon", None) is None:
                self._folder_open_icon = QIcon(":/icons/folder_open.svg")
            item.setIcon(self._folder_open_icon if expanded else self._folder_icon)
        except Exception:
            pass

    def on_group_expanded(self, index: QtCore.QModelIndex):
        """
        Slot: update icon when a group is expanded.
        """
        self._set_group_icon_for_index(index, True)

    def on_group_collapsed(self, index: QtCore.QModelIndex):
        """
        Slot: update icon when a group is collapsed.
        """
        self._set_group_icon_for_index(index, False)