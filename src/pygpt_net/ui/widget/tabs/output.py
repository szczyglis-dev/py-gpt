#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.08.25 18:00:00                  #
# ================================================== #

from PySide6.QtWidgets import QTabWidget, QMenu, QPushButton, QToolButton, QTabBar
from PySide6.QtCore import Qt, Slot, QTimer, QEvent
from PySide6.QtGui import QAction, QIcon, QGuiApplication

from pygpt_net.core.tabs.tab import Tab
from pygpt_net.utils import trans

_ICON_CACHE = {}


def icon(path: str) -> QIcon:
    if QGuiApplication.instance() is None:
        return QIcon()
    cached = _ICON_CACHE.get(path)
    if cached is None:
        cached = QIcon(path)
        _ICON_CACHE[path] = cached
    return cached


ICON_PATH_ADD = ':/icons/add.svg'
ICON_PATH_EDIT = ':/icons/edit.svg'
ICON_PATH_CLOSE = ':/icons/close.svg'
ICON_PATH_RELOAD = ':/icons/reload.svg'
ICON_PATH_FORWARD = ':/icons/forward'
ICON_PATH_BACK = ':/icons/back'


class OutputTabBar(QTabBar):
    def __init__(
            self,
            window=None,
            column=None,
            tabs=None,
            corner_button=None,
            parent=None
    ):
        super().__init__(parent)
        self.window = window
        self.column = column
        self.tabs = tabs
        self.corner_button = corner_button

        # inline [+] just after the last tab (only when there is real free space)
        self.add_btn_inline = AddButton(window, column, tabs)
        self.add_btn_inline.setParent(self)
        self.add_btn_inline.setVisible(False)
        self.add_btn_inline.raise_()

        # visual gap between last tab and [+]
        self._spacing = 3

        # add button vertical offset (to align with text)
        self._inline_y_offset = 2  # px up

        # keep tabs natural width (do not stretch)
        self.setExpanding(False)

        # allow scroll buttons when needed
        self.setUsesScrollButtons(True)

        # ensure the tab bar stays visible even with 0 tabs
        self._min_bar_height = max(self.add_btn_inline.sizeHint().height() + 6, 28)
        self.setMinimumHeight(self._min_bar_height)

        if hasattr(self.tabs, "setTabBarAutoHide"):
            self.tabs.setTabBarAutoHide(False)

        # state
        self._inline_mode = False
        self._corner_current = None  # track where the corner [+] currently is
        self._last_inline_pos = None  # track last inline position to avoid useless moves

        # coalesced updates (debounce to 1 per event-loop turn)
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self.updateAddButtonPlacement)

        # re-layout updates
        self.currentChanged.connect(lambda _: self._queue_update())
        self.tabMoved.connect(lambda _from, _to: self._queue_update())

        # initial placement
        QTimer.singleShot(0, self.updateAddButtonPlacement)

    def sizeHint(self):
        """
        Override sizeHint to

        :return: QSize
        """
        # keep a non-zero height even with 0 tabs
        sh = super().sizeHint()
        sh.setHeight(max(sh.height(), self._min_bar_height))
        return sh

    def minimumSizeHint(self):
        """
        Override minimumSizeHint

        :return: QSize
        """
        m = super().minimumSizeHint()
        m.setHeight(max(m.height(), self._min_bar_height))
        return m

    def _queue_update(self):
        """Queue an update to recompute [+] placement (debounced)."""
        # Coalesce many triggers into a single call at the end of the event loop.
        self._update_timer.start(0)

    def _visible_scroll_buttons(self):
        """
        Find the left and right scroll buttons if they are visible.

        :return: (left_button, right_button) or (None, None) if not found
        """
        # find the scroll arrow buttons created by QTabBar
        left = right = None
        for btn in self.findChildren(QToolButton):
            if not btn.isVisible():
                continue
            if not btn.autoRepeat():
                continue
            if left is None or btn.x() < left.x():
                left = btn
            if right is None or btn.x() > right.x():
                right = btn
        return left, right

    def _set_corner_target(self, corner: Qt.Corner | None) -> bool:
        """
        Move the corner_button to a given corner (or detach it) only when it changes.

        :param corner: target corner or None to detach
        :return: True if changed, False if no change was needed
        """
        if self.corner_button is None:
            return False

        if self._corner_current == corner:
            return False  # nothing to do

        # detach only from the previously used corner
        if self._corner_current is not None:
            self.tabs.setCornerWidget(None, self._corner_current)

        if corner is not None:
            self.tabs.setCornerWidget(self.corner_button, corner)

        self._corner_current = corner
        return True

    def _column_index(self) -> int:
        """
        Get the column index this tab bar belongs to (0 or 1).

        :return: Column index
        """
        idx = 0
        if self.column is None:
            return idx
        return int(self.column.get_idx())

    def updateAddButtonPlacement(self):
        """
        Recompute where the [+] button should be placed (inline or corner).

        This method is called automatically on relevant events.
        1. If there are no tabs, show [+] in the left or right corner based on column index.
        2. If there are tabs but scroll buttons are visible (overflow), show [+] in the top-right corner.
        3. If there are tabs and no scroll buttons, show [+] inline after the last tab if there's room.
        4. Otherwise, show [+] in the top-right corner.
        """
        # CASE 1: no tabs -> show [+] in left or right corner based on column index
        if self.count() == 0:
            idx = self._column_index()
            corner = Qt.TopLeftCorner if idx == 0 else Qt.TopRightCorner

            changed = False
            changed |= self._set_corner_target(corner)

            if self._inline_mode:
                self._inline_mode = False
                changed = True

            if self.add_btn_inline.isVisible():
                self.add_btn_inline.setVisible(False)
                changed = True

            if self.corner_button is not None and not self.corner_button.isVisible():
                self.corner_button.setVisible(True)
                changed = True
            return

        # CASE 2: tabs exist
        # if scroll buttons are visible we are in overflow -> use top-right corner [+]
        left_sb, right_sb = self._visible_scroll_buttons()
        if left_sb or right_sb:
            changed = False
            if self._inline_mode:
                self._inline_mode = False
                changed = True
            if self.add_btn_inline.isVisible():
                self.add_btn_inline.setVisible(False)
                changed = True
            changed |= self._set_corner_target(Qt.TopRightCorner)
            if self.corner_button is not None and not self.corner_button.isVisible():
                self.corner_button.setVisible(True)
                changed = True
            return

        # otherwise, put [+] inline (right after the last tab) if there's real room
        last_rect = self.tabRect(self.count() - 1)
        x = last_rect.right() + 1 + self._spacing
        want_inline = (x + self.add_btn_inline.width()) <= (self.width() - 1)

        if want_inline:
            changed = False

            if not self._inline_mode:
                self._inline_mode = True
                changed = True

            # hide any corner [+]
            if self.corner_button is not None and self.corner_button.isVisible():
                self.corner_button.setVisible(False)
                changed = True
            changed |= self._set_corner_target(None)

            # compute position
            y = (self.height() - self.add_btn_inline.height()) // 2
            # NOTE: lift inline [+] slightly to align with tabs
            y = max(0, y - self._inline_y_offset)  # clamp to avoid negative
            x = min(x, self.width() - self.add_btn_inline.width() - 1)  # clamp inside the bar
            new_pos = (x, y)
            if self._last_inline_pos != new_pos:
                self.add_btn_inline.move(x, y)
                self._last_inline_pos = new_pos
                changed = True

            if not self.add_btn_inline.isVisible():
                self.add_btn_inline.setVisible(True)
                changed = True

            self.add_btn_inline.raise_()
        else:
            # not enough room -> top-right corner
            changed = False
            if self._inline_mode:
                self._inline_mode = False
                changed = True
            if self.add_btn_inline.isVisible():
                self.add_btn_inline.setVisible(False)
                changed = True
            changed |= self._set_corner_target(Qt.TopRightCorner)
            if self.corner_button is not None and not self.corner_button.isVisible():
                self.corner_button.setVisible(True)
                changed = True

    def resizeEvent(self, event):
        """Resize event handler to recompute [+] placement."""
        super().resizeEvent(event)
        self._queue_update()

    def showEvent(self, event):
        """Show event handler to recompute [+] placement."""
        super().showEvent(event)
        self._queue_update()

    def tabInserted(self, index):
        """Tab inserted event handler to recompute [+] placement."""
        super().tabInserted(index)
        self._queue_update()

    def tabRemoved(self, index):
        """Tab removed event handler to recompute [+] placement."""
        super().tabRemoved(index)
        self._queue_update()

    def event(self, e):
        """Event handler to catch layout/style changes that may affect [+] placement."""
        res = super().event(e)
        # only queue updates
        if e.type() in (QEvent.LayoutRequest, QEvent.StyleChange, QEvent.PolishRequest, QEvent.FontChange):
            self._queue_update()
        return res


