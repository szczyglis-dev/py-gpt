#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.24 11:00:00                  #
# ================================================== #

from pygpt_net.core.events import RenderEvent
from pygpt_net.core.tabs.tab import Tab


class TabLifecycle:
    def setup(self, reload: bool = False):
        """Setup tabs"""
        w = self.window

        # Suppress QTabWidget.currentChanged side effects while core Tabs is
        # rebuilding the saved widgets.  Active-tab/context restoration is done
        # deliberately later by restore_data(), after Ctx is ready.
        self.begin_widget_loading()
        try:
            w.core.tabs.load()
            w.controller.notepad.load()
            if not reload:
                self.setup_options()
        finally:
            self.end_widget_loading()
        self.mark_initialized()

    def setup_options(self):
        """Setup options"""
        w = self.window
        state = w.core.config.get("layout.split", False)
        w.ui.nodes['layout.split'].setChecked(state)
        if not state:
            w.ui.splitters['columns'].setSizes([1, 0])
        self._sync_chat_input_width()

    def unload(self):
        """Unload tabs and reset the logical selection registry."""
        self._state.reset()
        columns = self.window.ui.layout.columns
        for col in columns:
            col.setUpdatesEnabled(False)
        with self.suspend_tab_events():
            self.window.core.tabs.remove_all()
        for col in columns:
            col.setUpdatesEnabled(True)

    def reload(self, restore_data: bool = True):
        """
        Reload tab widgets from the current profile config.

        During a profile/workdir switch ``restore_data`` must be False. The
        new profile's tabs can be created immediately, but their ``data_id``
        values must not be resolved until ``ctx.reload()`` has loaded CtxMeta
        records from the new profile database.
        """
        self.unload()
        columns = self.window.ui.layout.columns
        for col in columns:
            col.setUpdatesEnabled(False)
        self.setup(reload=True)
        if restore_data:
            self.restore_after_ctx_reload()
        self.debug()
        for col in columns:
            col.setUpdatesEnabled(True)

    def restore_after_ctx_reload(self):
        """Restore active tabs only after the current profile CtxMeta is ready."""
        # Reset per-PID renderer state before loading the restored chats.
        # Preparing after restore_data() clears the renderer caches that have
        # just been populated for both split-screen columns; ctx.reload_after()
        # then refreshes only the globally current chat, leaving the other
        # visible WebView empty until it receives focus.
        self.window.dispatch(RenderEvent(RenderEvent.PREPARE))
        self.restore_data()
        self.debug()

    def reload_after(self):
        """Reload tabs after"""
        w = self.window
        plain = w.core.config.get("render.plain") is True
        outputs = w.ui.nodes['output']
        outputs_plain = w.ui.nodes['output_plain']
        for pid in outputs:
            out_plain = outputs_plain.get(pid)
            out = outputs.get(pid)
            if out_plain is None or out is None:
                continue
            if plain:
                out_plain.setVisible(True)
                out.setVisible(False)
            else:
                out_plain.setVisible(False)
                out.setVisible(True)
        self.debug()

    def finalize_profile_reload(self):
        """
        Re-apply the active tab state after the whole profile reload has finished.

        Tabs/contexts are restored early enough that the remaining controllers can
        use them during reload.  Some of those later steps (notably renderer/theme
        synchronization) can invalidate the already restored WebView or leave the
        footer visibility at an intermediate tab state.  Rebuild only the currently
        displayed chat outputs here and then re-apply the active tab UI.

        This intentionally does not call ``ctx.load()``: doing so would restore the
        mode/model stored in the conversation and could overwrite profile-level
        settings which were explicitly restored at the end of Controller.reload().
        """
        w = self.window
        layout = w.ui.layout

        # Rebuild the chat currently displayed in each active output column.
        # fresh_output() recreates/rebinds the WebView; refresh_output() fills it
        # from the target meta without changing the globally selected context.
        split = bool(w.core.config.get("layout.split", False))
        max_columns = len(getattr(layout, "columns", []))
        columns = range(max_columns if split else min(max_columns, 1))
        for column_idx in columns:
            tabs = layout.get_tabs_by_idx(column_idx)
            if tabs is None:
                continue
            idx = tabs.currentIndex()
            if idx < 0:
                continue
            tab = w.core.tabs.get_tab_by_index(idx, column_idx)
            if tab is None or tab.type != Tab.TAB_CHAT or tab.data_id is None:
                continue
            meta = w.core.ctx.get_meta_by_id(tab.data_id)
            if meta is None:
                continue

            # Rebuild against the tab being iterated, not whichever column is
            # currently focused while the profile UI is coming back online.
            output = w.core.ctx.output
            previous_pid = output.get_pinned_pid(meta)
            pinned_pid = output.pin_render_pid(meta, pid=tab.pid, force=True)
            if pinned_pid != tab.pid:
                continue
            try:
                w.controller.ctx.fresh_output(meta)
                w.controller.ctx.refresh_output(meta)
            finally:
                if previous_pid is not None:
                    output.render_pids[meta.id] = previous_pid
                else:
                    output.unpin_render_pid(meta=meta)

        # The active tab owns footer/chat-only visibility. Re-read the actual
        # QTabWidget selection instead of trusting values cached before reload.
        # When split-screen is disabled, column 1 still exists as a hidden
        # QTabWidget and can transiently steal the logical column during the
        # rebuild. Column 0 is unconditionally the active/visible column then.
        active_column = self.get_current_column_idx() if split else 0
        self.clear_pending_focus_column()
        tabs = layout.get_tabs_by_idx(active_column)
        if tabs is None:
            active_column = 0
            tabs = layout.get_tabs_by_idx(active_column)
        if tabs is not None:
            idx = tabs.currentIndex()
            if idx >= 0:
                tab = w.core.tabs.get_tab_by_index(idx, active_column)
                self._state.activate(active_column, idx, getattr(tab, "pid", None) if tab else None)

        w.controller.ui.mode.update()
        w.controller.ui.vision.update()
        tab = self.get_current_tab()
        if tab is not None:
            w.controller.audio.on_tab_changed(tab)

        # Re-apply the footer from the *resolved* active tab and repopulate its
        # chat metadata. During profile reload those labels can be cleared while
        # UI.update_*() still holds the previous cached strings, so a normal
        # update sees "no change" and skips setText(). That leaves Plugins /
        # mode / model / token-context info empty until ctx.load() is triggered
        # by a manual click on the conversation list.
        if tab is not None and tab.type == Tab.TAB_CHAT:
            w.controller.ui.mode.show_chat_footer()

            ui = w.controller.ui
            ui._last_input_string = None
            ui._last_chat_model = None
            ui._last_chat_label = None

            # Plugin count does not use the UI string cache, but it is profile-
            # dependent and must be recalculated after the new plugin config is
            # loaded.
            w.controller.plugins.update_info()
            ui.update_chat_label()
            ui.update_tokens()

            # Restore the mode/context label for the chat actually displayed in
            # the active tab without calling ctx.load() (which would also change
            # profile-level mode/model state).
            meta_id = getattr(tab, "data_id", None)
            meta = w.core.ctx.get_meta_by_id(meta_id) if meta_id is not None else None
            if meta is not None:
                mode = meta.mode or w.core.config.get("mode")
                w.controller.ctx.common.update_label(mode, meta.assistant)
            else:
                w.controller.ctx.common.update_label_by_current()
        else:
            w.controller.ui.mode.hide_chat_footer()

        self.update_current()
        self.debug()
