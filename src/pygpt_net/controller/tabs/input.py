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

from typing import Optional

from PySide6.QtCore import QTimer

from pygpt_net.core.tabs.tab import Tab


class TabInput:
    def _sync_chat_input_width(self):
        """Refresh responsive ChatInput width after split-screen geometry changes."""
        node = self.window.ui.nodes.get('input.container')
        if node is not None and hasattr(node, 'sync_width'):
            QTimer.singleShot(0, node.sync_width)

    def update_current(self):
        """Update current tab"""
        curr_tab = self.get_current_tab()
        curr_column = self.get_current_column_idx()
        if curr_tab is not None:
            self._state.remember(curr_column, curr_tab.idx, curr_tab.pid)
        self._update_chat_input_visibility(curr_tab)
        self.debug()

    def _get_column_current_tab(self, column_idx: int) -> Optional[Tab]:
        """Return the tab currently selected in ``column_idx``."""
        layout = getattr(self.window.ui, 'layout', None)
        if layout is None:
            return None
        tabs = layout.get_tabs_by_idx(column_idx)
        if tabs is None:
            return None
        idx = tabs.currentIndex()
        if idx < 0:
            return None
        return self.window.core.tabs.get_tab_by_index(idx, column_idx)

    def get_chat_input_column_idx(self) -> Optional[int]:
        """Return the visible column currently intended to host Chat input."""
        return self._get_chat_input_target_column()

    def is_chat_input_visible(self) -> bool:
        """Return True when the shared Chat input belongs to a visible Chat tab."""
        return self._get_chat_input_target_column() is not None

    def _get_chat_input_target_column(self) -> Optional[int]:
        """Return the visible column that should own the single Chat composer.

        With one visible Chat tab, keep the composer attached to that Chat even
        while the other column has focus (for example a Tool or Notepad tab).
        When both visible columns currently show Chat tabs, the composer follows
        the logically active/focused column.  If no visible column shows Chat,
        the composer is hidden.
        """
        visible_columns = [0]
        if self.is_split_screen_enabled():
            visible_columns.append(1)

        chat_columns = []
        for column_idx in visible_columns:
            current = self._get_column_current_tab(column_idx)
            if current is not None and current.type == Tab.TAB_CHAT:
                chat_columns.append(column_idx)

        if not chat_columns:
            return None
        if len(chat_columns) == 1:
            return chat_columns[0]

        active_column = self.get_current_column_idx()
        if active_column in chat_columns:
            return active_column

        # Defensive fallback for a transient/stale column focus event. With two
        # visible Chat tabs this should normally be unreachable.
        return chat_columns[0]

    def _update_chat_input_visibility(self, tab: Optional[Tab]):
        """Place the shared Chat composer according to visible Chat columns."""
        nodes = self.window.ui.nodes
        composer = nodes.get('input.container')
        root = nodes.get('input.root')
        if composer is None or root is None:
            return

        target_column = self._get_chat_input_target_column()
        show = target_column is not None
        layout = getattr(self.window.ui, 'layout', None)
        splitter = self.window.ui.splitters.get('main.output')
        live_saved = None

        # Capture the current chat geometry before moving the shared input to
        # another column. Once the old host is hidden its splitter naturally
        # reports a collapsed lower pane, so the snapshot must happen first.
        if splitter is not None:
            try:
                sizes = list(splitter.sizes())
                if self._is_expanded_chat_input_sizes(sizes):
                    live_saved = sizes
                    self.window.controller.ui.splitter_output_size_input = list(sizes)
            except Exception:
                pass

        if show:
            if layout is not None and hasattr(layout, 'mount_chat_input'):
                mounted = layout.mount_chat_input(root, target_column)
                if mounted is not None:
                    splitter = mounted

            root.show()
            composer.show()
            self._chat_input_suppressed = False
            composer.updateGeometry()
            root.updateGeometry()
            if hasattr(composer, 'sync_width'):
                QTimer.singleShot(0, composer.sync_width)

            saved = live_saved or self._chat_input_splitter_sizes
            if not self._is_expanded_chat_input_sizes(saved):
                cached = self.window.controller.ui.splitter_output_size_input
                if self._is_expanded_chat_input_sizes(cached):
                    saved = list(cached)
            if self._is_expanded_chat_input_sizes(saved):
                self._restore_chat_input_splitter_sizes(list(saved))
                QTimer.singleShot(0, lambda sizes=list(saved): self._restore_chat_input_splitter_sizes(sizes))
            else:
                # Profiles saved while a non-chat tab was active may contain the
                # footer-only splitter size from the old suppression code. Grow
                # the composer back to a usable minimum instead of leaving it at
                # zero/near-zero height. Run twice so delayed Qt size-hint
                # propagation cannot immediately clamp it back down.
                QTimer.singleShot(0, self._ensure_chat_input_splitter_visible)
                QTimer.singleShot(50, self._ensure_chat_input_splitter_visible)
            self._chat_input_splitter_sizes = None
            return

        # Files, Notepad, Calendar, Painter and every custom Tool tab use their
        # full column height. The application-wide status/footer remains outside
        # the per-column splitters, while only the shared Chat input is collapsed.
        if live_saved is not None:
            self._chat_input_splitter_sizes = list(live_saved)

        self._chat_input_suppressed = True
        composer.hide()
        root.hide()
        composer.updateGeometry()
        root.updateGeometry()
        if layout is not None and hasattr(layout, 'hide_chat_input'):
            layout.hide_chat_input(root)
        else:
            QTimer.singleShot(0, self._collapse_chat_input_splitter)

    def _input_root_index(self, splitter, root) -> int:
        if splitter is None or root is None:
            return -1
        try:
            direct = int(splitter.indexOf(root))
            if direct >= 0:
                return direct
            for idx in range(splitter.count()):
                widget = splitter.widget(idx)
                if widget is not None and widget.isAncestorOf(root):
                    return idx
        except Exception:
            pass
        return -1

    def _chat_input_footer_height(self) -> int:
        """Return legacy footer-only height for local input-pane detection.

        The application-wide bottom status is no longer a child of input.root,
        so a hidden local input pane now collapses fully to zero. Keep this
        compatibility helper at zero for old splitter-geometry checks.
        """
        return 0

    def _is_expanded_chat_input_sizes(self, sizes) -> bool:
        """Return True when sizes represent a real Chat composer, not footer-only suppression."""
        splitter = self.window.ui.splitters.get('main.output')
        root = self.window.ui.nodes.get('input.root')
        if splitter is None or root is None or not sizes or len(sizes) != splitter.count():
            return False
        try:
            input_idx = self._input_root_index(splitter, root)
            if input_idx < 0 or input_idx >= len(sizes) or sum(int(v) for v in sizes) <= 0:
                return False
            return int(sizes[input_idx]) > self._chat_input_footer_height() + 8
        except Exception:
            return False

    def remember_restored_chat_input_splitter_sizes(self, sizes):
        """Keep normal Chat geometry restored while the composer is temporarily hidden."""
        if self._chat_input_suppressed and self._is_expanded_chat_input_sizes(sizes):
            self._chat_input_splitter_sizes = list(sizes)

    def get_chat_input_splitter_sizes_for_save(self):
        """Return the real Chat geometry to persist while a non-chat tab hides the composer."""
        if not self._chat_input_suppressed:
            return None
        if self._is_expanded_chat_input_sizes(self._chat_input_splitter_sizes):
            return list(self._chat_input_splitter_sizes)
        return None

    def _ensure_chat_input_splitter_visible(self):
        """Recover a usable Chat input height from legacy footer-only saved geometry."""
        if self._chat_input_suppressed:
            return
        splitter = self.window.ui.splitters.get('main.output')
        root = self.window.ui.nodes.get('input.root')
        composer = self.window.ui.nodes.get('input.container')
        if splitter is None or root is None or composer is None:
            return
        try:
            composer.updateGeometry()
            root.updateGeometry()
            current = list(splitter.sizes())
            input_idx = self._input_root_index(splitter, root)
            if input_idx < 0 or input_idx >= len(current) or not current:
                return
            if self._is_expanded_chat_input_sizes(current):
                self.window.controller.ui.splitter_output_size_input = list(current)
                return

            total = sum(current)
            if total <= 0:
                return
            required = max(
                self._chat_input_footer_height() + 16,
                int(root.minimumSizeHint().height()),
                int(root.sizeHint().height()),
                140,
            )

            other_min_total = 0
            for idx in range(splitter.count()):
                if idx == input_idx:
                    continue
                widget = splitter.widget(idx)
                if widget is not None:
                    try:
                        other_min_total += max(0, int(widget.minimumSizeHint().height()))
                    except Exception:
                        pass
            target = min(required, max(0, total - other_min_total))
            if target <= current[input_idx]:
                return

            delta = target - current[input_idx]
            new_sizes = list(current)
            new_sizes[input_idx] = target
            remaining = delta
            for idx in range(len(new_sizes)):
                if idx == input_idx or remaining <= 0:
                    continue
                widget = splitter.widget(idx)
                min_h = 0
                if widget is not None:
                    try:
                        min_h = max(0, int(widget.minimumSizeHint().height()))
                    except Exception:
                        pass
                reducible = max(0, new_sizes[idx] - min_h)
                take = min(reducible, remaining)
                new_sizes[idx] -= take
                remaining -= take
            if remaining > 0:
                new_sizes[input_idx] = max(current[input_idx], new_sizes[input_idx] - remaining)
            splitter.setSizes(new_sizes)
            accepted = list(splitter.sizes())
            if self._is_expanded_chat_input_sizes(accepted):
                self.window.controller.ui.splitter_output_size_input = accepted
        except Exception:
            pass

    def _collapse_chat_input_splitter(self):
        """Collapse the local Chat input pane completely."""
        if not self._chat_input_suppressed:
            return

        splitter = self.window.ui.splitters.get('main.output')
        root = self.window.ui.nodes.get('input.root')
        if splitter is None or root is None:
            return

        try:
            root.updateGeometry()
            current = list(splitter.sizes())
            input_idx = self._input_root_index(splitter, root)
            if input_idx < 0 or input_idx >= len(current):
                return

            # On startup Layout may restore the normal Chat splitter geometry
            # after the non-chat tab already requested suppression. Preserve it
            # before replacing it with the footer-only runtime geometry.
            if self._chat_input_splitter_sizes is None and self._is_expanded_chat_input_sizes(current):
                self._chat_input_splitter_sizes = list(current)

            total = sum(current)
            target = 0
            if current[input_idx] <= target + 1:
                return

            reclaimed = current[input_idx] - target
            new_sizes = list(current)
            new_sizes[input_idx] = target

            # Give all reclaimed height to the output pane(s), preferring the
            # first one. main.output normally contains exactly output + input.
            for idx in range(len(new_sizes)):
                if idx == input_idx:
                    continue
                new_sizes[idx] += reclaimed
                break
            splitter.setSizes(new_sizes)
        except Exception:
            pass

    def _restore_chat_input_splitter_sizes(self, sizes):
        """Restore the pane geometry captured immediately before suppression."""
        if self._chat_input_suppressed:
            return
        splitter = self.window.ui.splitters.get('main.output')
        root = self.window.ui.nodes.get('input.root')
        composer = self.window.ui.nodes.get('input.container')
        if splitter is None or root is None or composer is None:
            return
        if not sizes or len(sizes) != splitter.count():
            return
        try:
            composer.updateGeometry()
            root.updateGeometry()
            splitter.setSizes(list(sizes))
        except Exception:
            pass