class AddButton(QPushButton):
    def __init__(self, window=None, column=None, tabs=None):
        super(AddButton, self).__init__(icon(ICON_PATH_ADD), "", window)
        self.window = window
        self.column = column
        self.tabs = tabs
        self.setFixedSize(30, 25)
        self.setFlat(True)
        self.clicked.connect(
            lambda: self.window.controller.ui.tabs.new_tab(self.column.get_idx())
        )
        self.setObjectName('tab-add')
        self.setProperty('tabAdd', True)
        self.setToolTip(trans('action.tab.add.chat'))

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: event
        """
        if event.button() == Qt.RightButton:
            idx = 0
            column_idx = self.column.get_idx()
            self.show_menu(idx, column_idx, event.globalPos())
        super(AddButton, self).mousePressEvent(event)

    def show_menu(self, index: int, column_idx: int, global_pos):
        """
        Show context menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        context_menu.exec(global_pos)

    def prepare_menu(self, index: int, column_idx: int) -> QMenu:
        """
        Prepare and return context menu

        :param index: index
        :param column_idx: column index
        :return: menu
        """
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose, True)

        add_chat = QAction(icon(ICON_PATH_ADD), trans('action.tab.add.chat'), menu)
        add_chat.triggered.connect(
            lambda: self.tabs.add_tab(-2, column_idx, Tab.TAB_CHAT)
        )
        add_notepad = QAction(icon(ICON_PATH_ADD), trans('action.tab.add.notepad'), menu)
        add_notepad.triggered.connect(
            lambda: self.tabs.add_tab(-2, column_idx, Tab.TAB_NOTEPAD)
        )

        menu.addAction(add_chat)
        menu.addAction(add_notepad)

        self.window.controller.tools.append_tab_menu(self, menu, -2, column_idx, self.tabs)

        return menu


