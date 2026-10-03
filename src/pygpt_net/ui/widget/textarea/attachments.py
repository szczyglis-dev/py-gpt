"""Attachment thumbnails embedded in the chat composer."""
import os
from functools import partial

from PySide6.QtCore import Qt, QRect, QFile, QSize, QEvent, Signal, QMimeData
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap, QIcon, QImageReader, QDrag
from PySide6.QtWidgets import QWidget, QScrollArea, QHBoxLayout, QToolButton, QApplication
from pygpt_net.utils import is_image


class AttachmentTile(QWidget):
    SIDE = 104
    MIME_TYPE = 'application/x-pygpt-composer-attachment'

    def __init__(self, window, item, remove, open_attachment, parent=None):
        super().__init__(parent)
        self.window = window
        self.open_attachment = open_attachment
        self.attachment_key = None
        self._drag_start = None
        self.setCursor(Qt.PointingHandCursor)
        self.name = item.name or os.path.basename(item.path or '')
        self.is_image_file = is_image(item.path or self.name)
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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.position().toPoint()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (self._drag_start is not None and event.buttons() & Qt.LeftButton
                and self.attachment_key is not None
                and (event.position().toPoint() - self._drag_start).manhattanLength()
                >= QApplication.startDragDistance()):
            self._drag_start = None
            drag = QDrag(self)
            mime = QMimeData()
            mime.setData(self.MIME_TYPE, str(self.attachment_key).encode('utf-8'))
            drag.setMimeData(mime)
            drag.setPixmap(self.grab())
            drag.setHotSpot(event.position().toPoint())
            drag.exec(Qt.MoveAction)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        clicked = self._drag_start is not None
        self._drag_start = None
        if clicked and event.button() == Qt.LeftButton and self.rect().contains(event.position().toPoint()):
            self.open_attachment(not self.image.isNull())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        light = self.window.controller.theme.common.is_light_theme_id(self.window.core.config.get('theme', 'dark'))
        background = QColor('#f5f5f5')
        band = QColor('#e8e8e8' if light else '#252525')
        text = QColor('#444444' if light else '#dddddd')
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.SIDE, self.SIDE, 8, 8)
        painter.setClipPath(path)
        # Qt can decode document previews too (e.g. PDF). Only image files
        # should lose the backing; documents keep a white page background.
        if not self.is_image_file:
            painter.fillRect(self.rect(), background)
        if not self.image.isNull():
            image = self.image.scaled(self.SIDE, self.SIDE, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter.drawPixmap((self.SIDE - image.width()) // 2, (self.SIDE - image.height()) // 2, image)
        else:
            if self.is_image_file:
                painter.fillRect(self.rect(), background)
            self.icon.paint(painter, QRect((self.SIDE - 40) // 2, (self.SIDE - 19 - 40) // 2, 40, 40))
        if self.image.isNull():
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
        self.setAcceptDrops(True)
        self.drop_marker = QWidget(self.content)
        self.drop_marker.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.drop_marker.setStyleSheet('background: #55bb88; border-radius: 1px;')
        self.drop_marker.hide()
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
            tile = AttachmentTile(self.window, item, partial(self.remove_attachment, key), partial(self.open_attachment, key), self.content)
            tile.attachment_key = key
            self.row.addWidget(tile)
        self.content.setMinimumWidth(max(0, len(visible) * (AttachmentTile.SIDE + self.row.spacing()) - self.row.spacing()))
        self.setVisible(bool(visible))
        self.heightChanged.emit(self.ROW_HEIGHT if visible else 0)

    def _accept_reorder(self, event):
        source = event.source()
        return (isinstance(source, AttachmentTile) and source.parentWidget() is self.content
                and event.mimeData().hasFormat(AttachmentTile.MIME_TYPE))

    def _drop_index(self, position):
        x = self.content.mapFrom(self.viewport(), position.toPoint()).x()
        for index in range(self.row.count()):
            if x < self.row.itemAt(index).widget().geometry().center().x():
                return index
        return self.row.count()

    def dragEnterEvent(self, event):
        if self._accept_reorder(event):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if not self._accept_reorder(event):
            event.ignore()
            return
        bar = self.horizontalScrollBar()
        x = event.position().x()
        if x < 24:
            bar.setValue(bar.value() - 16)
        elif x > self.viewport().width() - 24:
            bar.setValue(bar.value() + 16)
        index = self._drop_index(event.position())
        marker_x = (self.row.itemAt(index).widget().x() if index < self.row.count()
                    else self.row.itemAt(self.row.count() - 1).widget().geometry().right() - 1)
        self.drop_marker.setGeometry(max(0, marker_x - 3), 0, 3, AttachmentTile.SIDE)
        self.drop_marker.show()
        self.drop_marker.raise_()
        event.setDropAction(Qt.MoveAction)
        event.accept()

    def dragLeaveEvent(self, event):
        self.drop_marker.hide()
        event.accept()

    def dropEvent(self, event):
        self.drop_marker.hide()
        if not self._accept_reorder(event):
            event.ignore()
            return
        self.move_attachment(event.source().attachment_key, self._drop_index(event.position()))
        event.setDropAction(Qt.MoveAction)
        event.accept()

    def move_attachment(self, key, index):
        items = self.window.core.attachments.get_all(self.mode)
        visible = [item_key for item_key in items if item_key not in self.sent]
        if key not in visible:
            return
        previous = visible.index(key)
        visible.pop(previous)
        visible.insert(max(0, min(len(visible), index - (previous < index))), key)
        iterator = iter(visible)
        order = [item_key if item_key in self.sent else next(iterator) for item_key in items]
        if order == list(items):
            return
        reordered = {item_key: items[item_key] for item_key in order}
        items.clear()
        items.update(reordered)
        self.window.core.attachments.save()
        self.window.controller.attachment.update()

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
            self.window.ui.nodes['input'].fit_to_content()

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
