#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 11:45:00                  #
# ================================================== #

from typing import Optional, Tuple

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.item.ctx import CtxMeta
from pygpt_net.utils import trans


class TabTitles:
    def reload_titles(self):
        """Reload tab titles"""
        self.window.core.tabs.reload_titles()
        self.debug()


    def get_current_tab_name(self) -> str:
        """
        Get current tab name

        :return: tab name
        """
        tab = self.get_current_tab()
        if tab is None:
            return ""
        tabs = self.window.ui.layout.get_tabs_by_idx(tab.column_idx)
        if tabs is None or tab.idx is None or tab.idx < 0 or tab.idx >= tabs.count():
            return ""
        return tabs.tabText(tab.idx)


    def get_current_tab_name_for_audio(self) -> str:
        """
        Get current tab name for audio description

        :return: tab name
        """
        tab = self.get_current_tab()
        if tab is None:
            return ""

        title = ""
        if tab.type in self.window.core.tabs.titles:
            title = trans(self.window.core.tabs.titles[tab.type])

        num = self.window.core.tabs.count_by_type(tab.type)
        if num > 1:
            order = self.window.core.tabs.get_order_by_idx_and_type(tab.idx, tab.type)
            if order != -1:
                title += f" #{order}"
        if tab.tooltip is not None and tab.tooltip != "":
            title += f" - {tab.tooltip}"
        return title


    def update_tooltip(
            self,
            tooltip: str,
            meta_id: Optional[int] = None,
    ):
        """
        Update chat tab tooltip.

        Render events may arrive while a non-chat tab is focused (e.g. Notepad
        or Painter), especially in split-screen mode. Never apply a context
        title to the currently focused tab blindly; target only chat tabs bound
        to the loaded context.

        :param tooltip: tooltip text
        :param meta_id: context meta ID; if omitted, use the current chat tab
        """
        if meta_id is None:
            tab = self.get_current_tab()
            targets = [tab] if tab is not None and tab.type == Tab.TAB_CHAT else []
        else:
            targets = [
                tab for tab in self.window.core.tabs.pids.values()
                if tab.type == Tab.TAB_CHAT and tab.data_id == meta_id
            ]

        for tab in targets:
            tabs = self.window.ui.layout.get_tabs_by_idx(tab.column_idx)
            if tabs is None or tab.idx is None or tab.idx < 0 or tab.idx >= tabs.count():
                continue
            tab.tooltip = tooltip
            tabs.setTabToolTip(tab.idx, tooltip)
        self.debug()


    def rename(
            self,
            idx: int,
            column_idx: int = 0
    ):
        """
        Rename tab (show dialog)

        :param idx: tab idx
        :param column_idx: column idx
        """
        tab = self.window.core.tabs.get_tab_by_index(idx, column_idx)
        if tab is None:
            return
        self.window.ui.dialog['rename'].id = 'tab.pid'
        self.window.ui.dialog['rename'].input.setText(tab.title)
        self.window.ui.dialog['rename'].current = tab.pid
        self.window.ui.dialog['rename'].show()


    def update_name(
        self,
        idx: int,
        name: str,
        close: bool = True,
        column_idx: Optional[int] = None,
    ):
        """Update a tab title by explicit column/index.

        An empty explicit name on a chat means "use the automatic title".
        It clears the custom-name flag and immediately restores the title from
        the context currently bound to that tab (or the default Chat title for
        an unbound/stale tab). Non-empty names remain explicit custom labels.
        """
        if column_idx is None:
            column_idx = self.get_current_column_idx()

        core = self.window.core
        tab = core.tabs.get_tab_by_index(idx, column_idx)
        empty_chat_name = (
            tab is not None
            and tab.type == Tab.TAB_CHAT
            and not str(name or "").strip()
        )

        if empty_chat_name:
            meta = (
                core.ctx.get_meta_by_id(tab.data_id)
                if tab.data_id is not None
                else None
            )
            if meta is not None and meta.name is not None:
                changed = self.update_title_by_tab(tab, meta.name, force=True)
            else:
                changed = self._reset_unbound_chat_title(tab, force=True)
        else:
            changed = core.tabs.update_title(
                idx,
                name,
                name,
                column_idx=column_idx,
                custom_name=True,
                title_source="custom",
            )

        if changed:
            core.tabs.save()
        if close:
            self.window.ui.dialog['rename'].close()
        self.debug()
        return changed

    def update_name_by_pid(self, pid: int, name: str, close: bool = True):
        """Update a tab title using stable tab identity."""
        tab = self.window.core.tabs.get_tab_by_pid(pid)
        if tab is None:
            return False
        return self.update_name(tab.idx, name, close, column_idx=tab.column_idx)

    def update_current_name(self, name: str):
        """Update the explicitly active tab title."""
        tab = self.get_current_tab()
        if tab is None:
            return False
        return self.update_name_by_pid(tab.pid, name)


    def _format_tab_title(self, title: str) -> Tuple[str, str]:
        """Return display title and full tooltip text."""
        tooltip = "" if title is None else str(title)
        display = tooltip
        if len(display) > self.TAB_CHAT_MAX_CHARS:
            display = display[:self.TAB_CHAT_MAX_CHARS] + '...'
        return display, tooltip


    def _legacy_chat_title_is_automatic(self, tab: Tab, meta: CtxMeta) -> bool:
        """Best-effort migration for tabs saved before title_source existed."""
        display, tooltip = self._format_tab_title(meta.name)
        saved_title = "" if tab.title is None else str(tab.title)
        saved_tooltip = "" if tab.tooltip is None else str(tab.tooltip)

        # Exact context title (or its old shortened display) was produced by the
        # automatic title path, even though older code could mark it custom.
        if saved_title == display or saved_tooltip == tooltip:
            return True

        placeholders = {"", "...", str(trans('ctx.new.prefix'))}
        if saved_title in placeholders or saved_tooltip in placeholders:
            return True

        default_chat = str(trans('output.tab.chat'))
        if saved_title == default_chat or saved_title.startswith(default_chat + " "):
            return True
        return False


    def update_title(
            self,
            idx: int,
            title: str
    ):
        """Update the current chat tab from its context title."""
        tab = self.window.core.tabs.get_tab_by_index(idx, self.get_current_column_idx())
        if tab is None or tab.type != Tab.TAB_CHAT:
            return False
        return self.update_title_by_tab(tab, title)


    def update_title_by_tab(self, tab: Tab, title: str, force: bool = False) -> bool:
        """
        Apply an automatic title to a tab.

        Explicit user names are never overwritten. For chat tabs this method is
        the context-name synchronization path; for tool tabs it remains an
        automatic/dynamic title update.
        """
        if tab is None:
            return False
        if not force and (tab.custom_name or tab.title_source == "custom"):
            return False

        tabs = self.window.ui.layout.get_tabs_by_idx(tab.column_idx)
        if tabs is None or tab.idx is None or tab.idx < 0 or tab.idx >= tabs.count():
            return False

        display, tooltip = self._format_tab_title(title)
        source = "context" if tab.type == Tab.TAB_CHAT else "auto"
        old = (tab.title, tab.tooltip, tab.custom_name, tab.title_source)

        tab.title = display
        tab.tooltip = tooltip
        tab.custom_name = False
        tab.title_source = source
        tabs.setTabText(tab.idx, display)
        tabs.setTabToolTip(tab.idx, tooltip)
        self.debug()
        return old != (tab.title, tab.tooltip, tab.custom_name, tab.title_source)


    def set_chat_placeholder(self, tab: Tab, title: str = "...") -> bool:
        """Set an empty-chat placeholder without marking it as a custom name."""
        if tab is None or tab.type != Tab.TAB_CHAT:
            return False

        display, tooltip = self._format_tab_title(title)
        old = (tab.title, tab.tooltip, tab.custom_name, tab.title_source)
        tab.title = display
        tab.tooltip = tooltip
        tab.custom_name = False
        # ``default`` deliberately prevents startup stale-binding reconciliation
        # from replacing the deletion placeholder with the generic Chat label.
        tab.title_source = "default"

        tabs = self.window.ui.layout.get_tabs_by_idx(tab.column_idx)
        if tabs is not None and tab.idx is not None and 0 <= tab.idx < tabs.count():
            tabs.setTabText(tab.idx, display)
            tabs.setTabToolTip(tab.idx, tooltip)
        return old != (tab.title, tab.tooltip, tab.custom_name, tab.title_source)


    def _reset_unbound_chat_title(self, tab: Tab, force: bool = False) -> bool:
        """Reset a chat tab to its default automatic title."""
        if tab is None or tab.type != Tab.TAB_CHAT:
            return False
        if not force and (tab.custom_name or tab.title_source == "custom"):
            return False

        tabs = self.window.ui.layout.get_tabs_by_idx(tab.column_idx)
        if tabs is None or tab.idx is None or tab.idx < 0 or tab.idx >= tabs.count():
            return False

        title = str(trans('output.tab.chat'))
        old = (tab.title, tab.tooltip, tab.custom_name, tab.title_source)
        tab.title = title
        tab.tooltip = title
        tab.custom_name = False
        tab.title_source = "default"
        tabs.setTabText(tab.idx, title)
        tabs.setTabToolTip(tab.idx, title)
        return old != (tab.title, tab.tooltip, tab.custom_name, tab.title_source)


    def sync_chat_titles(self, meta_id: Optional[int] = None) -> bool:
        """
        Synchronize chat tabs with CtxMeta names and repair stale bindings.

        A full sync (``meta_id is None``) is also the profile/startup
        reconciliation pass: every persisted ``data_id`` is verified against
        the database that is active *now*. A missing ID is detached instead of
        being allowed to survive as a misleading tab assignment.
        """
        changed = False
        core = self.window.core
        for tab in core.tabs.pids.values():
            if tab.type != Tab.TAB_CHAT:
                continue

            # A context-derived title without a binding is stale. This can be
            # left behind by old configs or by deleting a context while the tab
            # is persisted. Keep explicit user labels, reset automatic ones.
            if tab.data_id is None:
                if meta_id is None and tab.title_source == "context":
                    if self._reset_unbound_chat_title(tab):
                        changed = True
                continue

            if meta_id is not None and tab.data_id != meta_id:
                continue

            meta = core.ctx.get_meta_by_id(tab.data_id)
            if meta is None:
                # Full startup/profile reconciliation: this ID does not exist
                # in the active profile DB. Never keep a dangling assignment;
                # a later focus/send must treat this as a genuinely empty tab.
                if meta_id is None:
                    core.ctx.output.remove_pid(tab.pid)
                    tab.data_id = None
                    tab.loaded = False
                    self._reset_unbound_chat_title(tab)
                    changed = True
                continue
            if meta.name is None:
                continue

            # Legacy configs have no title_source. Older automatic updates could
            # incorrectly set custom_name=True, so migrate only values that can
            # be identified safely as automatic. Any other divergent name stays
            # custom to avoid destroying a user's label.
            if tab.title_source is None:
                if tab.custom_name and not self._legacy_chat_title_is_automatic(tab, meta):
                    tab.title_source = "custom"
                    continue
                tab.custom_name = False
                tab.title_source = "context"
                changed = True

            if tab.title_source == "custom" or tab.custom_name:
                continue
            if self.update_title_by_tab(tab, meta.name):
                changed = True
        return changed


    def update_title_current(self, title: str):
        """Update the title of the explicitly active chat tab."""
        tab = self.get_current_tab()
        if tab is None or tab.type != Tab.TAB_CHAT:
            return False
        return self.update_title_by_tab(tab, title)