class OutputTabs(QTabWidget):
    def __init__(self, window=None, column=None):
        super(OutputTabs, self).__init__(window)
        self.window = window
        self.active = True
        self.column = column
        self.setMinimumHeight(1)
        self.owner = None
        self.setMovable(True)
        self.init()

    def init(self):
        """Initialize"""
        # create the [+] button
        add_button = AddButton(self.window, self.column, self)

        # add the button to the top right corner of the tab bar
        self.setCornerWidget(add_button, corner=Qt.TopRightCorner)

        self.setDocumentMode(True)

        # use a custom tab bar that shows an inline [+] right after the tabs
        tab_bar = OutputTabBar(
            window=self.window,
            column=self.column,
            tabs=self,
            corner_button=add_button,
            parent=self,
        )
        self.setTabBar(tab_bar)
        self.setMovable(True)
        self.tabBar().setMovable(True)

        self.setDocumentMode(True)  # QT Material fix
        self.tabBar().setDrawBase(False)  # QT Material fix

        # the custom tab bar decides when to show inline or corner [+]
        add_button.setVisible(False)

        # ensure initial recompute happens after the first layout pass
        QTimer.singleShot(0, self._refresh_plus_button)

        # tab bar visible even when empty
        if hasattr(self, "setTabBarAutoHide"):
            self.setTabBarAutoHide(False)

        # IMPORTANT: reserve vertical space for the bar even with 0 tabs
        # (prevents the whole widget from collapsing)
        mh = max(self.tabBar().minimumSizeHint().height() + 2, 30)  # +2
        self.setMinimumHeight(mh)

        # connect signals
        self.currentChanged.connect(self._on_current_changed)
        self.tabBarClicked.connect(self._on_tabbar_clicked)
        self.tabBarDoubleClicked.connect(self._on_tabbar_dbl_clicked)
        self.tabCloseRequested.connect(self._on_tab_close_requested)
        self.tabBar().tabMoved.connect(self._on_tab_moved)

    def set_active(self, active: bool):
        """
        Set the active state of the tab bar.

        :param active: True to activate, False to deactivate
        """
        self.active = active

    def _refresh_plus_button(self):
        """Force the tab bar to recompute [+] placement after tab changes."""
        tb = self.tabBar()
        if hasattr(tb, "updateAddButtonPlacement"):
            tb.updateAddButtonPlacement()

    def addTab(self, *args, **kwargs):
        """Add a new tab and refresh [+] placement."""
        idx = super().addTab(*args, **kwargs)
        QTimer.singleShot(0, self._refresh_plus_button)  # defer until layout is done
        return idx

    def insertTab(self, *args, **kwargs):
        """Insert a new tab at a specific index and refresh [+] placement."""
        idx = super().insertTab(*args, **kwargs)
        QTimer.singleShot(0, self._refresh_plus_button)
        return idx

    def removeTab(self, index):
        """Remove a tab and refresh [+] placement."""
        super().removeTab(index)
        QTimer.singleShot(0, self._refresh_plus_button)

    def setTabText(self, index: int, text: str):
        """Set tab text and refresh [+] placement."""
        super().setTabText(index, text)
        QTimer.singleShot(0, self._refresh_plus_button)

    def clear(self):
        """Clear all tabs and refresh [+] placement."""
        super().clear()
        QTimer.singleShot(0, self._refresh_plus_button)

    def get_column(self):
        """
        Get column

        :return: OutputColumn
        """
        return self.column

    def setOwner(self, owner: Tab):
        """
        Set internal tab instance

        :param owner: parent tab instance
        """
        self.owner = owner

    def mousePressEvent(self, event):
        """
        Mouse press event

        :param event: event
        """
        if event.button() == Qt.RightButton:
            idx = self.tabBar().tabAt(event.pos())
            column_idx = self.column.get_idx()
            tab = self.window.core.tabs.get_tab_by_index(idx, column_idx)
            if tab is not None:
                if tab.type == Tab.TAB_NOTEPAD:
                    self.show_notepad_menu(idx, column_idx, event.globalPos())  # notepad
                elif tab.type == Tab.TAB_CHAT:
                    self.show_chat_menu(idx, column_idx, event.globalPos())  # chat
                elif tab.type == Tab.TAB_FILES:
                    self.show_files_menu(idx, column_idx, event.globalPos())  # files
                elif tab.type == Tab.TAB_TOOL:
                    self.show_tool_menu(idx, column_idx, event.globalPos())  # tool
                else:
                    self.show_default_menu(idx, column_idx, event.globalPos())  # default
        super(OutputTabs, self).mousePressEvent(event)

    def prepare_menu(self, index: int, column_idx: int) -> QMenu:
        """
        Prepare and return context menu

        :param index: index
        :param column_idx: column index
        :return: menu
        """
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose, True)

        add_chat = QAction(icon(ICON_PATH_ADD), trans('action.tab.add.chat'), menu)
        add_chat.triggered.connect(
            lambda: self.add_tab(index, column_idx, Tab.TAB_CHAT)
        )
        add_notepad = QAction(icon(ICON_PATH_ADD), trans('action.tab.add.notepad'), menu)
        add_notepad.triggered.connect(
            lambda: self.add_tab(index, column_idx, Tab.TAB_NOTEPAD)
        )
        edit = QAction(icon(ICON_PATH_EDIT), trans('action.rename'), menu)
        edit.triggered.connect(
            lambda: self.rename_tab(index, column_idx)
        )
        move_right = QAction(icon(ICON_PATH_FORWARD), trans('action.tab.move.right'), menu)
        move_right.triggered.connect(
            lambda: self.window.controller.ui.tabs.move_tab(index, column_idx, 1)
        )
        move_left = QAction(icon(ICON_PATH_BACK), trans('action.tab.move.left'), menu)
        move_left.triggered.connect(
            lambda: self.window.controller.ui.tabs.move_tab(index, column_idx, 0)
        )

        menu.addAction(add_chat)
        menu.addAction(add_notepad)

        self.window.controller.tools.append_tab_menu(self, menu, index, column_idx, self)

        menu.addAction(edit)

        if column_idx != 0:
            menu.addAction(move_left)
        if column_idx != 1:
            menu.addAction(move_right)

        return menu

    def show_notepad_menu(self, index: int, column_idx: int, global_pos):
        """
        Show notepad menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        close_act = QAction(icon(ICON_PATH_CLOSE), trans('action.tab.close'), context_menu)
        close_act.triggered.connect(
            lambda: self.close_tab(index, column_idx)
        )
        close_all_act = QAction(icon(ICON_PATH_CLOSE), trans('action.tab.close_all.notepad'), context_menu)
        close_all_act.triggered.connect(
            lambda: self.close_all(Tab.TAB_NOTEPAD, column_idx)
        )
        context_menu.addAction(close_act)

        if self.window.core.tabs.count_by_type(Tab.TAB_NOTEPAD) > 1:
            context_menu.addAction(close_all_act)

        context_menu.exec(global_pos)

    def show_chat_menu(self, index: int, column_idx: int, global_pos):
        """
        Show chat menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        close_act = QAction(icon(ICON_PATH_CLOSE), trans('action.tab.close'), context_menu)
        close_act.triggered.connect(
            lambda: self.close_tab(index, column_idx)
        )
        close_all_act = QAction(icon(ICON_PATH_CLOSE), trans('action.tab.close_all.chat'), context_menu)
        close_all_act.triggered.connect(
            lambda: self.close_all(Tab.TAB_CHAT, column_idx)
        )

        # at least one chat tab must be open
        if self.window.core.tabs.count_by_type(Tab.TAB_CHAT) > 1:
            context_menu.addAction(close_act)
            context_menu.addAction(close_all_act)

        context_menu.exec(global_pos)

    def show_files_menu(self, index: int, column_idx: int, global_pos):
        """
        Show files menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        refresh = QAction(icon(ICON_PATH_RELOAD), trans('action.refresh'), context_menu)
        refresh.triggered.connect(
            lambda: self.window.controller.files.update_explorer()
        )
        context_menu.addAction(refresh)
        context_menu.exec(global_pos)

    def show_tool_menu(self, index: int, column_idx: int, global_pos):
        """
        Show tool menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        close_act = QAction(icon(ICON_PATH_CLOSE), trans('action.tab.close'), context_menu)
        close_act.triggered.connect(
            lambda: self.close_tab(index, column_idx)
        )
        context_menu.addAction(close_act)
        context_menu.exec(global_pos)

    def show_default_menu(self, index: int, column_idx: int, global_pos):
        """
        Show default menu

        :param index: index
        :param column_idx: column index
        :param global_pos: global position
        """
        context_menu = self.prepare_menu(index, column_idx)
        context_menu.exec(global_pos)

    @Slot(int)
    def _on_current_changed(self, _idx: int):
        """On current tab changed"""
        self.window.controller.ui.tabs.on_tab_changed(self.currentIndex(), self.column.get_idx())

    @Slot(int)
    def _on_tabbar_clicked(self, _idx: int):
        """On tab bar clicked"""
        self.window.controller.ui.tabs.on_tab_clicked(self.currentIndex(), self.column.get_idx())

    @Slot(int)
    def _on_tabbar_dbl_clicked(self, _idx: int):
        """On tab bar double clicked"""
        self.window.controller.ui.tabs.on_tab_dbl_clicked(self.currentIndex(), self.column.get_idx())

    @Slot(int)
    def _on_tab_close_requested(self, _idx: int):
        """On tab close requested"""
        self.window.controller.ui.tabs.on_tab_closed(self.currentIndex(), self.column.get_idx())
        QTimer.singleShot(0, self._refresh_plus_button)  # defer until layout is done

    @Slot(int, int)
    def _on_tab_moved(self, _from: int, _to: int):
        """On tab moved"""
        self.window.controller.ui.tabs.on_tab_moved(self.currentIndex(), self.column.get_idx())

    @Slot()
    def rename_tab(self, index: int, column_idx: int):
        """
        Rename tab

        :param index: index
        :param column_idx: column index
        """
        self.window.controller.ui.tabs.rename(index, column_idx)

    @Slot()
    def close_tab(self, index: int, column_idx: int):
        """
        Close tab

        :param index: index
        :param column_idx: column index
        """
        self.window.controller.ui.tabs.close(index, column_idx)

    @Slot()
    def close_all(self, type, column_idx: int):
        """
        Close all tabs

        :param type: type
        :param column_idx: column index
        """
        self.window.controller.ui.tabs.close_all(type, column_idx)

    @Slot()
    def add_tab(self, index: int, column_idx: int, type: int, tool_id: str = None):
        """
        Add a new tab

        :param index: index
        :param column_idx: column index
        :param type: type
        :param tool_id: tool id
        """
        if index == -2:  # new btn
            index = self.window.core.tabs.get_max_idx_by_column(column_idx)
            if index == -1:
                index = 0

        self.window.controller.ui.tabs.append(
            type=type,
            tool_id=tool_id,
            idx=index,
            column_idx=column_idx,
        )