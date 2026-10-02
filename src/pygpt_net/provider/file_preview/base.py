"""Public API for Files preview add-ons. Widgets are created on the GUI thread."""
from pathlib import Path

from pygpt_net.core.locale import LocaleDomain


class BaseFilePreview(LocaleDomain):
    id = ''
    name = ''
    extensions = ()

    def __init__(self):
        self.init_locale_domain()
        self.window = None

    def attach_window(self, window):
        self.window = window

    def accepts(self, path):
        """Override for content detection; extensions accept dots or bare suffixes."""
        suffix = Path(path).suffix.lower().lstrip('.')
        return suffix in {str(ext).lower().lstrip('.') for ext in self.extensions}

    def create_widget(self, path, parent):
        """Return a fresh QWidget parented to parent for this absolute file path."""
        raise NotImplementedError

    def release_widget(self, widget):
        """Stop timers, media or other resources before Files deletes the widget."""
        pass
