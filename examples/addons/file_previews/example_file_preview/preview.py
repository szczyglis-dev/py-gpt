"""A read-only JSON tree preview, using only PyGPT's bundled Qt dependency."""
import json

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from pygpt_net.provider.file_preview import BaseFilePreview


class ExampleFilePreview(BaseFilePreview):
    id = 'example_file_preview'
    name = 'JSON tree preview'
    extensions = ('json',)

    def create_widget(self, path, parent):
        # Parse before creating the widget so a read/parse error leaves no orphan.
        with open(path, encoding='utf-8-sig') as stream:
            value = json.load(stream)
        tree = QTreeWidget(parent)
        tree.setHeaderLabels(['Key', 'Value'])

        def add(container, key, value):
            branch = isinstance(value, (dict, list))
            item = QTreeWidgetItem(container, [str(key), '' if branch else json.dumps(value, ensure_ascii=False)])
            if isinstance(value, dict):
                for child_key, child in value.items():
                    add(item, child_key, child)
            elif isinstance(value, list):
                for child_key, child in enumerate(value):
                    add(item, child_key, child)
        add(tree, 'root', value)
        tree.expandToDepth(1)
        return tree
