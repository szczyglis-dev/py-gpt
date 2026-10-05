"""Schema-driven loader fields shared by attachments, RAG and add-ons."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFileDialog

from pygpt_net.ui.widget.anims.toggles import AnimToggle
from pygpt_net.ui.widget.option.input import OptionInput, PasswordInput
from pygpt_net.utils import trans


class LoaderField(QWidget):
    """Expose one text/value interface for inputs, secrets and boolean toggles."""

    changed = Signal(str)

    def __init__(self, window, field_id, meta):
        super().__init__(window)
        self.meta = meta
        self.path_button = None
        extra = meta.get('extra', {})
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if meta['type'] == 'bool':
            self.input = AnimToggle('', window)
            layout.addWidget(self.input)
            layout.addStretch()
        else:
            input_class = PasswordInput if extra.get('secret') else OptionInput
            self.input = input_class(window, 'tool.indexer', field_id,
                                     {'value': '', '_use_locale': False})
            self.input.setPlaceholderText(meta['type'])
            layout.addWidget(self.input, 1)
            if extra.get('path'):
                self.path_button = QPushButton()
                self.path_button.clicked.connect(self.choose_path)
                layout.addWidget(self.path_button)
        if meta['type'] == 'bool':
            self.input.clicked.connect(lambda _checked: self.changed.emit(self.text()))
        else:
            self.input.textEdited.connect(self.changed.emit)
        self.setFocusProxy(self.input)
        self.setProperty('required', bool(meta.get('required')))

    def text(self):
        if self.meta['type'] == 'bool':
            return 'true' if self.input.isChecked() else 'false'
        return self.input.text()

    def setText(self, value):
        if self.meta['type'] == 'bool':
            self.input.setChecked(str(value).strip().lower() in ('true', '1'))
        else:
            self.input.setText(str(value))

    def choose_path(self):
        extra = self.meta.get('extra', {})
        title = trans('web.loader.choose.file')
        if extra.get('path') == 'directory':
            path = QFileDialog.getExistingDirectory(self, title, self.text())
        else:
            path, _ = QFileDialog.getOpenFileName(self, title, self.text(), extra.get('filter', ''))
        if path:
            self.setText(path)
            self.changed.emit(self.text())

    def update_locale(self, label, description):
        self.setAccessibleName(label)
        self.setAccessibleDescription(description)
        self.input.setAccessibleName(label)
        self.input.setAccessibleDescription(description)
        if self.path_button is not None:
            self.path_button.setText(trans('web.loader.browse'))
            self.path_button.setToolTip(trans('web.loader.choose.file'))
