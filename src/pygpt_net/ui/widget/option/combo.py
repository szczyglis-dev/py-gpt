#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2025.12.27 02:00:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QEvent, QTimer, QRect
from PySide6.QtWidgets import (
    QHBoxLayout,
    QWidget,
    QComboBox,
    QAbstractItemView,
    QStyle,
    QStyleOptionComboBox,
    QLineEdit,
    QListView,
    QStyledItemDelegate,
)
from PySide6.QtGui import QFontMetrics, QStandardItem, QStandardItemModel, QIcon  # keep existing imports, extend with items

from pygpt_net.utils import trans


class SeparatorComboBox(QComboBox):
    """A combo box that supports adding separator items and prevents selecting them."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._SEP_ROLE = Qt.UserRole + 1000
        self._block_guard = False

    def addSeparator(self, text):
        """
        Adds a separator item to the combo box that cannot be selected.
        This keeps separators visible but disabled/unselectable.

        :param text: The text to display for the separator.
        """
        model = self.model()
        if isinstance(model, QStandardItemModel):
            item = QStandardItem(text)
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled & ~Qt.ItemIsSelectable)
            item.setData(True, self._SEP_ROLE)
            model.appendRow(item)
        else:
            index = self.count()
            self.addItem(text)
            try:
                role = Qt.UserRole - 1
                self.setItemData(index, 0, role)
            except Exception:
                pass
            self.setItemData(index, True, self._SEP_ROLE)

    def is_separator(self, index: int) -> bool:
        """
        Returns True if item at index is a separator.

        :param index: The index to check.
        """
        if index < 0 or index >= self.count():
            return False
        try:
            if self.itemData(index, self._SEP_ROLE):
                return True
        except Exception:
            pass
        try:
            idx = self.model().index(index, self.modelColumn(), self.rootModelIndex())
            flags = self.model().flags(idx)
            if not (flags & Qt.ItemIsEnabled) or not (flags & Qt.ItemIsSelectable):
                return True
        except Exception:
            pass
        return False

    def first_valid_index(self) -> int:
        """Returns the first non-separator index, or -1 if none."""
        for i in range(self.count()):
            if not self.is_separator(i):
                return i
        return -1

    def last_valid_index(self) -> int:
        """
        Returns the last non-separator index, or -1 if none.

        :return: last valid index or -1
        """
        for i in range(self.count() - 1, -1, -1):
            if not self.is_separator(i):
                return i
        return -1

    def _sanitize_index(self, index: int) -> int:
        """
        Returns a corrected non-separator index, or -1 if none available.

        :param index: The index to sanitize.
        """
        if index is None:
            index = -1
        if index < 0 or index >= self.count():
            return self.first_valid_index()
        if self.is_separator(index):
            for i in range(index + 1, self.count()):
                if not self.is_separator(i):
                    return i
            for i in range(index - 1, -1, -1):
                if not self.is_separator(i):
                    return i
            return -1
        return index

    def ensure_valid_current(self) -> int:
        """
        Ensures the current index is not a separator.
        Returns the final valid index (or -1) after correction.

        :return: valid current index or -1
        """
        current = super().currentIndex()
        corrected = self._sanitize_index(current)
        if corrected != current:
            try:
                self._block_guard = True
                super().setCurrentIndex(corrected if corrected != -1 else -1)
            finally:
                self._block_guard = False
        return corrected

    def setCurrentIndex(self, index: int) -> None:
        """
        Prevent setting the current index to a separator from any caller.

        :param index: The desired index to set.
        """
        if self._block_guard:
            return super().setCurrentIndex(index)
        corrected = self._sanitize_index(index)
        try:
            self._block_guard = True
            super().setCurrentIndex(corrected if corrected != -1 else -1)
        finally:
            self._block_guard = False


class SearchableCombo(SeparatorComboBox):
    """
    A combo box with web-like search input shown while the popup is open.

    Behaviour:
    - search enabled by default (self.search == True).
    - First click on the combo opens the popup and displays a search field with a magnifier icon at the top of the popup,
      visually overlapping the combo area. The search field receives focus immediately (caret at end).
    - Typing scrolls the dropdown so that the first match appears at the top; nothing is auto-selected.
    - Popup is closed by focus out (clicking outside).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search: bool = True
        self._popup_open: bool = False
        self._search_line: QLineEdit | None = None
        self._search_action = None
        self._search_icon_path: str = ":/icons/search.svg"

        self._popup_container = None
        self._popup_header: QLineEdit | None = None
        self._popup_header_action = None
        self._popup_header_h: int = 28

        self._last_query_text: str = ""
        self._suppress_search: bool = False

        self._install_persistent_editor()
        self._init_popup_view_style_targets()

    # ----- Make the popup list reliably stylable -----

    def _init_popup_view_style_targets(self):
        """
        Ensure the popup list can be styled by common QSS rules:
        - Use a QListView explicitly.
        - Install a QStyledItemDelegate so sub-control item rules can take effect.
        - Provide stable objectNames/properties that themes (e.g., Qt Material) can target, if they rely on them.
        """
        try:
            lv = QListView(self)
            lv.setObjectName("ComboPopupList")             # e.g.: QListView#ComboPopupList { ... }
            lv.viewport().setObjectName("ComboPopupViewport")
            lv.setUniformItemSizes(False)
            self.setView(lv)
        except Exception:
            pass

        try:
            self.setItemDelegate(QStyledItemDelegate(self))  # allow ::item rules to be honored by the delegate
        except Exception:
            pass

        try:
            # Some themes use class selectors; expose a generic one on the view.
            self.view().setProperty("class", "combo-popup")
        except Exception:
            pass

    # ----- Persistent editor (display only, outside the popup) -----

    def _install_persistent_editor(self):
        """Create a persistent editor used for normal display; real search input lives in the popup header."""
        self.setEditable(True)
        line = QLineEdit(self)
        line.setPlaceholderText("")
        line.setClearButtonEnabled(False)
        line.setReadOnly(True)
        line.setFocusPolicy(Qt.NoFocus)
        line.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setLineEdit(line)
        line.installEventFilter(self)
        self._search_line = line
        self._sync_editor_to_current()

    # ----- Public API -----

    def setSearchEnabled(self, enabled: bool):
        """
        Enable or disable search functionality.

        :param enabled: bool
        """
        self.search = bool(enabled)
        if not self.search:
            self._teardown_popup_header()
            if self._search_line is not None:
                self._remove_magnifier_on(self._search_line)
                self._search_line.setClearButtonEnabled(False)
                self._search_line.setReadOnly(True)
                self._search_line.setFocusPolicy(Qt.NoFocus)
                self._sync_editor_to_current()

    # ----- Popup lifecycle -----

    def showPopup(self):
        """Open popup, set max visible height, inject header, and place it over the combo area."""
        self._apply_popup_max_rows()
        super().showPopup()
        self._popup_open = True

        first = self.first_valid_index()
        if first != -1:
            self._scroll_to_row(first)

        if self.search:
            self._prepare_popup_header()

        QTimer.singleShot(0, self._apply_popup_max_rows)

    def hidePopup(self):
        """Close popup and restore normal display text; remove header/margins."""
        super().hidePopup()
        self._popup_open = False

        if self._popup_header is not None:
            try:
                t = (self._popup_header.text() or "").strip()
                if t:
                    row = self._find_target_row_for(t.lower())
                    if row != -1:
                        self._last_query_text = t
                else:
                    self._last_query_text = ""
            except Exception:
                pass

        if self._search_line is not None:
            self._remove_magnifier_on(self._search_line)
            self._search_line.setClearButtonEnabled(False)
            self._search_line.setReadOnly(True)
            self._search_line.setFocusPolicy(Qt.NoFocus)
            self._sync_editor_to_current()

        self._teardown_popup_header()

    # ----- Popup header management (search input inside popup) -----

    def _prepare_popup_header(self):
        """
        Create and place a search line edit inside the popup container itself.
        The container is moved upwards by the header height so the header overlaps the combo area.
        """
        view = self.view()
        if view is None:
            return

        container = view.window()
        if container is None:
            return

        # Expose recognizable identifiers on the popup container for stylesheet authors
        try:
            container.setObjectName("ComboPopupWindow")         # QWidget#ComboPopupWindow { ... }
            container.setProperty("class", "combo-popup-window")
        except Exception:
            pass

        self._popup_container = container
        container.installEventFilter(self)

        if self._popup_header is None:
            self._popup_header = QLineEdit(container)
            self._popup_header.setObjectName("comboSearchHeader")
            self._popup_header.setClearButtonEnabled(True)
            self._popup_header.setReadOnly(False)
            self._popup_header.setFocusPolicy(Qt.ClickFocus)
            self._popup_header.textChanged.connect(self._on_search_text_changed)
            self._popup_header.installEventFilter(self)
            self._ensure_magnifier_on(self._popup_header)

        self._popup_header_h = max(24, self._popup_header.sizeHint().height())

        try:
            geo: QRect = container.geometry()
            new_geo = QRect(geo.x(), geo.y() - self._popup_header_h, geo.width(), geo.height() + self._popup_header_h)
            container.setGeometry(new_geo)
        except Exception:
            pass

        try:
            view.setViewportMargins(0, self._popup_header_h, 0, 0)
        except Exception:
            pass

        try:
            view.installEventFilter(self)
            if hasattr(view, "viewport"):
                view.viewport().installEventFilter(self)
        except Exception:
            pass

        self._place_popup_header()

        if self._search_line is not None:
            self._search_line.setReadOnly(True)
            self._search_line.setFocusPolicy(Qt.NoFocus)
            self._ensure_magnifier_on(self._search_line)

        self._prefill_with_current_or_restore_last()
        self._focus_header_async()

    def _place_popup_header(self):
        """Position the header inside popup container and keep it visible."""
        if not self._popup_container or not self._popup_header:
            return
        try:
            w = self._popup_container.width()
            h = self._popup_header_h
            self._popup_header.setGeometry(1, 1, max(1, w - 2), h - 2)
            self._popup_header.show()
        except Exception:
            pass

    def _teardown_popup_header(self):
        """Remove margins and hide the header, leaving the container to default."""
        view = self.view()
        if view is not None:
            try:
                view.setViewportMargins(0, 0, 0, 0)
            except Exception:
                pass
            try:
                view.removeEventFilter(self)
                if hasattr(view, "viewport"):
                    view.viewport().removeEventFilter(self)
            except Exception:
                pass
        if self._popup_header is not None:
            self._popup_header.hide()
        if self._popup_container is not None:
            try:
                self._popup_container.removeEventFilter(self)
            except Exception:
                pass
        self._popup_container = None

    # ----- Mouse handling on combo (display area) -----

    def _edit_field_rect(self):
        """Estimate the rectangle of the editable field area in the combo."""
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        return self.style().subControlRect(QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxEditField, self)

    def _arrow_rect(self):
        """Estimate the rectangle of the arrow area in the combo."""
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        return self.style().subControlRect(QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxArrow, self)

    def mousePressEvent(self, event):
        """
        Open popup on left-click anywhere in the combo area; let the arrow retain default toggle behaviour.

        :param event: QMouseEvent
        """
        if event.button() == Qt.LeftButton and self.isEnabled():
            arrow_rect = self._arrow_rect()
            if arrow_rect.contains(event.pos()):
                return super().mousePressEvent(event)
            if not self._popup_open:
                self.showPopup()
            event.accept()
            return
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        """
        Commit the highlighted item with Enter/Return while the popup is open.

        :param event: QKeyEvent
        """
        if self._popup_open:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self._commit_view_current()
                event.accept()
                return
            if event.key() == Qt.Key_Escape:
                event.accept()
                return
        super().keyPressEvent(event)

    # ----- Event filter -----

    def eventFilter(self, obj, event):
        """
        - Keep popup header sized with container.
        - Handle navigation/confirm keys in the header.
        - Handle Enter on the popup list as well.
        - Do not close popup on ESC.

        :param obj: QObject
        :param event: QEvent
        """
        if obj is self._popup_container and self._popup_container is not None:
            if event.type() in (QEvent.Resize, QEvent.Show):
                self._place_popup_header()
                return False

        if obj is self._popup_header:
            if event.type() == QEvent.KeyPress:
                key = event.key()
                if key == Qt.Key_Escape:
                    return True
                if key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_PageUp, Qt.Key_PageDown, Qt.Key_Home, Qt.Key_End):
                    self._handle_navigation_key(key)
                    return True
                if key in (Qt.Key_Return, Qt.Key_Enter):
                    self._commit_view_current()
                    return True
            return False

        view = self.view()
        if view is not None and (obj is view or obj is getattr(view, "viewport", lambda: None)()):
            if event.type() == QEvent.KeyPress:
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    self._commit_view_current()
                    return True
                if event.key() == Qt.Key_Escape:
                    return True
            return False

        return super().eventFilter(obj, event)

    # ----- Magnifier helpers -----

    def _ensure_magnifier_on(self, line_edit: QLineEdit | None):
        """
        Add magnifier icon to the given line edit if not already present.

        :param line_edit: QLineEdit
        """
        if line_edit is None:
            return
        try:
            icon = QIcon(self._search_icon_path)
            if icon.isNull():
                return
            if line_edit is self._search_line:
                if self._search_action is None:
                    self._search_action = line_edit.addAction(icon, QLineEdit.LeadingPosition)
            elif line_edit is self._popup_header:
                if self._popup_header_action is None:
                    self._popup_header_action = line_edit.addAction(icon, QLineEdit.LeadingPosition)
        except Exception:
            pass

    def _remove_magnifier_on(self, line_edit: QLineEdit | None):
        """
        Remove magnifier icon from the given line edit if present.

        :param line_edit: QLineEdit
        """
        if line_edit is None:
            return
        try:
            if line_edit is self._search_line and self._search_action is not None:
                line_edit.removeAction(self._search_action)
                self._search_action = None
            elif line_edit is self._popup_header and self._popup_header_action is not None:
                line_edit.removeAction(self._popup_header_action)
                self._popup_header_action = None
        except Exception:
            pass

    # ----- Clear button helper -----

    def _ensure_clear_button_visible(self, line_edit: QLineEdit | None):
        """
        Force-refresh clear button visibility to ensure the 'x' appears for programmatically restored text.

        :param line_edit: QLineEdit
        """
        if line_edit is None:
            return
        try:
            if line_edit.text():
                line_edit.setClearButtonEnabled(True)
                line_edit.update()
        except Exception:
            pass

    # ----- Display sync -----

    def _sync_editor_to_current(self):
        """Sync the persistent editor text to the currently selected combo value."""
        if self._search_line is None:
            return
        try:
            self._search_line.blockSignals(True)
            self._search_line.setText(self.currentText())
        finally:
            self._search_line.blockSignals(False)

    # ----- Search helpers -----

    def _find_target_row_for(self, needle_lower: str) -> int:
        """
        Find row for a given lowercase needle using priority:
        1) exact match, 2) prefix, 3) substring. Skips separators.
        Returns -1 if not found.

        :param needle_lower: lowercase search needle
        :return: target row index or -1
        """
        if needle_lower is None:
            return -1
        for row in range(self.count()):
            if self.is_separator(row):
                continue
            txt = (self.itemText(row) or "").strip().lower()
            if txt == needle_lower:
                return row
        for row in range(self.count()):
            if self.is_separator(row):
                continue
            txt = (self.itemText(row) or "").lower()
            if txt.startswith(needle_lower):
                return row
        for row in range(self.count()):
            if self.is_separator(row):
                continue
            txt = (self.itemText(row) or "").lower()
            if needle_lower in txt:
                return row
        return -1

    def _prefill_with_current_or_restore_last(self):
        """
        On popup open:
        1) Prefill header with the currently selected value (if any), scroll to it and store as last query.
        2) Otherwise, restore previously typed valid query and scroll to it.
        3) Otherwise, clear and scroll to first valid.
        """
        if not self._popup_header:
            return

        cur_idx = super().currentIndex()
        if cur_idx is not None and cur_idx >= 0:
            current_txt = (self.currentText() or "").strip()
            if current_txt:
                row = self._find_target_row_for(current_txt.lower())
                if row == -1:
                    row = self.first_valid_index()
                self._suppress_search = True
                self._popup_header.setText(current_txt)
                self._suppress_search = False
                self._last_query_text = current_txt
                self._ensure_clear_button_visible(self._popup_header)
                self._popup_header.setCursorPosition(len(current_txt))
                self._scroll_to_row(row)
                return

        last = (self._last_query_text or "").strip()
        if last:
            row = self._find_target_row_for(last.lower())
            if row != -1:
                self._suppress_search = True
                self._popup_header.setText(last)
                self._suppress_search = False
                self._ensure_clear_button_visible(self._popup_header)
                self._popup_header.setCursorPosition(len(last))
                self._scroll_to_row(row)
                return

        self._suppress_search = True
        self._popup_header.clear()
        self._suppress_search = False
        self._ensure_clear_button_visible(self._popup_header)
        self._scroll_to_row(self.first_valid_index())

    def _focus_header_async(self):
        """Focus the header immediately and again in the next event loop to ensure caret at the end."""
        if not self._popup_header:
            return
        self._popup_header.setFocus(Qt.OtherFocusReason)
        self._popup_header.setCursorPosition(len(self._popup_header.text()))
        self._ensure_clear_button_visible(self._popup_header)
        QTimer.singleShot(0, self._focus_header_end)

    def _focus_header_end(self):
        """Focus the header and place caret at the end."""
        if not self._popup_header:
            return
        self._popup_header.setFocus(Qt.OtherFocusReason)
        self._popup_header.setCursorPosition(len(self._popup_header.text()))
        self._ensure_clear_button_visible(self._popup_header)

    # ----- Search behaviour -----

    def _on_search_text_changed(self, text: str):
        """
        Handle search text changes: find target row and scroll to it.

        :param text: search text
        """
        if self._suppress_search:
            self._ensure_clear_button_visible(self._popup_header)
            return
        if not self._popup_open or not self.search:
            return

        raw = (text or "").strip()
        needle = raw.lower()
        target_row = -1

        if not raw:
            target_row = self.first_valid_index()
            self._last_query_text = ""
        else:
            target_row = self._find_target_row_for(needle)
            if target_row != -1:
                self._last_query_text = raw

        self._ensure_clear_button_visible(self._popup_header)

        if target_row != -1:
            self._scroll_to_row(target_row)

    def _scroll_to_row(self, row: int):
        """
        Scroll the popup list to place the given row at the top and highlight it.

        :param row: target row index
        """
        if row is None or row < 0:
            return
        view = self.view()
        if view is None:
            return
        try:
            model_index = self.model().index(row, self.modelColumn(), self.rootModelIndex())
        except Exception:
            return
        try:
            view.scrollTo(model_index, QAbstractItemView.PositionAtTop)
        except Exception:
            view.scrollTo(model_index)
        try:
            view.setCurrentIndex(model_index)
        except Exception:
            pass

    # ----- Keyboard navigation while header focused -----

    def _handle_navigation_key(self, key: int):
        """
        Handle navigation keys in the popup header to move highlight accordingly.

        :param key: navigation key (Qt.Key_*)
        """
        view = self.view()
        if view is None:
            return
        idx = view.currentIndex()
        row = idx.row() if idx.isValid() else self.first_valid_index()
        if row < 0:
            return

        if key == Qt.Key_Up:
            self._move_to_next_valid(row - 1, -1)
        elif key == Qt.Key_Down:
            self._move_to_next_valid(row + 1, +1)
        elif key == Qt.Key_PageUp:
            self._page_move(-1)
        elif key == Qt.Key_PageDown:
            self._page_move(+1)
        elif key == Qt.Key_Home:
            first = self.first_valid_index()
            if first != -1:
                self._scroll_to_row(first)
        elif key == Qt.Key_End:
            last = self.last_valid_index()
            if last != -1:
                self._scroll_to_row(last)

    def _row_height_hint(self) -> int:
        """
        Get an estimated row height for the popup list.

        :return: estimated row height in pixels
        """
        v = self.view()
        if v is None:
            return 20
        try:
            if self.count() > 0:
                h = v.sizeHintForRow(0)
                if h and h > 0:
                    return h
        except Exception:
            pass
        try:
            return max(18, v.fontMetrics().height() + 6)
        except Exception:
            return 20

    def _visible_rows_in_viewport(self) -> int:
        """
        Estimate how many rows fit in the current viewport height.

        :return: estimated number of visible rows
        """
        v = self.view()
        if v is None:
            return 10
        h = self._row_height_hint()
        try:
            viewport_h = max(1, v.viewport().height())
        except Exception:
            viewport_h = h * 10
        return max(1, viewport_h // max(1, h))

    def _page_move(self, direction: int):
        """
        Move highlight by one page up or down, skipping separators.

        :param direction: +1 for page down, -1 for page up
        """
        v = self.view()
        if v is None:
            return
        page_rows = max(1, self._visible_rows_in_viewport() - 1)
        idx = v.currentIndex()
        cur = idx.row() if idx.isValid() else self.first_valid_index()
        if cur < 0:
            return
        target = cur + (page_rows * (1 if direction >= 0 else -1))
        target = max(0, min(self.count() - 1, target))
        if direction >= 0:
            self._move_to_next_valid(target, +1)
        else:
            self._move_to_next_valid(target, -1)

    def _move_to_next_valid(self, start_row: int, step: int):
        """
        Move highlight to the next non-separator row from start_row in step direction.

        :param start_row: starting row index
        :param step: +1 to move down, -1 to move up
        """
        if self.count() <= 0:
            return
        row = start_row
        while 0 <= row < self.count():
            if not self.is_separator(row):
                self._scroll_to_row(row)
                return
            row += step

    def _commit_view_current(self):
        """Commit the currently highlighted row in the popup list and close the popup."""
        view = self.view()
        if view is None:
            return
        idx = view.currentIndex()
        row = idx.row() if idx.isValid() else self.first_valid_index()
        if row is None or row < 0:
            return
        if self.is_separator(row):
            forward = row + 1
            while forward < self.count() and self.is_separator(forward):
                forward += 1
            if forward < self.count():
                row = forward
            else:
                backward = row - 1
                while backward >= 0 and self.is_separator(backward):
                    backward -= 1
                if backward >= 0:
                    row = backward
                else:
                    return
        self.setCurrentIndex(row)
        self.hidePopup()

    # ----- Popup sizing (max height to window, compact when fewer items) -----

    def _apply_popup_max_rows(self):
        """Compute and set maxVisibleItems so the popup fits within the available window height."""
        try:
            view = self.view()
            if view is None:
                return
            total_rows = max(1, self.count())
            row_h = self._row_height_hint()
            header_h = self._popup_header_h \
                if (self.search and self._popup_open) else (self._popup_header_h if self.search else 0)

            win = self.window()
            if win is not None:
                try:
                    fg = win.frameGeometry()
                    win_top = fg.top()
                    win_bottom = fg.bottom()
                except Exception:
                    win_top = None
                    win_bottom = None
            else:
                win_top = None
                win_bottom = None

            if win_top is None or win_bottom is None:
                try:
                    scr = (self.window().screen() if self.window() is not None else self.screen())
                    ag = scr.availableGeometry() if scr is not None else None
                    if ag is not None:
                        win_top = ag.top()
                        win_bottom = ag.bottom()
                except Exception:
                    ag = None
            else:
                ag = None

            if win_top is None or win_bottom is None:
                max_rows_fit = 12
            else:
                bottom_global = self.mapToGlobal(self.rect().bottomLeft()).y()
                top_global = self.mapToGlobal(self.rect().topLeft()).y()

                space_down = win_bottom - bottom_global
                space_up = top_global - win_top

                usable_down = max(0, space_down - header_h - 8)
                usable_up = max(0, space_up - header_h - 8)
                max_px = max(usable_down, usable_up)
                max_rows_fit = max(1, int(max_px // max(1, row_h)))

            rows = min(total_rows, max_rows_fit)
            rows = max(1, rows)
            self.setMaxVisibleItems(rows)
        except Exception:
            pass


class NoScrollCombo(SearchableCombo):
    """A combo box that disables mouse wheel scrolling, extended with optional search support."""

    def __init__(self, parent=None):
        super(NoScrollCombo, self).__init__(parent)

    def wheelEvent(self, event):
        """
        Disable mouse wheel scrolling

        :param event: QWheelEvent
        """
        event.ignore()

    def showPopup(self):
        """Adjust popup width to fit the longest item before showing."""
        max_width = 0
        font_metrics = QFontMetrics(self.font())
        for i in range(self.count()):
            text = self.itemText(i)
            width = font_metrics.horizontalAdvance(text)
            max_width = max(max_width, width)
        extra_margin = 80
        max_width += extra_margin
        try:
            self.view().setMinimumWidth(max_width)
        except Exception:
            pass
        super().showPopup()


class OptionCombo(QWidget):
    """A combobox for selecting options in the settings."""

    def __init__(self, window=None, parent_id: str = None, id: str = None, option: dict = None):
        """
        Settings combobox

        :param window: main window
        :param id: option id
        :param parent_id: parent option id
        :param option: option data
        """
        super(OptionCombo, self).__init__(window)
        self.window = window
        self.id = id
        self.parent_id = parent_id
        self.option = option
        self.value = None
        self.keys = []
        self.title = ""
        self.real_time = False
        self.search = True

        self.combo = NoScrollCombo()
        self.combo.currentIndexChanged.connect(self.on_combo_change)
        self.current_id = None
        self.locked = False

        self.update()

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.combo)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.fit_to_content()

    def update(self):
        """Prepare items"""
        if self.option is not None:
            if "label" in self.option and self.option["label"] is not None and self.option["label"] != "":
                self.title = trans(self.option["label"])
            if "keys" in self.option:
                self.keys = self.option["keys"]
            if "value" in self.option:
                self.value = self.option["value"]
                self.current_id = self.value
            if "real_time" in self.option:
                self.real_time = self.option["real_time"]
            if "search" in self.option:
                self.search = bool(self.option["search"])

        try:
            self.combo.setSearchEnabled(self.search)
        except Exception:
            self.combo.search = self.search

        self.combo.clear()
        if type(self.keys) is list:
            for item in self.keys:
                if type(item) is dict:
                    for key, value in item.items():
                        if not isinstance(key, str):
                            key = str(key)
                        if key.startswith("separator::"):
                            self.combo.addSeparator(value)
                        else:
                            self.combo.addItem(value, key)
                else:
                    if isinstance(item, str) and item.startswith("separator::"):
                        self.combo.addSeparator(item.split("separator::", 1)[1])
                    else:
                        self.combo.addItem(item, item)
        elif type(self.keys) is dict:
            for key, value in self.keys.items():
                if not isinstance(key, str):
                    key = str(key)
                if key.startswith("separator::"):
                    self.combo.addSeparator(value)
                else:
                    self.combo.addItem(value, key)

        self._apply_initial_selection()

    def _apply_initial_selection(self):
        """
        Ensures that after building the list the combobox does not end up on a separator.
        Prefers self.current_id if present; otherwise selects the first valid non-separator.
        Signals are suppressed during this operation.
        """
        prev_locked = self.locked
        self.locked = True
        try:
            index = -1
            if self.current_id is not None and self.current_id != "":
                index = self.combo.findData(self.current_id)
            if index == -1:
                index = self.combo.first_valid_index()
            if index != -1:
                self.combo.setCurrentIndex(index)
            else:
                self.combo.setCurrentIndex(-1)
        finally:
            self.locked = prev_locked

    def set_value(self, value):
        """
        Set value

        :param value: value
        """
        if not value:
            return
        index = self.combo.findData(value)
        if index != -1:
            self.combo.setCurrentIndex(index)
        else:
            self.combo.ensure_valid_current()

    def get_value(self):
        """
        Get value

        :return: value
        """
        return self.current_id

    def set_keys(self, keys, lock: bool = False):
        """
        Set keys

        :param keys: keys
        :param lock: lock current value if True
        """
        if lock:
            self.locked = True
        self.keys = keys
        self.option["keys"] = keys
        self.combo.clear()
        self.update()
        self.combo.ensure_valid_current()
        if lock:
            self.locked = False

    def on_combo_change(self, index):
        """
        On combo change

        :param index: combo index
        :return:
        """
        if self.locked:
            return

        if self.combo.is_separator(index):
            self.locked = True
            corrected = self.combo.ensure_valid_current()
            self.locked = False
            if corrected == -1:
                self.current_id = None
                return
            index = corrected

        self.current_id = self.combo.itemData(index)
        self.window.controller.config.combo.on_update(self.parent_id, self.id, self.option, self.current_id)

    def fit_to_content(self):
        """Fit to content"""
        self.combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)