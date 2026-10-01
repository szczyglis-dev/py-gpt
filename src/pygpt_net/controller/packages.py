"""One application-wide package installer and manager."""
import threading

from PySide6.QtCore import QObject, QThreadPool, QRunnable, Signal, Slot, Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTreeWidget,
                               QTreeWidgetItem, QPushButton, QPlainTextEdit, QMessageBox, QApplication)

from pygpt_net.ui.widget.dialog.update_progress import UpdateProgressDialog
from pygpt_net.utils import trans


class WorkerSignals(QObject):
    output = Signal(str)
    done = Signal(str)


class PackageWorker(QRunnable):
    def __init__(self, core, action, packages):
        super().__init__()
        self.core, self.action, self.packages = core, action, packages
        self.signals = WorkerSignals()
        self.cancel = threading.Event()

    def run(self):
        error = ''
        try:
            self.core.operate(self.action, self.packages, self.cancel, self.signals.output.emit)
        except Exception as exc:
            error = str(exc)
        self.signals.done.emit(error)


class Packages(QObject):
    dependency_request = Signal(object)

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.worker = None
        self.dialog = None
        self.callback = None
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self.dependency_request.connect(self._dependencies, Qt.ConnectionType.QueuedConnection)
        QApplication.instance().aboutToQuit.connect(self.cancel)

    def cancel(self):
        if self.worker is not None:
            self.worker.cancel.set()

    def open(self):
        if self.dialog is None:
            self.dialog = QDialog(self.window)
            self.dialog.setWindowTitle(trans('packages.title'))
            self.dialog.resize(760, 540)
            layout = QVBoxLayout(self.dialog)
            label = QLabel(self.window.core.packages.path)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(label)
            layout.addWidget(QLabel(trans('packages.restart')))
            self.tree = QTreeWidget()
            self.tree.setHeaderLabels([trans('packages.name'), trans('packages.version')])
            layout.addWidget(self.tree)
            self.input = QPlainTextEdit()
            self.input.setPlaceholderText(trans('packages.input'))
            self.input.setMaximumHeight(90)
            layout.addWidget(self.input)
            row = QHBoxLayout()
            for text, callback in [('packages.install', self.install_input),
                                   ('packages.remove', self.remove),
                                   ('packages.refresh', self.refresh)]:
                button = QPushButton(trans(text))
                button.clicked.connect(callback)
                row.addWidget(button)
            layout.addLayout(row)
            self.output = QPlainTextEdit()
            self.output.setReadOnly(True)
            self.output.document().setMaximumBlockCount(2000)
            layout.addWidget(self.output)
        self.refresh()
        self.dialog.show()
        self.dialog.raise_()

    def check_addons(self):
        """Offer repair after a Python upgrade selects an empty version directory."""
        try:
            dependencies = []
            for addon in self.window.core.extensions.list_installed():
                if addon.get('_compatible', True):
                    dependencies.extend(addon.get('external_dependencies', []))
            missing = self.window.core.packages.missing(dependencies)
            if missing:
                self.install(list(dict.fromkeys(missing)))
        except Exception as exc:
            self.window.ui.dialogs.alert(str(exc))

    def refresh(self):
        if self.dialog:
            self.tree.clear()
            for name, version in self.window.core.packages.installed():
                QTreeWidgetItem(self.tree, [name, version])

    def install_input(self):
        self.install(self.input.toPlainText().splitlines())

    def remove(self):
        item = self.tree.currentItem()
        if item:
            self.start('uninstall', [item.text(0)])

    def install(self, requirements, callback=None):
        return self.start('install', requirements, callback)

    def start(self, action, requirements, callback=None):
        if self.worker is not None:
            if callback:
                callback(False)
            return False
        try:
            self.window.core.packages.check_profile()
            requirements = self.window.core.packages.requirements([r for r in requirements if str(r).strip()])
        except Exception as exc:
            self.window.ui.dialogs.alert(str(exc))
            if callback:
                callback(False)
            return False
        if not requirements:
            if callback:
                callback(True)
            return True
        message = trans('packages.confirm').format(
            action=trans('packages.install' if action == 'install' else 'packages.remove'),
            packages='\n'.join(requirements), path=self.window.core.packages.path)
        if QMessageBox.question(self.window, trans('packages.title'), message,
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            if callback:
                callback(False)
            return False
        self.open()
        self.output.clear()
        self.callback = callback
        self.worker = PackageWorker(self.window.core.packages, action, requirements)
        self.worker.signals.output.connect(self._output)
        self.worker.signals.done.connect(self._done)
        self.progress = UpdateProgressDialog(self.window)
        self.progress.setWindowTitle(trans('packages.title'))
        self.progress.start_update(self.worker.cancel.set, trans('packages.working'))
        self.pool.start(self.worker)
        return True

    @Slot(str)
    def _output(self, line):
        self.output.appendPlainText(line)
        self.progress.set_progress(line)

    @Slot(str)
    def _done(self, error):
        self.progress.finish_update()
        self.progress.deleteLater()
        callback, self.callback = self.callback, None
        worker, self.worker = self.worker, None
        worker.signals.deleteLater()
        if not error:
            try:
                self.window.core.packages.activate()
            except Exception as exc:
                error = str(exc)
        self.refresh()
        self.output.appendPlainText(error or trans('packages.restart'))
        if error:
            self.window.ui.dialogs.alert(error)
        if callback:
            callback(not bool(error))

    def request_dependencies(self, requirements):
        """Called by an add-on worker; all widgets stay on the GUI thread."""
        request = {'requirements': requirements, 'event': threading.Event(), 'ok': False}
        self.dependency_request.emit(request)
        while not request['event'].wait(0.2):
            if getattr(self.window, 'is_closing', False):
                return False
        return request['ok']

    @Slot(object)
    def _dependencies(self, request):
        def finished(ok):
            request['ok'] = ok
            request['event'].set()
        try:
            self.install(request['requirements'], finished)
        except Exception:
            finished(False)
            raise
