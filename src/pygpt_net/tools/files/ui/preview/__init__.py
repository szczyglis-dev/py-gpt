"""Extensible inline Files preview panel."""
import os
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QPoint, Signal, QSaveFile, QIODevice, QEvent
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QScrollArea, QMenu, QFileDialog, QMessageBox)
from pygpt_net.utils import trans
from .readers import ReaderRegistry, TextReader
from .directories import DirectoryPopup
from .text import TextPreview
from .media import ImagePreview, MediaPreview
from .markdown import MarkdownPreview
from pygpt_net.core.file_preview import FilePreviews


class PreviewPanel(QWidget):
    directoryRequested = Signal(str)

    def __init__(self, window, root, parent=None):
        super().__init__(parent)
        self.window = window
        self.root = os.path.abspath(root)
        self.path = None
        self.viewer = None
        self._preview_provider = None
        self.encoding = 'utf-8'
        self.newline = '\n'
        self.registry = ReaderRegistry()
        self.viewer_factories = {'image': ImagePreview, 'media': MediaPreview, 'markdown': MarkdownPreview}
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumbs = QHBoxLayout()
        self.breadcrumbs.setContentsMargins(0, 0, 0, 0)
        crumbs = QWidget()
        crumbs.setLayout(self.breadcrumbs)
        self.breadcrumbs_widget = scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(crumbs)
        scroll.setFixedHeight(32)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.layout.addWidget(scroll)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_menu)
        save = QShortcut(QKeySequence.Save, self)
        save.setContext(Qt.WidgetWithChildrenShortcut)
        save.activated.connect(self.save)
        self.show_empty()
        if isinstance(window, QWidget):
            window.installEventFilter(self)

    def event(self, event):
        if event.type() == QEvent.DeferredDelete:
            self._clear()
        return super().event(event)

    def eventFilter(self, watched, event):
        if watched is self.window and event.type() == QEvent.Close and not self.may_replace():
            event.ignore()
            return True
        return super().eventFilter(watched, event)

    def register_reader(self, reader, factory):
        """Add a reader and its widget factory(path, parent), e.g. an archive viewer."""
        self.registry.register(reader)
        self.viewer_factories[reader.kind] = factory

    def set_root(self, root):
        root = os.path.abspath(root)
        if root != self.root:
            if not self.may_replace():
                return False
            self.root = root
            self.path = None
            self.show_empty()
        return True

    def _clear(self):
        provider = self._preview_provider
        self._preview_provider = None
        if self.viewer is not None:
            if provider is not None:
                try:
                    provider.release_widget(self.viewer)
                except Exception as error:
                    print(f"File preview cleanup failed: {error}")
            if isinstance(self.viewer, TextPreview):
                self.viewer.on_destroy()
            if isinstance(self.viewer, MediaPreview):
                self.viewer.stop()
            self.layout.removeWidget(self.viewer)
            self.viewer.hide()
            self.viewer.deleteLater()
            self.viewer = None

    def _message(self, text, external=False):
        self._clear()
        self.viewer = QWidget(self)
        layout = QVBoxLayout(self.viewer)
        layout.addStretch()
        icon = QLabel()
        icon.setPixmap(QIcon(':/icons/folder.svg').pixmap(64, 64))
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        if external:
            button = QPushButton(trans('files.preview.external'))
            button.clicked.connect(self.open_external)
            layout.addWidget(button, 0, Qt.AlignHCenter)
        layout.addStretch()
        self.layout.addWidget(self.viewer, 1)

    def show_empty(self):
        self.path = None
        self._update_breadcrumbs()
        self._message(trans('files.preview.empty'))

    def _update_breadcrumbs(self):
        while self.breadcrumbs.count():
            item = self.breadcrumbs.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        paths = [(os.path.basename(self.root) or self.root, self.root)]
        if self.path:
            relative = os.path.relpath(self.path, self.root)
            current = self.root
            for part in Path(relative).parts:
                current = os.path.join(current, part)
                paths.append((part, current))
        for i, (name, path) in enumerate(paths):
            if i:
                self.breadcrumbs.addWidget(QLabel('›'))
            if path == self.path and isinstance(self.viewer, TextPreview) and self.viewer.is_content_modified():
                name += ' *'
            button = QPushButton(name)
            button.setProperty("fileBreadcrumb", True)
            button.setProperty("currentBreadcrumb", i == len(paths) - 1)
            button.setFlat(True)
            button.setToolTip(os.path.relpath(path, self.root))
            if os.path.isdir(path):
                button.clicked.connect(lambda checked=False, p=path, b=button: self.directory_menu(p, b))
            else:
                button.clicked.connect(lambda checked=False, p=path: self.directoryRequested.emit(os.path.dirname(p)))
            self.breadcrumbs.addWidget(button)
        self.breadcrumbs.addStretch()

    def directory_menu(self, path, button):
        popup = DirectoryPopup(path, self.open_file, self, workdir_root=self.root)
        position = button.mapToGlobal(QPoint(0, button.height()))
        screen = button.screen().availableGeometry()
        popup.resize(min(420, screen.width()), min(350, screen.height()))
        position.setX(max(screen.left(), min(position.x(), screen.right() - popup.width() + 1)))
        if position.y() + popup.height() > screen.bottom():
            position.setY(max(screen.top(), button.mapToGlobal(QPoint(0, 0)).y() - popup.height()))
        popup.move(position)
        self._directory_popup = popup
        popup.show()


    def may_replace(self):
        if not isinstance(self.viewer, TextPreview) or not self.viewer.is_content_modified():
            return True
        choice = QMessageBox.question(self, trans('action.save'), trans('files.preview.unsaved'),
                                      QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                      QMessageBox.Save)
        if choice == QMessageBox.Cancel:
            return False
        return self.save() if choice == QMessageBox.Save else True

    def open_file(self, path):
        path = os.path.abspath(path)
        if path == self.path:
            return True
        if not self.may_replace():
            return False
        self._clear()
        self.path = path
        self._update_breadcrumbs()
        try:
            providers = getattr(getattr(self.window, 'core', None), 'file_previews', None)
            provider = providers.resolve(path) if isinstance(providers, FilePreviews) else None
            if provider is not None:
                self._preview_provider = provider
                self.viewer = provider.create_widget(path, self)
                if not isinstance(self.viewer, QWidget):
                    self.viewer = None
                    self._preview_provider = None
                    raise TypeError('File preview must return a QWidget')
                self.viewer.setParent(self)
                self.layout.addWidget(self.viewer, 1)
                return True
            reader = self.registry.resolve(path)
            if reader is None:
                self._message(trans('files.preview.unsupported'), external=True)
                return True
            if reader.kind == 'text':
                text, self.encoding = reader.read(path)
                self.newline = '\r\n' if '\r\n' in text else '\n'
                self.viewer = TextPreview(self, path, text)
                self._stamp = self._file_stamp(path)
                self.viewer.document().modificationChanged.connect(self._update_breadcrumbs)
            else:
                self.viewer = self.viewer_factories[reader.kind](path, self)
                self.viewer.setContextMenuPolicy(Qt.CustomContextMenu)
                self.viewer.customContextMenuRequested.connect(
                    lambda pos: self.context_menu(self.viewer.mapTo(self, pos)))
            self.layout.addWidget(self.viewer, 1)
        except Exception as error:
            self._message(trans('files.preview.unsupported') + '\n' + str(error), external=True)
        return True

    def edit_markdown_source(self):
        if not isinstance(self.viewer, MarkdownPreview):
            return
        try:
            text, encoding = TextReader().read(self.path)
            stamp = self._file_stamp(self.path)
            self._clear()
            self.encoding = encoding
            self.newline = '\r\n' if '\r\n' in text else '\n'
            self.viewer = TextPreview(self, self.path, text)
            self._stamp = stamp
            self.viewer.document().modificationChanged.connect(self._update_breadcrumbs)
            self.layout.addWidget(self.viewer, 1)
            self._update_breadcrumbs()
        except (OSError, UnicodeError, ValueError) as error:
            QMessageBox.warning(self, trans('files.preview.edit_source'), str(error))

    def back_to_markdown_preview(self):
        if not self.may_replace():
            return
        path = self.path
        self._clear()
        # Reload through the normal reader dispatch after saving/discarding edits.
        self.path = None
        self.open_file(path)

    @staticmethod
    def _file_stamp(path):
        stat = os.stat(path)
        return stat.st_mtime_ns, stat.st_size

    def save(self, target=None):
        if not isinstance(self.viewer, TextPreview):
            return False
        target = target or self.path
        try:
            if target == self.path and self._file_stamp(target) != self._stamp:
                QMessageBox.warning(self, trans('action.save'), trans('files.preview.changed'))
                return False
            text = self.viewer.toPlainText().replace('\n', self.newline)
            data = text.encode(self.encoding)
            output = QSaveFile(target)
            if not output.open(QIODevice.WriteOnly):
                raise OSError(output.errorString())
            if output.write(data) != len(data):
                output.cancelWriting()
                raise OSError(output.errorString())
            if not output.commit():
                raise OSError(output.errorString())
            if target == self.path:
                self._stamp = self._file_stamp(target)
                self.viewer.set_baseline_content()
            return True
        except (OSError, UnicodeError) as error:
            QMessageBox.warning(self, trans('action.save'), str(error))
            return False

    def save_as(self):
        if not self.path:
            return
        target, _ = QFileDialog.getSaveFileName(self, trans('action.save_as'), self.path)
        if target:
            if isinstance(self.viewer, TextPreview):
                self.save(target)
            else:
                try:
                    if os.path.abspath(target) != self.path:
                        shutil.copy2(self.path, target)
                except OSError as error:
                    QMessageBox.warning(self, trans('action.save_as'), str(error))

    def open_external(self):
        if self.path:
            self.window.tools.get("files").paths.open(self.path)

    def add_file_actions(self, menu):
        if not self.path:
            return
        if isinstance(self.viewer, MarkdownPreview):
            menu.addAction(QIcon(':/icons/edit.svg'), trans('files.preview.edit_source'), self.edit_markdown_source)
            menu.addSeparator()
            copy = menu.addAction(QIcon(':/icons/copy.svg'), trans('action.copy'), self.viewer.copy)
            copy.setEnabled(self.viewer.textCursor().hasSelection())
            menu.addAction(trans('action.select_all'), self.viewer.selectAll)
            menu.addSeparator()
        elif isinstance(self.viewer, TextPreview) and Path(self.path).suffix.lower() in ('.md', '.markdown'):
            menu.addAction(trans('files.preview.back_to_preview'), self.back_to_markdown_preview)
            menu.addSeparator()
        menu.addAction(trans('files.preview.external'), self.open_external)
        menu.addAction(trans('action.open_dir'), lambda: self.window.tools.get("files").paths.reveal(self.path))
        if isinstance(self.viewer, TextPreview):
            menu.addAction(trans('action.save'), lambda: self.save())
        menu.addAction(trans('action.save_as'), self.save_as)

    def context_menu(self, pos):
        menu = QMenu(self)
        self.add_file_actions(menu)
        if not menu.isEmpty():
            menu.exec(self.mapToGlobal(pos))
        menu.deleteLater()

    def hideEvent(self, event):
        if isinstance(self.viewer, MediaPreview):
            self.viewer.player.pause()
        super().hideEvent(event)
