"""Native text editor with multiline syntax highlighting, without a web runtime."""
from PySide6.QtCore import QTimer, Qt, QEvent
from PySide6.QtGui import QColor, QFontDatabase, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QPlainTextEdit
from pygments import lex
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound


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


class TextPreview(QPlainTextEdit):
    def __init__(self, panel, path, text):
        super().__init__(panel)
        self.panel = panel
        self.value = 12
        self.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setPlainText(text)
        self.restore_zoom()
        self.ensurePolished()
        self.highlighter = SyntaxHighlighter(self.document(), path, self)
        self.document().setModified(False)

    def restore_zoom(self):
        value = self.panel.window.core.config.get('font_size')
        self.value = max(8, min(42, value if isinstance(value, (int, float)) else 12))
        self.setStyleSheet(f"QPlainTextEdit {{ font-size: {self.value}px; }}")

    def on_zoom_changed(self, value):
        self.value = max(8, min(42, int(value)))
        window = self.panel.window
        window.core.config.set('font_size', self.value)
        window.core.config.save()
        option = window.controller.settings.editor.get_option('font_size')
        option['value'] = self.value
        window.controller.config.apply(parent_id='config', key='font_size', option=option)
        window.controller.ui.update_font_size()
        self.setStyleSheet(f"QPlainTextEdit {{ font-size: {self.value}px; }}")

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

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.PaletteChange, QEvent.StyleChange, QEvent.ApplicationPaletteChange):
            if hasattr(self, 'highlighter'):
                self.highlighter.timer.start(0)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        self.panel.add_file_actions(menu)
        menu.addMenu(self.panel.window.ui.context_menu.get_copy_to_menu(
            menu, selected_text_provider=lambda: self.textCursor().selection().toPlainText()
            if self.textCursor().hasSelection() else self.toPlainText()))
        menu.addMenu(self.panel.window.ui.context_menu.get_zoom_menu(
            self, "editor", self.value, self.on_zoom_changed))
        menu.exec(event.globalPos())
        menu.deleteLater()
