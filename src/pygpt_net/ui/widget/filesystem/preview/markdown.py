"""Built-in Markdown preview with local images and relative links."""
import os

from PySide6.QtCore import QUrl, Qt, QEvent
from PySide6.QtGui import QDesktopServices, QTextDocument, QTextBlockFormat, QTextCursor, QTextCharFormat, QColor, QPalette
from PySide6.QtWidgets import QTextBrowser, QFrame

from .readers import TextReader


class MarkdownPreview(QTextBrowser):
    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("QTextBrowser { border: none; }")
        self._links_ready = False
        self._wheel_delta = 0
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.document().setBaseUrl(QUrl.fromLocalFile(os.path.dirname(path) + os.sep))
        text, _ = TextReader().read(path)
        self.document().setMarkdown(text, QTextDocument.MarkdownDialectGitHub)
        self._apply_spacing()
        self.ensurePolished()
        self._restore_zoom()
        self._links_ready = True
        self._apply_link_colors()
        self.anchorClicked.connect(self._open_link)

    def _apply_spacing(self):
        block = self.document().begin()
        while block.isValid():
            cursor = QTextCursor(block)
            fmt = block.blockFormat()
            fmt.setLineHeight(140, QTextBlockFormat.ProportionalHeight.value)
            if fmt.headingLevel():
                fmt.setTopMargin(14 if block.blockNumber() else 0)
                fmt.setBottomMargin(8)
            elif block.textList() is not None:
                fmt.setBottomMargin(4)
            else:
                fmt.setBottomMargin(10)
            cursor.setBlockFormat(fmt)
            block = block.next()

    def _set_zoom(self, size):
        # Keep the widget font in sync: Qt reapplies it to the document on show
        # and stylesheet changes, overriding a document-only font adjustment.
        font = self.font()
        font.setPointSizeF(max(6, min(48, size)))
        if self.font() != font:
            self.setFont(font)
        self.document().setDefaultFont(font)

    def _restore_zoom(self):
        window = getattr(self.parentWidget(), 'window', None)
        config = getattr(getattr(window, 'core', None), 'config', None)
        if config is not None:
            size = config.get('filesystem.preview.markdown.font_size', 0)
            if isinstance(size, (int, float)) and size > 0:
                self._set_zoom(size)

    def showEvent(self, event):
        super().showEvent(event)
        self._restore_zoom()

    def _apply_link_colors(self):
        light = self.palette().color(QPalette.Base).lightness() > 140
        try:
            window = self.parentWidget().window
            theme = window.core.config.get('theme')
            kind = window.controller.theme.common.get_theme_type(theme)
            if isinstance(kind, str):
                light = kind == 'light'
        except (AttributeError, TypeError):
            pass
        color = QColor('#154c96' if light else '#80caff')
        document = self.document()
        block = document.begin()
        while block.isValid():
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                if fragment.isValid() and fragment.charFormat().isAnchor():
                    cursor = QTextCursor(document)
                    cursor.setPosition(fragment.position())
                    cursor.setPosition(fragment.position() + fragment.length(), QTextCursor.KeepAnchor)
                    fmt = QTextCharFormat()
                    fmt.setForeground(color)
                    cursor.mergeCharFormat(fmt)
                iterator += 1
            block = block.next()

    def changeEvent(self, event):
        super().changeEvent(event)
        if getattr(self, '_links_ready', False) and event.type() in (QEvent.PaletteChange, QEvent.StyleChange):
            self._apply_link_colors()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self._wheel_delta += event.angleDelta().y()
            steps = int(self._wheel_delta / 120)
            if steps:
                self._wheel_delta -= steps * 120
                size = self.document().defaultFont().pointSizeF()
                if size <= 0:
                    size = 10
                self._set_zoom(size + steps)
                window = getattr(self.parentWidget(), 'window', None)
                config = getattr(getattr(window, 'core', None), 'config', None)
                if config is not None:
                    config.set('filesystem.preview.markdown.font_size', self.document().defaultFont().pointSizeF())
                    config.save()
            event.accept()
            return
        super().wheelEvent(event)

    def _open_link(self, url):
        if not url.path() and url.fragment():
            self.scrollToAnchor(url.fragment())
            return
        resolved = self.document().baseUrl().resolved(url)
        if resolved.isLocalFile():
            self.parentWidget().open_file(resolved.toLocalFile())
        elif resolved.scheme() in ('http', 'https', 'mailto'):
            QDesktopServices.openUrl(resolved)
