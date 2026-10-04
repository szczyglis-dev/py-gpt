#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.10.04 00:00:00                  #
# ================================================== #
"""VT terminal display: ANSI cells, keyboard input and bounded scrollback."""
import math

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetricsF, QPainter, QKeySequence
from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QMenu
from pygpt_net.utils import trans
from ..core.process import TerminalProcess


class TerminalWidget(QAbstractScrollArea):
    colors = dict(black='#202020', red='#cd3131', green='#0dbc79', brown='#e5e510',
                  blue='#2472c8', magenta='#bc3fbc', cyan='#11a8cd', white='#e5e5e5')

    def __init__(self, tool, parent=None):
        super().__init__(parent)
        self.tool = tool
        self.tab = None
        self.closed = False
        self.screen = None
        self.offset = 0
        self.error = ''
        self.apply_theme()
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_InputMethodEnabled)
        self.viewport().setFocusProxy(self)
        self.viewport().setFocusPolicy(Qt.StrongFocus)
        self.viewport().setCursor(Qt.IBeamCursor)
        self.setFrameShape(QAbstractScrollArea.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.verticalScrollBar().valueChanged.connect(self.scroll_changed)
        self.cursor_visible = True
        self.cursor_timer = QTimer(self)
        self.cursor_timer.setInterval(500)
        self.cursor_timer.timeout.connect(self.blink_cursor)
        self.padding = 12
        available = set(QFontDatabase.families())
        family = next((name for name in ('DejaVu Sans Mono', 'Menlo', 'Consolas', 'Liberation Mono')
                       if name in available), QFontDatabase.systemFont(QFontDatabase.FixedFont).family())
        self.terminal_font = QFont(family)
        self.selection_anchor = None
        self.selection_end = None
        self.dragging = False
        self.font_cache = {}
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.setInterval(30)
        self.resize_timer.timeout.connect(self.sync_size)
        self.terminal_font.setStyleHint(QFont.Monospace)
        self.terminal_font.setFixedPitch(True)
        config = getattr(getattr(getattr(tool, 'window', None), 'core', None), 'config', None)
        size = config.get('terminal.font_size', config.get('font_size')) if config is not None else 14
        self.apply_font(size if isinstance(size, (int, float)) else 14)
        self.process = TerminalProcess(self)
        self.process.output.connect(self.feed)
        self.process.finished.connect(self.exited)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.start)
        self.timer.start(0)

    def set_tab(self, tab):
        self.tab = tab

    def dimensions(self):
        return (max(2, int((self.viewport().height() - 2 * self.padding) // self.cell_height)),
                max(2, int((self.viewport().width() - 2 * self.padding) // self.cell_width)))

    def start(self):
        if self.closed:
            return
        try:
            import pyte
            rows, columns = self.dimensions()
            if not self.usable_size():
                rows, columns = 24, 80
            from ..core.screen import TerminalScreen
            self.screen = TerminalScreen(columns, rows, history=2000)
            self.screen.write_process_input = self.process.write
            self.stream = pyte.Stream(self.screen)
            self.process.start(self.tool.window.core.filesystem.get_data_dir(), rows, columns)
        except Exception as exc:
            self.error = str(exc)
            self.process.close()
        self.viewport().update()

    def feed(self, text):
        if self.closed or self.screen is None:
            return
        self.offset = 0
        self.stream.feed(text)
        self.sync_scrollbar()
        self.viewport().update()

    def exited(self):
        self.error = '[Process exited]'
        self.viewport().update()

    def showEvent(self, event):
        super().showEvent(event)
        self.queue_resize()
        QTimer.singleShot(0, self.focus_terminal)

    def focus_terminal(self):
        if not self.closed and self.isVisible():
            self.setFocus(Qt.OtherFocusReason)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.queue_resize()

    def queue_resize(self):
        # Throttle, rather than debounce: update throughout a splitter drag.
        if not self.resize_timer.isActive():
            self.resize_timer.start()

    def usable_size(self):
        rows, columns = self.dimensions()
        return self.isVisible() and rows >= 4 and columns >= 20

    def hideEvent(self, event):
        self.resize_timer.stop()
        super().hideEvent(event)

    def sync_size(self):
        if self.screen is not None and not self.closed and self.usable_size():
            rows, columns = self.dimensions()
            if (rows, columns) != (self.screen.lines, self.screen.columns):
                self.screen.resize(lines=rows, columns=columns)
                self.offset = min(self.offset, len(self.screen.history.top))
                self.selection_anchor = self.selection_end = None
                self.viewport().update()
                self.process.resize(rows, columns)
            self.sync_scrollbar()

    def displayed(self):
        if self.screen is None:
            return []
        lines = list(self.screen.history.top) + [self.screen.buffer[y] for y in range(self.screen.lines)]
        end = len(lines) - self.offset
        return lines[max(0, end - self.screen.lines):end]

    def color(self, value, foreground=True):
        if value == 'default':
            return self.foreground if foreground else self.background
        return QColor(self.colors.get(value, '#' + value))

    def apply_theme(self):
        window = getattr(self.tool, 'window', None)
        common = getattr(getattr(getattr(window, 'controller', None), 'theme', None), 'common', None)
        light = common is not None and common.is_light_theme_id(window.core.config.get('theme'))
        self.foreground = QColor('#000000' if light else '#eeeeee')
        self.background = QColor('#ffffff' if light else '#171717')
        self.error_color = QColor('#b00020' if light else '#ff8080')
        self.viewport().update()

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.fillRect(self.viewport().rect(), self.background)
        fm = self.metrics
        width, height = self.cell_width, self.cell_height
        painter.translate(self.padding, self.padding)
        for y, line in enumerate(self.displayed()):
            if (y + 1) * height + self.padding < event.rect().top() or y * height + self.padding > event.rect().bottom():
                continue
            runs = []
            for x in range(self.screen.columns):
                cell = line[x]
                foreground, background = cell.fg, cell.bg
                selected = self.is_selected(y, x)
                key = (foreground, background, cell.bold, cell.italics, cell.underscore, selected, cell.reverse)
                if runs and runs[-1][1] == key:
                    runs[-1][2].append(cell.data)
                else:
                    runs.append((x, key, [cell.data]))
            for x, key, characters in runs:
                foreground, background, bold, italic, underline, selected, reverse = key
                fg, bg = self.color(foreground), self.color(background, False)
                if reverse:
                    fg, bg = bg, fg
                if selected:
                    fg, bg = QColor('#ffffff'), QColor('#365b80')
                style = (bold, italic, underline)
                font = self.font_cache.get(style)
                if font is None:
                    font = QFont(self.terminal_font)
                    font.setBold(bold)
                    font.setItalic(italic)
                    font.setUnderline(underline)
                    self.font_cache[style] = font
                painter.fillRect(math.floor(x * width), y * height, math.ceil(len(characters) * width), height, bg)
                painter.setFont(font)
                painter.setPen(fg)
                painter.drawText(round(x * width), round(y * height + fm.ascent() + 1), ''.join(characters))
        if self.screen is not None and self.hasFocus() and not self.offset and not self.screen.cursor.hidden and self.cursor_visible:
            painter.setPen(self.foreground)
            x, y = self.screen.cursor.x, self.screen.cursor.y
            painter.fillRect(round(x * width), y * height, math.ceil(width), height, self.foreground)
            painter.setFont(self.terminal_font)
            painter.setPen(self.background)
            painter.drawText(round(x * width), round(y * height + fm.ascent() + 1), self.screen.buffer[y][x].data)
        if self.error:
            painter.setPen(self.error_color)
            painter.setFont(self.terminal_font)
            painter.drawText(0, round(self.viewport().height() - 2 * self.padding - fm.descent()), self.error)

    def apply_font(self, value):
        self.value = max(8, min(42, int(value)))
        if self.terminal_font.pixelSize() == self.value:
            return
        self.font_cache.clear()
        self.terminal_font.setPixelSize(self.value)
        self.setFont(self.terminal_font)
        self.metrics = QFontMetricsF(self.terminal_font)
        self.cell_width = self.metrics.horizontalAdvance('M')
        self.cell_height = math.ceil(self.metrics.height()) + 2
        if self.screen is not None:
            self.queue_resize()
        self.viewport().update()

    def on_zoom_changed(self, value):
        from pygpt_net.ui.widget.textarea.zoom import schedule_zoom
        self.apply_font(value)
        schedule_zoom(self.tool.window, 'terminal.font_size', self.value)

    def sync_scrollbar(self):
        if self.screen is None:
            return
        bar = self.verticalScrollBar()
        maximum = len(self.screen.history.top)
        from PySide6.QtCore import QSignalBlocker
        blocker = QSignalBlocker(bar)
        bar.setRange(0, maximum)
        bar.setPageStep(self.screen.lines)
        bar.setValue(maximum - min(self.offset, maximum))
        del blocker

    def scroll_changed(self, value):
        self.offset = self.verticalScrollBar().maximum() - value
        self.viewport().update()

    def blink_cursor(self):
        self.cursor_visible = not self.cursor_visible
        if self.screen is not None:
            from PySide6.QtCore import QRect
            self.viewport().update(QRect(round(self.padding + self.screen.cursor.x * self.cell_width),
                                         self.padding + self.screen.cursor.y * self.cell_height,
                                         math.ceil(self.cell_width), self.cell_height))

    def mousePressEvent(self, event):
        self.setFocus(Qt.MouseFocusReason)
        self.cursor_visible = True
        if event.button() == Qt.LeftButton:
            self.selection_anchor = self.selection_end = self.cell_at(event.position())
            self.dragging = True
        self.viewport().update()
        event.accept()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                self.on_zoom_changed(self.value + (1 if delta > 0 else -1))
            event.accept()
            return
        if self.screen is not None:
            self.offset = max(0, min(len(self.screen.history.top), self.offset + event.angleDelta().y() // 40))
            self.sync_scrollbar()
            self.viewport().update()
        event.accept()

    def paste(self):
        text = QApplication.clipboard().text().replace('\r\n', '\n').replace('\n', '\r')
        if self.screen is not None and (2004 << 5) in self.screen.mode:
            text = '\x1b[200~' + text + '\x1b[201~'
        self.process.write(text)

    def all_lines(self):
        if self.screen is None:
            return []
        return list(self.screen.history.top) + [self.screen.buffer[y] for y in range(self.screen.lines)]

    def cell_at(self, position):
        if self.screen is None:
            return (0, 0)
        row = max(0, min(self.screen.lines - 1, int((position.y() - self.padding) // self.cell_height)))
        column = max(0, min(self.screen.columns, int((position.x() - self.padding) // self.cell_width)))
        start = len(self.all_lines()) - self.offset - self.screen.lines
        return (max(0, start + row), column)

    def has_selection(self):
        return self.selection_anchor is not None and self.selection_end != self.selection_anchor

    def is_selected(self, row, column):
        if not self.has_selection():
            return False
        start, end = sorted((self.selection_anchor, self.selection_end))
        absolute = len(self.screen.history.top) - self.offset + row
        return start <= (absolute, column) < end

    def selected_text(self):
        if not self.has_selection():
            return ''
        start, end = sorted((self.selection_anchor, self.selection_end))
        result = []
        for row, line in enumerate(self.all_lines()):
            if start[0] <= row <= end[0]:
                left = start[1] if row == start[0] else 0
                right = end[1] if row == end[0] else self.screen.columns
                result.append(''.join(line[x].data for x in range(left, right)).rstrip())
        return '\n'.join(result)

    def select_all(self):
        lines = self.all_lines()
        if lines:
            self.selection_anchor = (0, 0)
            self.selection_end = (len(lines) - 1, self.screen.columns)
            self.viewport().update()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.selection_end = self.cell_at(event.position())
            self.viewport().update()
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.dragging:
                self.selection_end = self.cell_at(event.position())
            self.dragging = False
        self.viewport().update()
        event.accept()

    def copy(self):
        if self.has_selection():
            QApplication.clipboard().setText(self.selected_text())

    def build_context_menu(self):
        menu = QMenu(self)
        copy = menu.addAction(trans('action.copy'), self.copy)
        copy.setEnabled(self.has_selection())
        menu.addAction(trans('action.paste'), self.paste)
        menu.addAction(trans('action.select_all'), self.select_all)
        menu.addSeparator()
        menu.addMenu(self.tool.window.ui.context_menu.get_zoom_menu(
            self, 'editor', self.value, self.on_zoom_changed))
        return menu

    def contextMenuEvent(self, event):
        menu = self.build_context_menu()
        menu.exec(event.globalPos())
        menu.deleteLater()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            event.accept()
            return
        mods = event.modifiers()
        if mods & Qt.ControlModifier and mods & Qt.ShiftModifier:
            if event.key() == Qt.Key_A:
                self.select_all()
                return
            if event.key() == Qt.Key_C:
                self.copy()
                return
            if event.key() == Qt.Key_V:
                self.paste()
                return
        if event.matches(QKeySequence.Paste) and event.key() == Qt.Key_Insert:
            self.paste()
            return
        keys = {Qt.Key_Return:'\r', Qt.Key_Enter:'\r', Qt.Key_Backspace:'\x7f',
                Qt.Key_Tab:'\t', Qt.Key_Backtab:'\x1b[Z', Qt.Key_Escape:'\x1b',
                Qt.Key_Up:'\x1b[A', Qt.Key_Down:'\x1b[B', Qt.Key_Right:'\x1b[C',
                Qt.Key_Left:'\x1b[D', Qt.Key_Home:'\x1b[H', Qt.Key_End:'\x1b[F',
                Qt.Key_Delete:'\x1b[3~', Qt.Key_Insert:'\x1b[2~',
                Qt.Key_PageUp:'\x1b[5~', Qt.Key_PageDown:'\x1b[6~'}
        function_keys = ['OP', 'OQ', 'OR', 'OS', '[15~', '[17~', '[18~', '[19~', '[20~', '[21~', '[23~', '[24~']
        for index, sequence in enumerate(function_keys):
            keys[Qt.Key_F1 + index] = '\x1b' + sequence
        text = keys.get(event.key(), event.text())
        if self.screen is not None and (1 << 5) in self.screen.mode and event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Right, Qt.Key_Left):
            text = text.replace('[', 'O')
        if mods & Qt.ControlModifier and Qt.Key_A <= event.key() <= Qt.Key_Z:
            text = chr(event.key() - Qt.Key_A + 1)
        elif mods & Qt.AltModifier:
            text = '\x1b' + text
        self.selection_anchor = self.selection_end = None
        self.offset = 0
        self.sync_scrollbar()
        self.cursor_visible = True
        self.cursor_timer.start()
        self.process.write(text)
        event.accept()

    def inputMethodEvent(self, event):
        self.process.write(event.commitString())
        event.accept()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.cursor_visible = True
        self.cursor_timer.start()
        self.viewport().update()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.cursor_timer.stop()
        self.viewport().update()

    def on_delete(self):
        if self.closed:
            return
        self.closed = True
        self.timer.stop()
        self.cursor_timer.stop()
        self.resize_timer.stop()
        self.process.close()
        self.tool.unregister_surface(self)
        self.tool.widgets.remove(self)
