"""Native text editor with multiline syntax highlighting, without a web runtime."""
import os

from PySide6.QtCore import QTimer, Qt, QEvent, QRect
from PySide6.QtGui import QColor, QFontDatabase, QFontMetrics, QSyntaxHighlighter, QTextCharFormat, QPainter, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QDialog, QVBoxLayout, QLabel, QDialogButtonBox
from pygpt_net.core.text.finder import Finder
from pygpt_net.ui.widget.textarea.zoom import zoom_text
from pygpt_net.utils import trans
from pygments import lex
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound


LINE_NUMBER_PADDING = 10  # pixels on each side of the number
LINE_NUMBER_TEXT_GAP = 5  # pixels between the gutter and code
LINE_NUMBER_FONT_SCALE = 0.85  # relative to the editor font, follows zoom


class SyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, document, path, editor):
        super().__init__(document)
        try:
            self.lexer = get_lexer_for_filename(path, stripnl=False, ensurenl=False)
        except ClassNotFound:
            self.lexer = TextLexer(stripnl=False, ensurenl=False)
        self.editor = editor
        self.formats = {}
        self.spans = {}
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(180)
        self.timer.timeout.connect(self.refresh)
        document.contentsChange.connect(lambda pos, removed, added: self.timer.start() if removed or added else None)
        self.refresh()

    def refresh(self):
        dark = self.editor.palette().base().color().lightness() < 128
        signature = (self.document().toPlainText(), dark)
        if signature == getattr(self, '_signature', None):
            return
        self._signature = signature
        self.formats = {}
        style = get_style_by_name('monokai' if dark else 'default')
        self.spans = {}
        line, column = 0, 0
        for token, value in lex(self.document().toPlainText(), self.lexer):
            if token not in self.formats:
                spec = style.style_for_token(token)
                fmt = QTextCharFormat()
                if spec['color']:
                    fmt.setForeground(QColor('#' + spec['color']))
                fmt.setFontItalic(spec['italic'])
                self.formats[token] = fmt
            parts = value.split('\n')
            for i, part in enumerate(parts):
                # Qt positions count UTF-16 code units, not Python code points.
                length = len(part.encode('utf-16-le')) // 2
                self.spans.setdefault(line, []).append((column, length, self.formats[token]))
                column += length
                if i < len(parts) - 1:
                    line += 1
                    column = 0
        self.rehighlight()

    def highlightBlock(self, text):
        for start, length, fmt in self.spans.get(self.currentBlock().blockNumber(), []):
            self.setFormat(start, length, fmt)


class LineNumbers(QWidget):
    def number_font(self):
        font = self.parentWidget().font()
        if font.pixelSize() > 0:
            font.setPixelSize(max(1, round(font.pixelSize() * LINE_NUMBER_FONT_SCALE)))
        else:
            font.setPointSizeF(max(1, font.pointSizeF() * LINE_NUMBER_FONT_SCALE))
        return font

    def paintEvent(self, event):
        editor = self.parentWidget()
        painter = QPainter(self)
        dark = editor.palette().base().color().lightness() < 128
        painter.fillRect(event.rect(), QColor('#292b2e' if dark else '#f0f1f2'))
        painter.setFont(self.number_font())
        cursor = editor.textCursor()
        first = editor.document().findBlock(cursor.selectionStart()).blockNumber()
        # Selection end is exclusive: ending at the next line's start does not
        # select that line. Also works for selections dragged backwards.
        end = max(cursor.selectionStart(), cursor.selectionEnd() - 1)
        last = editor.document().findBlock(end).blockNumber()
        block = editor.firstVisibleBlock()
        while block.isValid():
            rect = editor.blockBoundingGeometry(block).translated(editor.contentOffset())
            if rect.top() > event.rect().bottom():
                break
            if block.isVisible() and rect.bottom() >= event.rect().top():
                current = first <= block.blockNumber() <= last
                annotated = any(start <= block.blockNumber() + 1 <= end
                                for start, end in editor.annotation_ranges)
                if annotated:
                    painter.fillRect(0, round(rect.top()), self.width(), round(rect.height()),
                                     QColor('#493f29' if dark else '#fff0cc'))
                if current:
                    painter.fillRect(0, round(rect.top()), self.width(), round(rect.height()),
                                     QColor('#3b424c' if dark else '#dce4ee'))
                if annotated:
                    # Keep the annotation visible even on selected/current lines.
                    painter.fillRect(0, round(rect.top()), 3, round(rect.height()),
                                     QColor('#e5b85c' if dark else '#b87b18'))
                painter.setPen(QColor(('#eef2f7' if dark else '#28384a') if current
                                      else ('#90949a' if dark else '#777c83')))
                painter.drawText(LINE_NUMBER_PADDING, round(rect.top()), self.width() - 2 * LINE_NUMBER_PADDING,
                                 editor.fontMetrics().height(), Qt.AlignRight | Qt.AlignVCenter,
                                 str(block.blockNumber() + 1))
            block = block.next()


