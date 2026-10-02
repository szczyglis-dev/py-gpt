"""Attachment thumbnails embedded in the chat composer."""
import os
from functools import partial

from PySide6.QtCore import Qt, QRect, QFile, QSize, QEvent, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap, QIcon, QImageReader
from PySide6.QtWidgets import QWidget, QScrollArea, QHBoxLayout, QToolButton


class AttachmentTile(QWidget):
    SIDE = 104

    def __init__(self, window, item, remove, open_attachment, parent=None):
        super().__init__(parent)
        self.window = window
        self.open_attachment = open_attachment
        self.setCursor(Qt.PointingHandCursor)
        self.name = item.name or os.path.basename(item.path or '')
        self.setFixedSize(self.SIDE, self.SIDE)
        self.setToolTip(item.path or self.name)
        reader = QImageReader(item.path or '')
        self.image = QPixmap()
        if reader.canRead():
            size = reader.size()
            if size.isValid():
                reader.setScaledSize(size.scaled(QSize(160, 160), Qt.KeepAspectRatio))
            reader.setAutoTransform(True)
            self.image = QPixmap.fromImage(reader.read())
        ext = os.path.splitext(item.path or self.name)[1].lower().lstrip('.')
        icon = ext if ext and QFile.exists(f':/filetypes/{ext}.svg') else 'default'
        self.icon = QIcon(f':/filetypes/{icon}.svg')
        self.close = QToolButton(self)
        self.close.setGeometry(self.SIDE - 22, 2, 20, 20)
        self.close.setCursor(Qt.PointingHandCursor)
        self.close.setFocusPolicy(Qt.NoFocus)
        # Tint the existing close SVG white independently of the active theme.
        pixmap = QIcon(':/icons/close.svg').pixmap(12, 12)
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), Qt.white)
        painter.end()
        self.close.setIcon(QIcon(pixmap))
        self.close.setIconSize(QSize(12, 12))
        self.close.setStyleSheet('QToolButton { background: #111; border: none; border-radius: 10px; padding: 0; margin: 0; } QToolButton:hover { background: #444; }')
        self.close.clicked.connect(remove)
        font = self.font()
        font.setPixelSize(10)
        self.setFont(font)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.open_attachment(not self.image.isNull())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        light = self.window.controller.theme.common.is_light_theme_id(self.window.core.config.get('theme', 'dark'))
        background = QColor('#f5f5f5' if light else '#303030')
        border = QColor('#d2d2d2' if light else '#505050')
        band = QColor('#e8e8e8' if light else '#252525')
        text = QColor('#444444' if light else '#dddddd')
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0.5, 0.5, self.SIDE - 1, self.SIDE - 1, 8, 8)
        painter.setClipPath(path)
        painter.fillRect(self.rect(), background)
        if not self.image.isNull():
            image = self.image.scaled(self.SIDE, self.SIDE, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter.drawPixmap((self.SIDE - image.width()) // 2, (self.SIDE - image.height()) // 2, image)
        else:
            self.icon.paint(painter, QRect((self.SIDE - 40) // 2, (self.SIDE - 19 - 40) // 2, 40, 40))
        painter.fillRect(QRect(0, self.SIDE - 19, self.SIDE, 19), band)
        painter.setPen(text)
        painter.setFont(self.font())
        # Use three literal dots for clipped filenames.
        name = self.name
        if self.fontMetrics().horizontalAdvance(name) > self.SIDE - 8:
            while name and self.fontMetrics().horizontalAdvance(name + '...') > self.SIDE - 8:
                name = name[:-1]
            name += '...'
        painter.drawText(QRect(4, self.SIDE - 19, self.SIDE - 8, 19), Qt.AlignCenter, name)
        painter.setPen(border)
        painter.drawPath(path)
        painter.end()


class InputAttachments(QScrollArea):
    """Project the existing attachment store; never own a second file list."""
    heightChanged = Signal(int)
    ROW_HEIGHT = AttachmentTile.SIDE + 20

    def __init__(self, window, parent):
        super().__init__(parent)
        self.window = window
        self.sent = set()
        self.mode = None
        self.signature = None
        self.setFrameShape(QScrollArea.NoFrame)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet('QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; } QScrollBar:horizontal { height: 6px; margin: 0; }')
        self.content = QWidget()
        self.row = QHBoxLayout(self.content)
        self.row.setContentsMargins(0, 0, 0, 0)
        self.row.setSpacing(8)
        self.row.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setWidget(self.content)
        self.hide()

    def sync(self, items, mode):
        if mode != self.mode:
            self.sent.clear()
            self.mode = mode
        self.sent.intersection_update(items)
        visible = [(key, item) for key, item in items.items() if key not in self.sent]
        signature = tuple((key, item.path, item.name) for key, item in visible)
        if signature == self.signature:
            return
        self.signature = signature
        while self.row.count():
            widget = self.row.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        for key, item in visible:
            self.row.addWidget(AttachmentTile(self.window, item, partial(self.remove_attachment, key), partial(self.open_attachment, key), self.content))
        self.content.setMinimumWidth(max(0, len(visible) * (AttachmentTile.SIDE + self.row.spacing()) - self.row.spacing()))
        self.setVisible(bool(visible))
        self.heightChanged.emit(self.ROW_HEIGHT if visible else 0)

    def open_attachment(self, key, is_image):
        item = self.window.core.attachments.get_all(self.mode).get(key)
        if item is None or not item.path:
            return
        if is_image:
            self.window.tools.get("viewer").open_preview(item.path)
        else:
            self.window.controller.files.open(path=item.path)

    def remove_attachment(self, key):
        # Resolve the current index on click, rather than retaining a stale index.
        items = self.window.core.attachments.get_all(self.mode)
        if key in items:
            self.window.controller.attachment.delete(list(items).index(key), force=True, remove_local=False)

    def mark_sent(self):
        self.sent.update(self.window.core.attachments.get_all(self.mode))
        self.signature = None
        self.sync(self.window.core.attachments.get_all(self.mode), self.mode)

    def changeEvent(self, event):
        super().changeEvent(event)
        if hasattr(self, "content") and event.type() in (QEvent.PaletteChange, QEvent.StyleChange):
            self.content.update()
            for tile in self.content.findChildren(AttachmentTile):
                tile.update()