class TextPreview(QPlainTextEdit):
    def __init__(self, panel, path, text):
        super().__init__(panel)
        self.panel = panel
        self.path = os.path.abspath(path)
        self.annotation_ranges = ()
        self.annotation_timer = QTimer(self)
        self.annotation_timer.setInterval(150)
        self.annotation_timer.timeout.connect(self.refresh_annotations)
        self.line_numbers = LineNumbers(self)
        self.blockCountChanged.connect(self.update_gutter)
        self.updateRequest.connect(self.update_gutter)
        self.cursorPositionChanged.connect(self.highlight_line)
        self.selectionChanged.connect(self.highlight_line)
        self.setObjectName('filesPreviewText')
        self.finder = Finder(panel.window, self)
        self.textChanged.connect(self.finder.text_changed)
        self.value = 12
        self.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setPlainText(text)
        self.restore_zoom()
        self.ensurePolished()
        self.highlighter = SyntaxHighlighter(self.document(), path, self)
        self.document().setModified(False)
        self.update_gutter()
        self.highlight_line()

    def update_gutter(self, *args):
        width = 2 * LINE_NUMBER_PADDING + QFontMetrics(self.line_numbers.number_font()).horizontalAdvance('9') * len(str(self.blockCount()))
        self.setViewportMargins(width + LINE_NUMBER_TEXT_GAP, 0, 0, 0)
        rect = self.contentsRect()
        self.line_numbers.setGeometry(QRect(rect.left(), rect.top(), width, rect.height()))
        self.line_numbers.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_gutter()

    def highlight_line(self):
        self.line_numbers.update()

    def annotation_session(self):
        window = self.panel.window
        return window.controller.chat.text.get_annotations(window.core.ctx.get_current_meta())

    def refresh_annotations(self):
        """Follow the active conversation, including removals after model delivery."""
        session = self.annotation_session()
        items = session.annotations if session is not None else []
        ranges = ()
        if items:
            path = os.path.relpath(self.path, self.panel.window.core.filesystem.get_data_dir()).replace(os.sep, '/')
            ranges = tuple((item['start_line'], item['end_line']) for item in items
                           if item.get('source') == 'files' and item.get('path') == path)
        if ranges != self.annotation_ranges:
            self.annotation_ranges = ranges
            self.line_numbers.update()

    def annotate(self, cursor):
        session = self.annotation_session()
        if session is None:
            return
        cursor = QTextCursor(cursor)
        if not cursor.hasSelection():
            cursor.select(QTextCursor.LineUnderCursor)
        start = self.document().findBlock(cursor.selectionStart()).blockNumber() + 1
        end = self.document().findBlock(max(cursor.selectionStart(), cursor.selectionEnd() - 1)).blockNumber() + 1
        selected = cursor.selection().toPlainText()
        workdir = self.panel.window.core.filesystem.get_data_dir()
        path = os.path.relpath(self.path, workdir).replace(os.sep, '/')
        dialog = QDialog(self)
        dialog.setWindowTitle(trans('ui.annotation_title', domain='plugin.canvas_web'))
        layout = QVBoxLayout(dialog)
        label = QLabel(f'{path}:{start}–{end}')
        label.setTextFormat(Qt.PlainText)
        label.setWordWrap(True)
        layout.addWidget(label)
        note = QPlainTextEdit(dialog)
        note.setPlaceholderText(trans('ui.annotation_selection_prompt', domain='plugin.canvas_web'))
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setEnabled(False)
        note.textChanged.connect(lambda: buttons.button(QDialogButtonBox.Save).setEnabled(bool(note.toPlainText().strip())))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.resize(420, 220)
        if dialog.exec() == QDialog.Accepted:
            session.add_file_annotation(path, start, end, selected, note.toPlainText())
            self.refresh_annotations()
        dialog.deleteLater()

    def restore_zoom(self):
        value = self.panel.window.core.config.get('font_size')
        self.value = max(8, min(42, value if isinstance(value, (int, float)) else 12))
        self.setStyleSheet(f"QPlainTextEdit {{ font-size: {self.value}px; }}")

    def on_zoom_changed(self, value):
        zoom_text(self, self.panel.window, value)

    def find_open(self):
        self.panel.window.controller.finder.open(self.finder)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F and event.modifiers() & Qt.ControlModifier:
            self.find_open()
            event.accept()
        else:
            super().keyPressEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.panel.window.controller.finder.focus_in(self.finder)

    def on_destroy(self):
        self.annotation_timer.stop()
        self.finder.timer.stop()
        self.highlighter.timer.stop()
        self.textChanged.disconnect(self.finder.text_changed)
        self.panel.window.controller.finder.unset(self.finder)
        self.finder.disconnect()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta:
                self.on_zoom_changed(self.value + (1 if delta > 0 else -1))
            event.accept()
        else:
            super().wheelEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.restore_zoom()
        self.highlighter.refresh()
        self.refresh_annotations()
        self.annotation_timer.start()

    def hideEvent(self, event):
        self.annotation_timer.stop()
        super().hideEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.PaletteChange, QEvent.StyleChange, QEvent.ApplicationPaletteChange, QEvent.FontChange):
            if hasattr(self, 'line_numbers'):
                self.update_gutter()
                self.highlight_line()
            if hasattr(self, 'highlighter'):
                self.highlighter.timer.start(0)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        cursor = self.textCursor() if self.textCursor().hasSelection() else self.cursorForPosition(event.pos())
        action = menu.addAction(trans('ui.annotate_selection', domain='plugin.canvas_web'),
                                lambda: self.annotate(cursor))
        session = self.annotation_session()
        action.setEnabled(session is not None)
        if session is not None:
            path = os.path.relpath(self.path, self.panel.window.core.filesystem.get_data_dir()).replace(os.sep, '/')
            items = [item for item in session.annotations if item.get('source') == 'files' and item.get('path') == path]
            if items:
                annotations = menu.addMenu(trans('ui.annotation_title', domain='plugin.canvas_web'))
                for item in items:
                    entry = annotations.addMenu(f"{item['start_line']}–{item['end_line']}: {item['note'][:60]}")
                    entry.setToolTip(item['note'])
                    entry.addAction(trans('ui.remove_annotation', domain='plugin.canvas_web'),
                                    lambda checked=False, aid=item['id']: session._remove_annotation(aid))
        self.panel.add_file_actions(menu)
        menu.addAction(trans('text.context_menu.find'), self.find_open)
        menu.addMenu(self.panel.window.ui.context_menu.get_copy_to_menu(
            menu, selected_text_provider=lambda: self.textCursor().selection().toPlainText()
            if self.textCursor().hasSelection() else self.toPlainText()))
        menu.addMenu(self.panel.window.ui.context_menu.get_zoom_menu(
            self, "editor", self.value, self.on_zoom_changed))
        menu.exec(event.globalPos())
        menu.deleteLater()
